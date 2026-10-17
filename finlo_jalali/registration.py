"""Inject Jalali date/time picker assets and History formatting without patching core."""

from finlo.registry.asset_registry import register_html
from finlo.registry.history_registry import register_history_datetime_formatter
from finlo_jalali.history import format_history_datetime_as_jalali

register_html(
    "finlo_jalali/inject_html/jalali_assets_head.html",
    slot="head_end",
    priority=95,
)

register_html(
    "finlo_jalali/inject_html/jalali_assets_js.html",
    slot="body_end",
    priority=80,
)

register_history_datetime_formatter(format_history_datetime_as_jalali)
