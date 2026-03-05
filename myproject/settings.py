"""
Django settings for myproject project.
Full-stack configuration: PostgreSQL, Redis, Elasticsearch, Wagtail, Celery, CORS.
"""

import os
from pathlib import Path
from decouple import config, Csv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# =============================================================================
# CORE
# =============================================================================

SECRET_KEY = config('SECRET_KEY', default='django-insecure-dev-only')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())
FERNET_KEY = config('FERNET_KEY', default='RVkCS56oEi2gJ9XVJFX1ds_uv7bCV0js1zvKCsPAhTk=')


# =============================================================================
# INSTALLED APPS
# =============================================================================

INSTALLED_APPS = [
    # Wagtail (must be before django.contrib.admin)
    'wagtail.contrib.forms',
    'wagtail.contrib.redirects',
    'wagtail.embeds',
    'wagtail.sites',
    'wagtail.users',
    'wagtail.snippets',
    'wagtail.documents',
    'wagtail.images',
    'wagtail.search',
    'wagtail.admin',
    'wagtail',
    'modelcluster',
    'taggit',

    # Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'corsheaders',
    'widget_tweaks',
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
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'wagtail.contrib.redirects.middleware.RedirectMiddleware',
]

ROOT_URLCONF = 'myproject.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates')
        ],
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

WSGI_APPLICATION = 'myproject.wsgi.application'


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


# =============================================================================
# CORS (for Next.js frontend)
# =============================================================================

CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:3000',
    cast=Csv()
)
CORS_ALLOW_CREDENTIALS = True


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

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'


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
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# =============================================================================
# WAGTAIL
# =============================================================================

WAGTAIL_SITE_NAME = config('WAGTAIL_SITE_NAME', default='Boards CMS')
WAGTAILADMIN_BASE_URL = 'http://localhost:8000'
WAGTAILSEARCH_BACKENDS = {
    'default': {
        'BACKEND': 'wagtail.search.backends.database',
    }
}


# =============================================================================
# EMAIL
# =============================================================================

EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')


# =============================================================================
# MISC
# =============================================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
