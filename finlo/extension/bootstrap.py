"""
Bootstrap all Finlo extension layers after Django has finished loading apps.

Called from ``finlo.urls.project`` (after ``apps.ready``) so extension apps
listed after their target apps in ``INSTALLED_APPS`` are included.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def bootstrap_extensions() -> None:
    """
    Compose form, filter, nav, list, card, kanban, detail, detail_section,
    tab, formatter, view, and mixin extensions, once the app registry is
    fully ready.
    """
    try:
        from django.apps import apps as django_apps

        if not django_apps.ready:
            return
    except Exception:
        return

    try:
        from finlo.extension.card.bootstrap import apply_card_extensions
        from finlo.extension.detail.bootstrap import apply_detail_extensions
        from finlo.extension.detail_section.bootstrap import (
            apply_detail_section_extensions,
        )
        from finlo.extension.filter.bootstrap import apply_filter_extensions
        from finlo.extension.formatting.bootstrap import apply_formatter_extensions
        from finlo.extension.forms.bootstrap import apply_form_extensions
        from finlo.extension.kanban.bootstrap import apply_kanban_extensions
        from finlo.extension.list.bootstrap import apply_list_extensions
        from finlo.extension.mixin.bootstrap import apply_mixin_extensions
        from finlo.extension.nav.bootstrap import apply_nav_extensions
        from finlo.extension.tab.bootstrap import apply_tab_extensions
        from finlo.extension.view.bootstrap import apply_view_extensions

        apply_form_extensions(force=True)
        apply_filter_extensions(force=True)
        apply_nav_extensions(force=True)
        apply_list_extensions(force=True)
        apply_card_extensions(force=True)
        apply_kanban_extensions(force=True)
        apply_detail_extensions(force=True)
        apply_detail_section_extensions(force=True)
        apply_tab_extensions(force=True)
        apply_formatter_extensions(force=True)
        apply_view_extensions(force=True)
        apply_mixin_extensions(force=True)
    except Exception as exc:
        logger.warning(
            "Finlo extension bootstrap failed: %s",
            exc,
            exc_info=True,
        )
