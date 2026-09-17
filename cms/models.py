"""
Site settings, editable in /admin/. Secret values are Fernet-encrypted at rest.
"""
from cryptography.fernet import Fernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models


class SiteSetting(models.Model):
    """
    Advanced model for storing generic site configurations.
    Optionally encrypts secrets at rest using Fernet.
    """
    key = models.CharField(max_length=255, unique=True)
    value = models.TextField(blank=True)
    is_secret = models.BooleanField(default=False, help_text="Encrypt data at rest and hide it from unauthorized reads.")
    _is_decrypted = False # Runtime marker

    def _get_fernet(self):
        if not settings.FERNET_KEY:
            raise ImproperlyConfigured("FERNET_KEY is required to store or read secret settings")
        return Fernet(settings.FERNET_KEY.encode())

    def get_value(self):
        """Retrieve the plaintext value."""
        if not self.is_secret or not self.value or self._is_decrypted:
            return self.value

        # A wrong key or corrupt token raises InvalidToken: never pass ciphertext off as the value.
        return self._get_fernet().decrypt(self.value.encode()).decode()

    def save(self, *args, **kwargs):
        """Encrypt value on save if marked secret."""
        if self.is_secret and self.value:
            if not self.value.startswith("gAAAAA"):  # Fernet tokens generally start with gAAAAA
                self.value = self._get_fernet().encrypt(self.value.encode()).decode()

        super().save(*args, **kwargs)
        
        # Clear the cached plaintext to force a read and potential decryption on next access.
        from django.core.cache import cache
        cache.delete(f"site_setting_{self.key}")

    def __str__(self):
        return self.key
