import json
from django.core.cache import cache
from .models import SiteSetting

def get_site_setting(key: str, default=None) -> str:
    """
    Retrieve a site setting by key. 
    Uses Redis cache. Decrypts automatically if marked as secret.
    """
    cache_key = f"site_setting_{key}"
    cached_val = cache.get(cache_key)
    if cached_val is not None:
        return cached_val

    try:
        setting = SiteSetting.objects.get(key=key)
        val = setting.get_value()
        
        # Cache the plaintext value to avoid decryption overhead on every read.
        # In validate/save signals, we should clear this cache key.
        cache.set(cache_key, val, timeout=3600)  # Cache for 1 hour
        return val
    except SiteSetting.DoesNotExist:
        return default
