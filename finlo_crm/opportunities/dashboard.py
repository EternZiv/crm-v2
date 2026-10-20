"""Dashboard utilities for opportunities module."""

# Standard library imports
import logging

# Third-party imports (Django)
from django.utils.http import urlencode

from finlo.contrib.dashboard.utils import DefaultDashboardGenerator
from finlo.contrib.utils.methods import get_section_info_for_model

# First party imports (Finlo)
from finlo.db.models import Count
from finlo.utils.choices import TABLE_FALLBACK_FIELD_TYPES
from finlo.utils.translation import gettext_lazy as _

# Local imports
from .models import Opportunity

logger = logging.getLogger(__name__)


def create_opportunity_charts(self, queryset, model_info):
    """Create opportunity-specific charts"""
    try:
        if hasattr(queryset.model, "lead_source") or hasattr(queryset.model, "source"):
            source_field = (
                "lead_source" if hasattr(queryset.model, "lead_source") else "source"
            )
            source_data = list(
                queryset.values(source_field)
                .annotate(count=Count("id"))
                .order_by("-count")
            )

            if source_data:
                labels = [item[source_field] or _("Unknown") for item in source_data]
                data = [item["count"] for item in source_data]

                section_info = get_section_info_for_model(queryset.model)
                urls = []
                for item in source_data:
                    value = item[source_field] or "Unknown"
                    query = urlencode(
                        {
                            "section": section_info["section"],
                            "apply_filter": "true",
                            "field": source_field,
                            "operator": "exact",
                            "value": value,
                        }
                    )
                    urls.append(f"{section_info['url']}?{query}")

                return {
                    "title": _("Opportunities by Lead Source"),
                    "type": "column",
                    "data": {
                        "labels": labels,
                        "urls": urls,
                        "data": data,
                        "labelField": _("Lead Source"),
                    },
                }

        stage_field = None
        if hasattr(queryset.model, "stage"):
            stage_field = "stage"
        elif hasattr(queryset.model, "status"):
            stage_field = "status"
        elif hasattr(queryset.model, "opportunity_stage"):
            stage_field = "opportunity_stage"

        if stage_field:
            stage_data = list(
                queryset.values(stage_field)
                .annotate(count=Count("id"))
                .order_by("-count")
            )

            if stage_data:
                labels = [item[stage_field] or _("Unknown") for item in stage_data]
                data = [item["count"] for item in stage_data]

                return {
                    "title": _("Opportunities by Stage"),
                    "type": "funnel",
                    "data": {"labels": labels, "data": data, "labelField": _("Stage")},
                }

        if hasattr(queryset.model, "is_won"):
            won_data = list(queryset.values("is_won").annotate(count=Count("id")))

            if won_data:
                labels = []
                data = []
                for item in won_data:
                    status = _("Won") if item["is_won"] else _("In Progress/Lost")
                    labels.append(status)
                    data.append(item["count"])

                return {
                    "title": _("Opportunity Win Rate"),
                    "type": "pie",
                    "data": {
                        "labels": labels,
                        "data": data,
                        "labelField": _("Status"),
                    },
                }

        if hasattr(queryset.model, "amount") or hasattr(queryset.model, "value"):
            amount_field = "amount" if hasattr(queryset.model, "amount") else "value"

            opportunities = list(
                queryset.values("id", amount_field).exclude(
                    **{f"{amount_field}__isnull": True}
                )
            )
            if opportunities:
                ranges = [_("<10K"), _("10K-50K"), _("50K-100K"), _("100K+")]
                range_counts = [0, 0, 0, 0]

                for opp in opportunities:
                    amount = float(opp[amount_field] or 0)
                    if amount < 10000:
                        range_counts[0] += 1
                    elif amount < 50000:
                        range_counts[1] += 1
                    elif amount < 100000:
                        range_counts[2] += 1
                    else:
                        range_counts[3] += 1

                return {
                    "title": _("Opportunities by Value Range"),
                    "type": "column",
                    "data": {
                        "labels": ranges,
                        "data": range_counts,
                        "labelField": _("Value Range"),
                    },
                }

    except Exception as e:
        logger.warning("Error creating opportunity chart: %s", e)

    return None


def opportuntiy_table_fields(model_class):
    """Return list of {name, verbose_name} for opportuntiy table columns."""

    priority = ["name", "title", "account", "amount", "stage"]
    fields = []
    for name in priority:
        try:
            f = model_class._meta.get_field(name)
            fields.append(
                {
                    "name": name,
                    "verbose_name": f.verbose_name or name.replace("_", " ").title(),
                }
            )
        except Exception:
            continue
    if len(fields) < 4:
        for f in model_class._meta.fields:
            if len(fields) >= 4:
                break
            if (
                f.name not in [x["name"] for x in fields]
                and f.get_internal_type() in TABLE_FALLBACK_FIELD_TYPES
            ):
                fields.append(
                    {
                        "name": f.name,
                        "verbose_name": f.verbose_name
                        or f.name.replace("_", " ").title(),
                    }
                )
    return fields


