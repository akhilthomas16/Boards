"""
Django settings for hash_out project.
Full-stack configuration: PostgreSQL, Redis, Elasticsearch, Celery.
"""

import os
from pathlib import Path
from decouple import config, Csv
from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# =============================================================================
# CORE
# =============================================================================

SECRET_KEY = config('SECRET_KEY', default='django-insecure-dev-only')
DEBUG = config('DEBUG', default=True, cast=bool)
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

    # Third-party
    'django_elasticsearch_dsl',

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

import dj_database_url

DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL', default='postgres://boards_user:boards_pass@localhost:5432/boards_db')
    )
}


# =============================================================================
# REDIS CACHE
# =============================================================================

REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'TIMEOUT': 300,
    }
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'


# =============================================================================
# ELASTICSEARCH
# =============================================================================

ELASTICSEARCH_DSL = {
    'default': {
        'hosts': config('ELASTICSEARCH_URL', default='http://localhost:9200'),
    },
}

# Writes must not depend on Elasticsearch being reachable. The default
# RealTimeSignalProcessor bulk-indexes inside every Board/Topic/Post save.
ELASTICSEARCH_DSL_AUTOSYNC = config('ELASTICSEARCH_DSL_AUTOSYNC', default=False, cast=bool)


# =============================================================================
# CELERY
# =============================================================================

CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/1')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/2')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_TRACK_STARTED = True


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
# GOOGLE ADS
# =============================================================================

GOOGLE_ADSENSE_CLIENT_ID = config('GOOGLE_ADSENSE_CLIENT_ID', default='')
GOOGLE_ADSENSE_SLOT_BANNER = config('GOOGLE_ADSENSE_SLOT_BANNER', default='')
GOOGLE_ADSENSE_SLOT_SIDEBAR = config('GOOGLE_ADSENSE_SLOT_SIDEBAR', default='')
GOOGLE_ADSENSE_SLOT_INFEED = config('GOOGLE_ADSENSE_SLOT_INFEED', default='')


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

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# =============================================================================
# EMAIL
# =============================================================================

EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')


# =============================================================================
# MISC
# =============================================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
