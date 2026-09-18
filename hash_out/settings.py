"""
Django settings for hash_out project.
Configuration: PostgreSQL, Redis, JWT, email.
"""

import os
from pathlib import Path

import dj_database_url
from decouple import Csv, config
from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# =============================================================================
# CORE
# =============================================================================

SECRET_KEY = config('SECRET_KEY', default='django-insecure-dev-only')
DEBUG = config('DEBUG', default=False, cast=bool)  # production default; dev sets DEBUG=True in .env
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())
FERNET_KEY = config('FERNET_KEY', default='')


# =============================================================================
# INSTALLED APPS
# =============================================================================

INSTALLED_APPS = [
    # Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Project apps
    'accounts',
    'boards',
    'cms',
    'notifications',
]


# =============================================================================
# MIDDLEWARE
# =============================================================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # serves /static/ for the admin in production
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'hash_out.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'hash_out.wsgi.application'


# =============================================================================
# DATABASE — PostgreSQL
# =============================================================================

DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL', default='postgres://boards_user:boards_pass@localhost:5432/boards_db')
    )
}


# =============================================================================
# REDIS CACHE
# =============================================================================

# Redis is not optional: sessions, the OTP store, rate-limit counters and notification pub/sub.
# Without it (tests, a bare checkout) fall back to local memory — single process, not shared.
REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'TIMEOUT': 300,
    } if REDIS_URL else {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'


# =============================================================================
# JWT
# =============================================================================

JWT_SECRET_KEY = config('JWT_SECRET_KEY', default='change-me-jwt-secret')
JWT_ALGORITHM = config('JWT_ALGORITHM', default='HS256')
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = config('JWT_ACCESS_TOKEN_EXPIRE_MINUTES', default=30, cast=int)
JWT_REFRESH_TOKEN_EXPIRE_DAYS = config('JWT_REFRESH_TOKEN_EXPIRE_DAYS', default=7, cast=int)

# Browser origins allowed to call the API with cookies (CORS + WebSocket Origin check).
# Must be same-site with the API host, or SameSite=Lax cookies are never sent.
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='http://localhost:3000', cast=Csv())

# Never run with DEBUG off on the dev defaults above or the env.sample placeholders.
if not DEBUG:
    for _name in ('SECRET_KEY', 'JWT_SECRET_KEY', 'FERNET_KEY'):
        _value = globals()[_name]
        if not _value or _value.startswith(('django-insecure', 'change-me', 'your-')):
            raise ImproperlyConfigured(f"{_name} must be a real secret when DEBUG=False")


# =============================================================================
# LLM
# =============================================================================

OPENAI_API_KEY = config('OPENAI_API_KEY', default='')
OPENAI_MODEL = config('OPENAI_MODEL', default='gpt-4o-mini')
OPENAI_BASE_URL = config('OPENAI_BASE_URL', default='https://api.openai.com/v1')


# =============================================================================
# AUTH
# =============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# =============================================================================
# INTERNATIONALIZATION
# =============================================================================

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# =============================================================================
# STATIC & MEDIA FILES
# =============================================================================

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    # Hashed filenames + long cache headers for the admin's CSS/JS.
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# =============================================================================
# EMAIL
# =============================================================================

EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='Hash Out <noreply@localhost>')
EMAIL_HOST = config('EMAIL_HOST', default='localhost')
EMAIL_PORT = config('EMAIL_PORT', default=25, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=False, cast=bool)


# =============================================================================
# PRODUCTION HARDENING
# =============================================================================

if not DEBUG:
    # The proxy terminates TLS and tells us so; without this Django sees plain HTTP and redirects forever.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
    SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=60 * 60 * 24 * 365, cast=int)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'same-origin'
    X_FRAME_OPTIONS = 'DENY'
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_HTTPONLY = True
    CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())


# =============================================================================
# MISC
# =============================================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
