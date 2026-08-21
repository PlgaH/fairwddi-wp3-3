"""Pytest configuration and minimal Django settings initialization."""

import django
from django.conf import settings


def pytest_configure() -> None:
    """Configure minimal Django settings for unit testing environment."""
    if not settings.configured:
        settings.configure(
            SECRET_KEY="fairwddi-development-test-key-only",
            INSTALLED_APPS=[
                "django.contrib.contenttypes",
                "django.contrib.auth",
            ],
            DATABASES={
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": ":memory:",
                }
            },
            USE_TZ=True,
        )
        django.setup()
