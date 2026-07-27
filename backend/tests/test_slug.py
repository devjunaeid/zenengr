"""Slug validation tests."""

from app.utils.slug import validate_slug


def test_slug_accepts_lowercase():
    assert validate_slug("acmecorp") is True


def test_slug_accepts_hyphenated():
    assert validate_slug("acme-corp") is True
    assert validate_slug("my-tenant-123") is True


def test_slug_accepts_numbers():
    assert validate_slug("tenant42") is True


def test_slug_rejects_leading_hyphen():
    assert validate_slug("-acme") is False


def test_slug_rejects_trailing_hyphen():
    assert validate_slug("acme-") is False


def test_slug_rejects_double_hyphen():
    assert validate_slug("acme--corp") is False


def test_slug_rejects_uppercase():
    assert validate_slug("AcmeCorp") is False


def test_slug_rejects_special_chars():
    assert validate_slug("acme_corp") is False
    assert validate_slug("acme corp") is False
    assert validate_slug("acme!corp") is False


def test_slug_rejects_empty():
    assert validate_slug("") is False
