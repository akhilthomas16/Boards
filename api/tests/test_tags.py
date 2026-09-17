"""Tag normalization. Runs under pytest, or standalone: python api/tests/test_tags.py"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

import django  # noqa: E402

django.setup()

from api.routers.topics import _normalize_tags  # noqa: E402


def test_normalize_tags():
    assert _normalize_tags("Meta, Welcome , meta") == "meta,welcome"  # lowercase, trim, dedupe
    assert _normalize_tags(None) == ""
    assert _normalize_tags("   ") == ""
    assert _normalize_tags("a,,b, A ") == "a,b"
    assert len(_normalize_tags("x" * 300)) == 255  # fits the CharField


if __name__ == '__main__':
    test_normalize_tags()
    print("ok")
