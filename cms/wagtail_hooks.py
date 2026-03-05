from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet
from wagtail import hooks
from django.contrib import admin
from django import forms
from django.forms import Media
from django.utils.safestring import mark_safe
from .models import SiteSetting
from django.contrib.auth import get_user_model
from boards.models import Board, Topic, Post

class SiteSettingForm(forms.ModelForm):
    class Meta:
        model = SiteSetting
        fields = ['key', 'value', 'is_secret']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If the setting is secret and it already has a value, mask it in the admin UI
        if self.instance and self.instance.pk and self.instance.is_secret and self.instance.value:
            self.initial['value'] = '********'

    def clean_value(self):
        value = self.cleaned_data.get('value')
        # If the setting is secretly masked and the admin didn't change the mask,
        # preserve the original encrypted string from the database.
        if self.instance and self.instance.pk and self.instance.is_secret:
            if value == '********':
                return self.instance.value
        return value

class SiteSettingViewSet(SnippetViewSet):
    model = SiteSetting
    menu_label = 'Site Settings'
    menu_icon = 'cogs'
    list_display = ('key', 'is_secret')
    search_fields = ('key',)
    form_class = SiteSettingForm

register_snippet(SiteSettingViewSet)

# --- Custom Admin Dashboard Panels ---

class SiteActivityPanel:
    order = 100
    media = Media()

    def render(self):
        User = get_user_model()
        user_count = User.objects.count()
        board_count = Board.objects.count()
        topic_count = Topic.objects.count()
        post_count = Post.objects.count()

        html = f"""
        <section class="panel summary nice-padding">
            <h2 class="title-wrapper">Site Activity</h2>
            <div class="panel-body">
                <ul class="stats">
                    <li style="margin-bottom: 0.5rem;"><strong>Users:</strong> {user_count}</li>
                    <li style="margin-bottom: 0.5rem;"><strong>Boards:</strong> {board_count}</li>
                    <li style="margin-bottom: 0.5rem;"><strong>Topics:</strong> {topic_count}</li>
                    <li style="margin-bottom: 0.5rem;"><strong>Posts:</strong> {post_count}</li>
                </ul>
            </div>
        </section>
        """
        return mark_safe(html)


class AnalyticsPanel:
    order = 110
    media = Media()

    def render(self):
        # In a real app, you might fetch from an external API or calculate from local models.
        # Here we mock it for demonstration or pull from settings.
        try:
            from cms.settings_service import get_site_setting
            monthly_revenue = get_site_setting('ad_revenue_mtd', default='$0.00')
            active_users = get_site_setting('active_users_mtd', default='0')
        except Exception:
            monthly_revenue = '$0.00'
            active_users = '0'

        html = f"""
        <section class="panel summary nice-padding">
            <h2 class="title-wrapper">Analytics & Revenue</h2>
            <div class="panel-body">
                <div style="background: var(--w-color-surface-hover); padding: 1rem; border-radius: 4px; margin-bottom: 1rem;">
                    <h3 style="margin-top: 0; color: var(--w-color-text-context);">Estimated Revenue (MTD)</h3>
                    <p style="font-size: 2rem; margin: 0; font-weight: bold; color: var(--w-color-success);">{monthly_revenue}</p>
                </div>
                <div style="background: var(--w-color-surface-hover); padding: 1rem; border-radius: 4px;">
                    <h3 style="margin-top: 0; color: var(--w-color-text-context);">Active Users (MTD)</h3>
                    <p style="font-size: 2rem; margin: 0; font-weight: bold;">{active_users}</p>
                </div>
            </div>
        </section>
        """
        return mark_safe(html)


class RecentActivityPanel:
    order = 120
    media = Media()

    def render(self):
        recent_topics = Topic.objects.order_by('-last_updated')[:5]
        
        items_html = ""
        from django.utils.html import escape
        from django.utils.timesince import timesince

        for topic in recent_topics:
            items_html += f"""
            <li style="padding: 0.5rem 0; border-bottom: 1px solid var(--w-color-border-furniture);">
                <strong>{escape(topic.subject)}</strong> 
                <br>
                <small style="color: var(--w-color-text-context);">
                    Started by {escape(topic.starter.username)} in {escape(topic.board.name)} 
                    ({timesince(topic.last_updated)} ago)
                </small>
            </li>
            """

        html = f"""
        <section class="panel summary nice-padding">
            <h2 class="title-wrapper">Recent Forum Topics</h2>
            <div class="panel-body">
                <ul style="list-style-type: none; padding-left: 0; margin-top: 0;">
                    {items_html if items_html else '<li>No topics yet.</li>'}
                </ul>
            </div>
        </section>
        """
        return mark_safe(html)


@hooks.register('construct_homepage_panels')
def add_custom_homepage_panels(request, panels):
    panels.append(SiteActivityPanel())
    panels.append(AnalyticsPanel())
    panels.append(RecentActivityPanel())
