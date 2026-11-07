"""
Finlo functional - re-exports django.utils.functional for consistent imports.

Use: from finlo.utils.functional import cached_property
     from finlo.utils.functional import lazy, Promise, ...
"""

from django.utils.functional import (
    LazyObject,
    Promise,
    SimpleLazyObject,
    cached_property,
    classproperty,
    empty,
    keep_lazy,
    keep_lazy_text,
    lazy,
    lazystr,
    partition,
)

__all__ = [
    "LazyObject",
    "Promise",
    "SimpleLazyObject",
    "cached_property",
    "classproperty",
    "empty",
    "keep_lazy",
    "keep_lazy_text",
    "lazy",
    "lazystr",
    "partition",
]
