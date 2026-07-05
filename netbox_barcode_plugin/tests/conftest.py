"""Pytest bootstrap for optional NetBox/Django integration tests."""

import os


def pytest_configure():
    """Initialize Django when tests are executed inside a NetBox environment.

    The repository's lightweight local tests do not require Django settings, but
    running the same suite inside a NetBox Docker container usually sets
    ``DJANGO_SETTINGS_MODULE`` without installing pytest-django. In that case
    explicit setup keeps URL/view imports from failing with AppRegistryNotReady.
    """

    if not os.environ.get("DJANGO_SETTINGS_MODULE"):
        return

    try:
        import django
        from django.apps import apps
    except Exception:
        return

    if not apps.ready:
        django.setup()
