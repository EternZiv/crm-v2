"""Small shared-cache helpers for authentication endpoint throttling."""

import hashlib

from django.core.cache import cache


def cache_key(scope, value):
    """Return a deterministic cache key without embedding usernames or IPs."""
    digest = hashlib.sha256(str(value).encode("utf-8", "ignore")).hexdigest()
    return f"auth-rate:{scope}:{digest}"


def count(key):
    """Read a throttle counter."""
    return cache.get(key, 0)


def increment(key, timeout):
    """Increment a fixed-window counter using the cache backend's atomic incr."""
    if cache.add(key, 1, timeout=timeout):
        return 1
    try:
        return cache.incr(key)
    except ValueError:
        # Expiry may race between add() and incr().
        cache.set(key, 1, timeout=timeout)
        return 1


def clear(*keys):
    """Clear counters after successful authentication."""
    for key in keys:
        if key:
            cache.delete(key)
