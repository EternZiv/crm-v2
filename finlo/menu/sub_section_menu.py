"""
Module that provides a registry for managing and retrieving sub-section in the sidebar
"""

from collections import defaultdict
from typing import Any, Dict, List, Type

from django.core.exceptions import ImproperlyConfigured

from .main_section_menu import get_main_section_menu

# Registry to hold all subsection menu classes
sub_section_menu: List[Any] = []
_STATIC_SUB_SECTION_DATA: List[Dict[str, Any]] = None


def register(cls: Type[Any]):
    """Decorator to register a main sub-section menu class."""
    global _STATIC_SUB_SECTION_DATA
    _STATIC_SUB_SECTION_DATA = None
    sub_section_menu.append(cls)
    return cls


def _get_static_sub_section_data(request=None) -> List[Dict[str, Any]]:
    global _STATIC_SUB_SECTION_DATA
    if _STATIC_SUB_SECTION_DATA is not None:
        return _STATIC_SUB_SECTION_DATA

    main_sections = {
        section["section"]
        for section in get_main_section_menu(request=request)
        if section.get("section")
    }

    parsed = []
    for cls in sub_section_menu:
        obj = cls()
        section_name = getattr(obj, "section", None)
        perm = getattr(obj, "perm", [])

        if isinstance(perm, str):
            perm = [perm]

        all_perms = getattr(obj, "all_perms", False)

        if section_name and section_name not in main_sections:
            raise ImproperlyConfigured(
                f"Sub section '{obj.__class__.__name__}' uses section "
                f"'{section_name}' but no matching main section is registered."
            )

        app_label = getattr(obj, "app_label", None)
        item = {
            "label": getattr(obj, "verbose_name", None),
            "icon": getattr(obj, "icon", None),
            "url": getattr(obj, "url", None),
            "class": getattr(obj, "css_class", "sidebar-link"),
            "app_label": app_label,
            "id": getattr(obj, "id", app_label),
            "perm": {
                "perms": perm,
                "all_perms": all_perms,
            },
            "position": getattr(obj, "position", None),
            "attrs": getattr(obj, "attrs", {}),
        }
        parsed.append({
            "section": section_name,
            "perm": perm,
            "all_perms": all_perms,
            "item": item,
            "position": item["position"],
        })

    _STATIC_SUB_SECTION_DATA = parsed
    return parsed


def get_sub_section_menu(request=None) -> Dict[str, List[Dict]]:
    """
    Return all registered main sub-sections grouped by section name,
    filtered by user permissions.
    """
    if request is not None and hasattr(request, "_cached_sub_section_menu"):
        return request._cached_sub_section_menu

    static_data = _get_static_sub_section_data(request=request)
    sections = defaultdict(list)

    user = getattr(request, "user", None) if request else None
    is_auth = user and user.is_authenticated
    is_super = is_auth and getattr(user, "is_superuser", False)

    for entry in static_data:
        perm = entry["perm"]
        all_perms = entry["all_perms"]

        # Skip items if user doesn't have required perms
        if is_auth and not is_super:
            if all_perms:
                if not all(user.has_perm(p) for p in perm):
                    continue
            else:
                if perm and not any(user.has_perm(p) for p in perm):
                    continue

        section_name = entry["section"]
        if section_name:
            sections[section_name].append(entry["item"])

    for items in sections.values():
        items.sort(key=lambda x: (x["position"] is None, x["position"]))

    if request is not None:
        request._cached_sub_section_menu = sections

    return sections
