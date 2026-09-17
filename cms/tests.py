"""SiteSetting secret handling. DB-free: runs without a test database."""
from unittest import mock

import pytest
from cryptography.fernet import Fernet, InvalidToken
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from cms.models import SiteSetting
from cms.settings_service import get_site_setting

KEY = Fernet.generate_key().decode()


def _secret(plaintext, key=KEY):
    return SiteSetting(key='api_token', is_secret=True,
                       value=Fernet(key.encode()).encrypt(plaintext.encode()).decode())


@override_settings(FERNET_KEY=KEY)
def test_secret_decrypts_with_configured_key():
    assert _secret('hunter2').get_value() == 'hunter2'


@override_settings(FERNET_KEY='')
def test_secret_without_key_raises_instead_of_returning_ciphertext():
    with pytest.raises(ImproperlyConfigured):
        _secret('hunter2').get_value()


@override_settings(FERNET_KEY=Fernet.generate_key().decode())
def test_secret_under_wrong_key_raises_instead_of_returning_ciphertext():
    with pytest.raises(InvalidToken):
        _secret('hunter2').get_value()


@override_settings(FERNET_KEY='')
def test_plain_setting_needs_no_key():
    assert SiteSetting(key='site_name', value='Boards').get_value() == 'Boards'


@override_settings(FERNET_KEY=KEY)
def test_decrypted_secret_is_never_cached():
    with mock.patch.object(SiteSetting.objects, 'get', return_value=_secret('hunter2')), \
         mock.patch('cms.settings_service.cache') as cache:
        cache.get.return_value = None
        assert get_site_setting('api_token') == 'hunter2'
    cache.set.assert_not_called()


@override_settings(FERNET_KEY=KEY)
def test_plain_setting_is_cached():
    with mock.patch.object(SiteSetting.objects, 'get',
                           return_value=SiteSetting(key='site_name', value='Boards')), \
         mock.patch('cms.settings_service.cache') as cache:
        cache.get.return_value = None
        assert get_site_setting('site_name') == 'Boards'
    cache.set.assert_called_once()
