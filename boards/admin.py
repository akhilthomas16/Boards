from django.contrib import admin

from .models import Board, Post, Reaction, Topic

admin.site.site_header = admin.site.site_title = "Hash Out admin"

admin.site.register(Board)


# ponytail: /admin/ is the moderation console until the API grows staff endpoints (Phase 6).
@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ('subject', 'board', 'starter', 'is_pinned', 'is_locked', 'last_updated')
    list_editable = ('is_pinned', 'is_locked')
    list_filter = ('board', 'is_pinned', 'is_locked')
    list_select_related = ('board', 'starter')
    search_fields = ('subject',)
    raw_id_fields = ('starter',)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'topic', 'created_by', 'created_at')
    list_select_related = ('topic', 'created_by')
    search_fields = ('message',)
    raw_id_fields = ('topic', 'created_by', 'updated_by')


@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ('post', 'user', 'emoji', 'created_at')
    raw_id_fields = ('post', 'user')