def opportunity_table_func(generator, model_info):
    """Generate table context for won opportunities."""
    filter_kwargs = (
        {"stage__name": "Closed Won"} if hasattr(model_info["model"], "stage") else {}
    )

    return generator.build_table_context(
        model_info=model_info,
        title=_("Closed Won Opportunities"),
        filter_kwargs=filter_kwargs,
        no_found_img="assets/img/not-found-list.svg",
        no_record_msg=_("No closed won opportunities found."),
        view_id="opportunities_dashboard_list",
    )


def opportunity_kpi_cards(generator, model_info):
    """
    Generate sales pipeline KPIs for opportunities:
    - Active Opportunities
    - Proposal Sent
    - In Negotiation
    - Won
    - Lost
    - Delayed
    - Total Won Value
    - Pipeline Value
    - Upcoming Follow-ups
    - Overdue Follow-ups
    """
    from decimal import Decimal
    from finlo.db.models import Q, Sum
    from finlo.utils import timezone

    model_class = model_info["model"]
    qs = generator.get_queryset(model_class)
    section_info = get_section_info_for_model(model_class)
    today = timezone.now().date()

    active_qs = qs.exclude(stage__stage_type__in=["won", "lost"])
    active_count = active_qs.count()

    proposal_count = qs.filter(
        Q(stage__name__icontains="Proposal") | Q(stage__stage_type="proposal")
    ).count()

    negotiation_count = qs.filter(
        Q(stage__name__icontains="Negotiation") | Q(stage__stage_type="negotiation")
    ).count()

    won_qs = qs.filter(Q(stage__stage_type="won") | Q(stage__name__icontains="Won"))
    won_count = won_qs.count()

    lost_qs = qs.filter(Q(stage__stage_type="lost") | Q(stage__name__icontains="Lost"))
    lost_count = lost_qs.count()

    delayed_qs = qs.filter(
        Q(stage__stage_type="delayed") | Q(stage__name__icontains="Delayed")
    )
    delayed_count = delayed_qs.count()

    won_val = won_qs.aggregate(total=Sum("final_deal_value"))["total"]
    if won_val is None:
        won_val = won_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0")

    pipeline_val = active_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0")

    upcoming_followups = qs.filter(
        next_follow_up_date__gte=today
    ).count()

    overdue_followups = qs.filter(
        next_follow_up_date__lt=today
    ).exclude(stage__stage_type__in=["won", "lost"]).count()

    return [
        {
            "title": _("Active Opportunities"),
            "value": active_count,
            "icon": "fa-briefcase",
            "color": "blue",
            "url": section_info["url"],
            "section": section_info["section"],
        },
        {
            "title": _("Proposal Sent"),
            "value": proposal_count,
            "icon": "fa-file-invoice-dollar",
            "color": "indigo",
            "url": section_info["url"],
            "section": section_info["section"],
        },
        {
            "title": _("In Negotiation"),
            "value": negotiation_count,
            "icon": "fa-comments-dollar",
            "color": "orange",
            "url": section_info["url"],
            "section": section_info["section"],
        },
        {
            "title": _("Won"),
            "value": won_count,
            "icon": "fa-trophy",
            "color": "green",
            "url": section_info["url"],
            "section": section_info["section"],
        },
        {
            "title": _("Lost"),
            "value": lost_count,
            "icon": "fa-circle-xmark",
            "color": "red",
            "url": section_info["url"],
            "section": section_info["section"],
        },
        {
            "title": _("Delayed"),
            "value": delayed_count,
            "icon": "fa-clock",
            "color": "amber",
            "url": section_info["url"],
            "section": section_info["section"],
        },
        {
            "title": _("Total Won Value"),
            "value": float(won_val),
            "type": "currency",
            "icon": "fa-money-bill-wave",
            "color": "emerald",
            "url": section_info["url"],
            "section": section_info["section"],
        },
        {
            "title": _("Pipeline Value"),
            "value": float(pipeline_val),
            "type": "currency",
            "icon": "fa-chart-line",
            "color": "cyan",
            "url": section_info["url"],
            "section": section_info["section"],
        },
        {
            "title": _("Upcoming Follow-ups"),
            "value": upcoming_followups,
            "icon": "fa-calendar-check",
            "color": "teal",
            "url": section_info["url"],
            "section": section_info["section"],
        },
        {
            "title": _("Overdue Follow-ups"),
            "value": overdue_followups,
            "icon": "fa-calendar-xmark",
            "color": "rose",
            "url": section_info["url"],
            "section": section_info["section"],
        },
    ]


DefaultDashboardGenerator.extra_models.append(
    {
        "model": Opportunity,
        "name": _("Opportunities"),
        "icon": "fa-handshake",
        "color": "purple",
        "include_kpi": False,
        "kpi_func": opportunity_kpi_cards,
        "chart_func": create_opportunity_charts,
        "table_func": opportunity_table_func,
        "table_fields_func": opportuntiy_table_fields,
    }
)
