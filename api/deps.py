"""
Shared dependencies — Redis cache, pagination helpers.
"""
import json
import hashlib
from typing import Optional
from functools import wraps

from django.core.cache import cache
from django.conf import settings


def cache_key(*args) -> str:
    """Generate a consistent cache key from arguments."""
    raw = ":".join(str(a) for a in args)
    return hashlib.md5(raw.encode()).hexdigest()


def cached(prefix: str, timeout: int = 300):
    """Decorator to cache function results in Redis."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = f"{prefix}:{cache_key(*args, *kwargs.values())}"
            result = cache.get(key)
            if result is not None:
                return json.loads(result)
            result = await func(*args, **kwargs)
            cache.set(key, json.dumps(result, default=str), timeout)
            return result
        return wrapper
    return decorator


def invalidate_cache(prefix: str):
    """Invalidate all cache entries for a given prefix (uses delete_pattern with django-redis)."""
    try:
        cache.delete_pattern(f"{prefix}:*")
    except Exception:
        pass  # Graceful degradation if Redis unavailable


def paginate(queryset, page: int = 1, page_size: int = 20):
    """Paginate a Django queryset."""
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    total = queryset.count()
    total_pages = max(1, (total + page_size - 1) // page_size)
    offset = (page - 1) * page_size
    items = list(queryset[offset:offset + page_size])
    return {
        "count": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "results": items,
    }
