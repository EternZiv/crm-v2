"""
FINLONEXA CRM v2 - Centralized Lead Data Service.

Provides high-performance, authorized, cross-page shared data access for:
- Lead KPI summaries (total, open, converted) via single-query aggregation
- Lead counts grouped by pipeline stage
- Lead counts grouped by lead source
- Cache versioning and invalidation hooks

Architecture:
- Layer 1: Request-local cache (deduplication within the same request lifecycle)
- Layer 2: Django cache backend (LocMemCache / Redis) with canonical scoped keys
- Security: Strictly uses get_queryset_for_module(user, Lead) ensuring tenant and role hierarchy
"""

import hashlib
import logging
import uuid
from django.core.cache import cache
from django.db.models import Count, Q
from finlo.contrib.generics.views.helpers.queryset_utils import get_queryset_for_module
from finlo.contrib.dashboard.utils import apply_date_range_to_queryset
from finlo.contrib.utils.middlewares import get_current_request
from finlo_crm.leads.models import Lead, LeadStatus

logger = logging.getLogger(__name__)

CACHE_TTL = 300  # 5 minutes bounded TTL for aggregated analytics
REVISION_TTL = 86400 * 7  # bounded metadata retention; reinitialization is random


def _get_or_create_revision(key):
    """Read a shared revision, initializing it without a stale-value collision.

    Revision metadata is deliberately non-expiring: it is one bounded key per
    company (and per user for authorization scope). If Redis evicts or loses a
    key, a fresh random revision prevents old result keys from becoming current
    again. On cache failure, ``None`` disables shared result caching safely.
    """
    try:
        version = cache.get(key)
        if version is not None:
            return version
        candidate = uuid.uuid4().hex
        if cache.add(key, candidate, timeout=REVISION_TTL):
            return candidate
        # Another worker initialized it between get and add.
        return cache.get(key)
    except Exception:
        logger.warning("Lead cache revision unavailable; bypassing cache", exc_info=True)
        return None


def get_lead_cache_version(company_id=None, user_id=None):
    """Return the tenant data revision while keeping results user-scoped."""
    v_key = f"finlo:leads:v:{company_id if company_id is not None else 'all'}"
    return _get_or_create_revision(v_key)


def get_lead_user_cache_version(user_id):
    """Return the per-user authorization-scope revision for cached aggregates."""
    key = f"finlo:leads:user:v:{user_id}"
    return _get_or_create_revision(key)


def bump_lead_cache_version(company_id=None, user_id=None):
    """Invalidate all per-user aggregates within one affected company.

    A random revision also works with cache backends that do not implement an
    atomic increment. A missing company means the genuinely shared/global
    records are affected; normal tenant mutations always pass their company.
    """
    key = f"finlo:leads:v:{company_id if company_id is not None else 'all'}"
    try:
        cache.set(key, uuid.uuid4().hex, timeout=REVISION_TTL)
    except Exception:
        logger.exception("Could not invalidate lead analytics cache for company=%s", company_id)
    logger.debug("Lead cache version bumped for company=%s", company_id)


def bump_lead_user_cache_version(user_id):
    """Invalidate only one user's aggregates after an individual scope change."""
    try:
        cache.set(
            f"finlo:leads:user:v:{user_id}", uuid.uuid4().hex, timeout=REVISION_TTL
        )
    except Exception:
        logger.exception("Could not invalidate lead analytics cache for user=%s", user_id)


