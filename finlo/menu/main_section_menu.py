"""
This module defines a registry for managing main section menu entries in Finlo.
"""

from typing import Any, Dict, List, Type

# Registry to hold all main section menu classes
main_section_menu: List[Any] = []
_CACHED_MAIN_PAGES: List[Dict] = None


def register(cls: Type[Any]):
    """Decorator to register a main section menu class."""
    global _CACHED_MAIN_PAGES
    _CACHED_MAIN_PAGES = None
    main_section_menu.append(cls)
    return cls


def get_main_section_menu(request=None) -> List[Dict]:
    """
    Return all registered main section menu items.

    Returns:
        A list of dictionaries representing menu items, sorted by position.
    """
    global _CACHED_MAIN_PAGES
    if _CACHED_MAIN_PAGES is not None:
        return _CACHED_MAIN_PAGES

    pages = []
    for cls in main_section_menu:
        obj = cls()
        item = {
            "section": getattr(obj, "section", None),
            "name": getattr(obj, "name", None),
            "url": getattr(obj, "url", None),
            "icon": getattr(obj, "icon", None),
            "position": getattr(obj, "position", None),
            "attrs": getattr(obj, "attrs", {}),
        }
        pages.append(item)

    pages.sort(
        key=lambda x: (
            (
                0
                if x["position"] is not None and x["position"] >= 0
                else 1 if x["position"] is None else 2
            ),
            x["position"] if x["position"] is not None else 0,
        )
    )
    _CACHED_MAIN_PAGES = pages
    return pages
