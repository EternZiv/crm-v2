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


def get_lead_cache_version(company_id=None, user_id=None):
    """Return the company-wide data revision used by user-scoped cache entries.

    Results remain keyed per user, since authorization scopes can differ. A
    company-wide revision ensures mutations by one user invalidate every
    user's derived aggregates without sharing their cached results.
    """
    v_key = f"finlo:leads:v:{company_id if company_id is not None else 'all'}"
    version = cache.get(v_key)
    if version is None:
        cache.add(v_key, 1, timeout=86400 * 7)
        version = cache.get(v_key, 1)
    return version


def get_lead_user_cache_version(user_id):
    """Return the per-user authorization-scope revision for cached aggregates."""
    key = f"finlo:leads:user:v:{user_id}"
    version = cache.get(key)
    if version is None:
        cache.add(key, 1, timeout=86400 * 7)
        version = cache.get(key, 1)
    return version


def bump_lead_cache_version(company_id=None, user_id=None):
    """Invalidate all per-user aggregates within one affected company.

    A random revision also works with cache backends that do not implement an
    atomic increment. A missing company means the genuinely shared/global
    records are affected; normal tenant mutations always pass their company.
    """
    key = f"finlo:leads:v:{company_id if company_id is not None else 'all'}"
    try:
        cache.set(key, uuid.uuid4().hex, timeout=86400 * 7)
    except Exception:
        logger.exception("Could not invalidate lead analytics cache for company=%s", company_id)
    logger.debug("Lead cache version bumped for company=%s", company_id)


def bump_lead_user_cache_version(user_id):
    """Invalidate only one user's aggregates after an individual scope change."""
    try:
        cache.set(
            f"finlo:leads:user:v:{user_id}", uuid.uuid4().hex, timeout=86400 * 7
        )
    except Exception:
        logger.exception("Could not invalidate lead analytics cache for user=%s", user_id)


class LeadDataService:
    """Centralized service for high-efficiency authorized lead aggregations."""

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
        company_id = getattr(getattr(user, "company", None), "pk", None)
        version = get_lead_cache_version(company_id)
        user_version = get_lead_user_cache_version(user.pk)
        raw = f"{prefix}:{sorted(kwargs.items())}"
        h = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
        return f"lead_svc:{user.pk}:{company_id if company_id is not None else 'none'}:{version}:{user_version}:{h}"

    @classmethod
    def get_lead_kpi_summary(cls, user, company=None, date_range=None, date_from=None, date_to=None):
        """
        Compute total, open, and converted leads using a SINGLE aggregate query.
        Replaces 3 separate full count queries across dashboard and module headers.
        """
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

        if req_cache and cache_key in req_cache:
            return req_cache[cache_key]

        cached = cache.get(cache_key)
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

        cache.set(cache_key, kpi_data, timeout=CACHE_TTL)
        if request is not None:
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

        if req_cache and cache_key in req_cache:
            return req_cache[cache_key]

        cached = cache.get(cache_key)
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

        cache.set(cache_key, rows, timeout=CACHE_TTL)
        if request is not None:
            if not hasattr(request, "_lead_stage_cache"):
                request._lead_stage_cache = {}
            request._lead_stage_cache[cache_key] = rows

        return rows

    @classmethod
    def get_leads_by_source(
        cls, user, company=None, date_range=None, date_from=None, date_to=None, is_convert=False
    ):
        """Aggregate lead counts grouped by lead source for dashboard charts."""
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

        if req_cache and cache_key in req_cache:
            return req_cache[cache_key]

        cached = cache.get(cache_key)
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

        cache.set(cache_key, rows, timeout=CACHE_TTL)
        if request is not None:
            if not hasattr(request, "_lead_source_cache"):
                request._lead_source_cache = {}
            request._lead_source_cache[cache_key] = rows

        return rows

