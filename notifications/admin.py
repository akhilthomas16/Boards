from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'actor', 'message', 'is_read', 'created_at')
    list_filter = ('is_read',)
    list_select_related = ('recipient', 'actor')
    raw_id_fields = ('recipient', 'actor')
