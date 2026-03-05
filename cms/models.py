"""
Wagtail CMS page models.
"""
from django.db import models
from wagtail.models import Page
from wagtail.fields import RichTextField, StreamField
from wagtail.admin.panels import FieldPanel
from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock
from wagtail.snippets.models import register_snippet
from cryptography.fernet import Fernet
from django.conf import settings


class HomePage(Page):
    """CMS-managed home/landing page."""
    hero_title = RichTextField(blank=True)
    hero_subtitle = RichTextField(blank=True)
    body = StreamField([
        ('heading', blocks.CharBlock(form_classname='title')),
        ('paragraph', blocks.RichTextBlock()),
        ('image', ImageChooserBlock()),
        ('quote', blocks.BlockQuoteBlock()),
    ], use_json_field=True, blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('hero_title'),
        FieldPanel('hero_subtitle'),
        FieldPanel('body'),
    ]


class AboutPage(Page):
    """About page with rich text content."""
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]


class BlogIndexPage(Page):
    """Blog listing page."""
    intro = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
    ]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context['posts'] = self.get_children().live().order_by('-first_published_at')
        return context


class BlogPage(Page):
    """Individual blog post page."""
    intro = RichTextField(blank=True)
    body = StreamField([
        ('heading', blocks.CharBlock(form_classname='title')),
        ('paragraph', blocks.RichTextBlock()),
        ('image', ImageChooserBlock()),
        ('code', blocks.TextBlock()),
        ('quote', blocks.BlockQuoteBlock()),
    ], use_json_field=True, blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
        FieldPanel('body'),
    ]


class SiteSetting(models.Model):
    """
    Advanced model for storing generic site configurations.
    Optionally encrypts secrets at rest using Fernet.
    """
    key = models.CharField(max_length=255, unique=True)
    value = models.TextField(blank=True)
    is_secret = models.BooleanField(default=False, help_text="Encrypt data at rest and hide it from unauthorized reads.")
    _is_decrypted = False # Runtime marker

    panels = [
        FieldPanel('key'),
        FieldPanel('value'),
        FieldPanel('is_secret'),
    ]

    def _get_fernet(self):
        f_key = getattr(settings, 'FERNET_KEY', None)
        if not f_key:
            return None
        return Fernet(f_key.encode())

    def get_value(self):
        """Retrieve the plaintext value."""
        if not self.is_secret or not self.value or self._is_decrypted:
            return self.value

        fernet = self._get_fernet()
        if not fernet:
            return self.value

        try:
            return fernet.decrypt(self.value.encode()).decode()
        except Exception:
            return self.value

    def save(self, *args, **kwargs):
        """Encrypt value on save if marked secret."""
        if self.is_secret and self.value:
            if not self.value.startswith("gAAAAA"):  # Fernet tokens generally start with gAAAAA
                fernet = self._get_fernet()
                if fernet:
                    self.value = fernet.encrypt(self.value.encode()).decode()
            
        super().save(*args, **kwargs)
        
        # Clear the cached plaintext to force a read and potential decryption on next access.
        from django.core.cache import cache
        cache.delete(f"site_setting_{self.key}")

    def __str__(self):
        return self.key
