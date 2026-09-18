"""
URL configuration for hash_out project.
Django serves only the admin; Next.js serves pages and FastAPI serves JSON.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path('admin/', admin.site.urls),
]

# Uploads are served by the API (FastAPI mounts /media with nosniff headers); this is only so that
# a developer hitting Django directly sees them too.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
