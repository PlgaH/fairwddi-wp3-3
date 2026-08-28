"""Pytest configuration and Django test settings initialization for FAIRwDDI."""

import django
from django.conf import settings
from django.core.management import call_command


def pytest_configure() -> None:
    """Configure Django settings and apply initial database migrations for tests."""
    if not settings.configured:
        settings.configure(
            SECRET_KEY="fairwddi-development-test-key-only",
            INSTALLED_APPS=[
                "django.contrib.contenttypes",
                "django.contrib.auth",
                "fairwddi",
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
        call_command("migrate", interactive=False, verbosity=0)