class LeadDataService:
    """Centralized service for high-efficiency authorized lead aggregations."""

    @classmethod
    def _can_read_leads(cls, user):
        """Check current effective Lead read access before any cache lookup.

        The scoped queryset enforces company and ownership boundaries when an
        aggregate is computed. A cache hit skips that queryset, so the current
        effective permission must be checked independently on every call.
        """
        if not user or not getattr(user, "is_authenticated", False):
            return False
        if not getattr(user, "is_active", False):
            return False
        if getattr(user, "is_superuser", False):
            return True

        from finlo.contrib.core.sales_authorization import has_effective_permission

        return has_effective_permission(user, "leads.view_lead") or (
            has_effective_permission(user, "leads.view_own_lead")
        )

    @classmethod
    def _get_base_queryset(cls, user, company=None, date_range=None, date_from=None, date_to=None):
        """Build authorized, scoped base queryset for the user."""
        qs = get_queryset_for_module(user, Lead)
        if company:
            qs = qs.filter(company=company)
        if date_range:
            if date_range == "custom":
                qs = apply_date_range_to_queryset(
                    qs, Lead, date_range_days="custom", date_from=date_from, date_to=date_to
                )
            else:
                qs = apply_date_range_to_queryset(qs, Lead, date_range)
        return qs

    @classmethod
    def _build_cache_key(cls, user, prefix, **kwargs):
        """Construct canonical, security-scoped cache key."""
        # A caller may query a switched/active company different from the
        # user's home company. Keep both the revision and key tied to the
        # actual data scope passed to the service.
        company_id = kwargs.get("company_id")
        if company_id is None:
            role_key = getattr(getattr(user, "role", None), "system_key", None)
            if getattr(user, "is_superuser", False) is True or role_key == "SUPER_ADMIN":
                # An all-company query cannot safely be invalidated by a
                # single tenant generation. Leave this rare path uncached.
                return None
            company_id = getattr(getattr(user, "company", None), "pk", None)
        if company_id is None:
            return None
        # Include the global generation as well, so an explicitly global
        # mutation (for example an authorized all-company bulk update) can
        # invalidate every tenant key without enumerating tenant IDs.
        global_revision = get_lead_cache_version("all")
        company_revision = (
            get_lead_cache_version(company_id) if company_id is not None else None
        )
        if global_revision is None or (
            company_id is not None and company_revision is None
        ):
            return None
        version = (
            global_revision
            if company_id is None
            else f"{global_revision}:{company_revision}"
        )
        user_version = get_lead_user_cache_version(user.pk)
        if version is None or user_version is None:
            return None
        raw = f"{prefix}:{sorted(kwargs.items())}"
        h = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
        return f"lead_svc:{user.pk}:{company_id if company_id is not None else 'none'}:{version}:{user_version}:{h}"

    @classmethod
    def get_lead_kpi_summary(cls, user, company=None, date_range=None, date_from=None, date_to=None):
        """
        Compute total, open, and converted leads using a SINGLE aggregate query.
        Replaces 3 separate full count queries across dashboard and module headers.
        """
        if not cls._can_read_leads(user):
            return {"total": 0, "open": 0, "converted": 0}

        request = get_current_request()
        req_cache = getattr(request, "_lead_kpi_cache", None) if request else None
        cache_key = cls._build_cache_key(
            user,
            "kpi_summary",
            company_id=getattr(company, "pk", company),
            dr=str(date_range),
            df=str(date_from),
            dt=str(date_to),
        )

        if cache_key is not None and req_cache and cache_key in req_cache:
            return req_cache[cache_key]

        try:
            cached = cache.get(cache_key) if cache_key is not None else None
        except Exception:
            logger.warning("Lead KPI cache read failed; querying database", exc_info=True)
            cached = None
        if cached is not None:
            if req_cache is not None:
                req_cache[cache_key] = cached
            return cached

        # Execute single aggregation query
        qs = cls._get_base_queryset(user, company, date_range, date_from, date_to)
        res = qs.aggregate(
            total=Count("id"),
            open=Count("id", filter=Q(is_convert=False)),
            converted=Count("id", filter=Q(is_convert=True)),
        )

        kpi_data = {
            "total": res["total"] or 0,
            "open": res["open"] or 0,
            "converted": res["converted"] or 0,
        }

        if cache_key is not None:
            try:
                cache.set(cache_key, kpi_data, timeout=CACHE_TTL)
            except Exception:
                logger.warning("Lead KPI cache write failed", exc_info=True)
        if request is not None and cache_key is not None:
            if not hasattr(request, "_lead_kpi_cache"):
                request._lead_kpi_cache = {}
            request._lead_kpi_cache[cache_key] = kpi_data

        return kpi_data

    @classmethod
    def get_lead_counts_by_stage(
        cls, user, company=None, date_range=None, date_from=None, date_to=None, is_convert=False
    ):
        """
        Aggregate lead counts grouped by pipeline stage.
        Shared between Dashboard (Leads by Stage chart) and Leads module (LeadChartView).
        """
        if not cls._can_read_leads(user):
            return []

        request = get_current_request()
        req_cache = getattr(request, "_lead_stage_cache", None) if request else None
        cache_key = cls._build_cache_key(
            user,
            "stage_counts",
            company_id=getattr(company, "pk", company),
            dr=str(date_range),
            df=str(date_from),
            dt=str(date_to),
            ic=is_convert,
        )

        if cache_key is not None and req_cache and cache_key in req_cache:
            return req_cache[cache_key]

        try:
            cached = cache.get(cache_key) if cache_key is not None else None
        except Exception:
            logger.warning("Lead stage cache read failed; querying database", exc_info=True)
            cached = None
        if cached is not None:
            if req_cache is not None:
                req_cache[cache_key] = cached
            return cached

        qs = cls._get_base_queryset(user, company, date_range, date_from, date_to)
        if is_convert is not None:
            qs = qs.filter(is_convert=is_convert)

        rows = list(
            qs.values("lead_status_id", "lead_status__name")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        if cache_key is not None:
            try:
                cache.set(cache_key, rows, timeout=CACHE_TTL)
            except Exception:
                logger.warning("Lead stage cache write failed", exc_info=True)
        if request is not None and cache_key is not None:
            if not hasattr(request, "_lead_stage_cache"):
                request._lead_stage_cache = {}
            request._lead_stage_cache[cache_key] = rows

        return rows

    @classmethod
    def get_leads_by_source(
        cls, user, company=None, date_range=None, date_from=None, date_to=None, is_convert=False
    ):
        """Aggregate lead counts grouped by lead source for dashboard charts."""
        if not cls._can_read_leads(user):
            return []

        request = get_current_request()
        req_cache = getattr(request, "_lead_source_cache", None) if request else None
        cache_key = cls._build_cache_key(
            user,
            "source_counts",
            company_id=getattr(company, "pk", company),
            dr=str(date_range),
            df=str(date_from),
            dt=str(date_to),
            ic=is_convert,
        )

        if cache_key is not None and req_cache and cache_key in req_cache:
            return req_cache[cache_key]

        try:
            cached = cache.get(cache_key) if cache_key is not None else None
        except Exception:
            logger.warning("Lead source cache read failed; querying database", exc_info=True)
            cached = None
        if cached is not None:
            if req_cache is not None:
                req_cache[cache_key] = cached
            return cached

        qs = cls._get_base_queryset(user, company, date_range, date_from, date_to)
        if is_convert is not None:
            qs = qs.filter(is_convert=is_convert)

        rows = list(
            qs.values("lead_source")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        if cache_key is not None:
            try:
                cache.set(cache_key, rows, timeout=CACHE_TTL)
            except Exception:
                logger.warning("Lead source cache write failed", exc_info=True)
        if request is not None and cache_key is not None:
            if not hasattr(request, "_lead_source_cache"):
                request._lead_source_cache = {}
            request._lead_source_cache[cache_key] = rows

        return rows

