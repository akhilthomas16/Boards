from django.conf import settings
from slowapi import Limiter
from slowapi.util import get_remote_address

# Redis-backed so limits survive restarts and apply across workers.
# ponytail: keyed on the socket peer; behind a reverse proxy, run uvicorn with --forwarded-allow-ips.
limiter = Limiter(key_func=get_remote_address, storage_uri=settings.REDIS_URL)
