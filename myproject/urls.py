"""
URL configuration for myproject project.
Routes: Django admin, Wagtail CMS, board views.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from wagtail.admin import urls as wagtailadmin_urls
from wagtail import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls

urlpatterns = [
    # Django admin
    path('admin/', admin.site.urls),

    # Wagtail CMS admin
    path('cms-admin/', include(wagtailadmin_urls)),
    path('documents/', include(wagtaildocs_urls)),

    # Board app routes
    path('', include('boards.urls')),

    # Wagtail pages (catch-all, must be last)
    path('pages/', include(wagtail_urls)),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
