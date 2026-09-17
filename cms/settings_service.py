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

        # Secrets are decrypted on every read rather than cached: Redis would hold them in plaintext.
        if not setting.is_secret:
            cache.set(cache_key, val, timeout=3600)
        return val
    except SiteSetting.DoesNotExist:
        return default
