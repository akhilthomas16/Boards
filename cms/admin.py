from django import forms
from django.contrib import admin

from .models import SiteSetting

MASK = '********'


class SiteSettingForm(forms.ModelForm):
    class Meta:
        model = SiteSetting
        fields = ['key', 'value', 'is_secret']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Never send a stored secret back to the browser.
        if self.instance.pk and self.instance.is_secret and self.instance.value:
            self.initial['value'] = MASK

    def clean_value(self):
        value = self.cleaned_data.get('value')
        # Untouched mask: keep the stored ciphertext.
        if self.instance.pk and self.instance.is_secret and value == MASK:
            return self.instance.value
        return value


@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    form = SiteSettingForm
    list_display = ('key', 'is_secret')
    search_fields = ('key',)
