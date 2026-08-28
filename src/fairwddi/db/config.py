"""Database configuration and environment resolver for FAIRwDDI.

Supports .env files, DATABASE_URL strings, and discrete PostgreSQL / SQLite environment variables.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse


def load_dotenv_config(env_path: str | Path | None = None) -> None:
    """Load environment variables from a .env file if available."""
    try:
        from dotenv import find_dotenv, load_dotenv

        if env_path:
            load_dotenv(dotenv_path=env_path)
        else:
            dotenv_file = find_dotenv(usecwd=True)
            if dotenv_file:
                load_dotenv(dotenv_path=dotenv_file)
    except ImportError:
        pass


def parse_database_url(url: str) -> dict[str, Any]:
    """Parse a DATABASE_URL into Django DATABASES configuration dictionary."""
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()

    if scheme in ("postgres", "postgresql", "pgsql"):
        engine = "django.db.backends.postgresql"
        dbname = parsed.path.lstrip("/")
        return {
            "ENGINE": engine,
            "NAME": unquote(dbname),
            "USER": unquote(parsed.username or ""),
            "PASSWORD": unquote(parsed.password or ""),
            "HOST": parsed.hostname or "",
            "PORT": str(parsed.port or "5432"),
        }

    if scheme == "sqlite":
        # sqlite:///relative/path or sqlite:////absolute/path or sqlite://:memory:
        db_path = parsed.path
        if not db_path or db_path == "/:memory:":
            db_name = ":memory:"
        elif url.startswith("sqlite:////"):
            db_name = "/" + db_path.lstrip("/")
        else:
            db_name = db_path.lstrip("/")

        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": db_name,
        }

    raise ValueError(f"Unsupported database scheme in DATABASE_URL: '{scheme}'")


def get_database_config() -> dict[str, Any]:
    """Resolve database configuration from environment variables (.env / system).

    Resolution priority:
    1. DATABASE_URL (e.g. postgresql://user:pass@localhost:5432/fairwddi_db)
    2. Discrete PostgreSQL vars (POSTGRES_DB / DB_NAME, POSTGRES_USER, POSTGRES_HOST, etc.)
    3. SQLite file path (FAIRWDDI_DB_PATH or default './fairwddi_dev.sqlite3')
    """
    load_dotenv_config()

    # 1. DATABASE_URL
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        return parse_database_url(database_url)

    # 2. Discrete PostgreSQL environment variables
    pg_db = os.environ.get("POSTGRES_DB") or os.environ.get("DB_NAME")
    if pg_db:
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": pg_db,
            "USER": os.environ.get("POSTGRES_USER") or os.environ.get("DB_USER") or "postgres",
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD") or os.environ.get("DB_PASSWORD") or "",
            "HOST": os.environ.get("POSTGRES_HOST") or os.environ.get("DB_HOST") or "localhost",
            "PORT": os.environ.get("POSTGRES_PORT") or os.environ.get("DB_PORT") or "5432",
        }

    # 3. Default to SQLite development database
    default_sqlite_path = str(Path.cwd() / "fairwddi_dev.sqlite3")
    sqlite_path = (
        os.environ.get("FAIRWDDI_DB_PATH") or os.environ.get("SQLITE_PATH") or default_sqlite_path
    )

    return {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": sqlite_path,
    }


def configure_django_for_cli() -> None:
    """Initialize Django runtime with resolved settings for CLI and standalone use."""
    import django
    from django.conf import settings

    if settings.configured:
        return

    load_dotenv_config()

    settings_module = os.environ.get("DJANGO_SETTINGS_MODULE")
    if settings_module:
        django.setup()
        return

    db_config = get_database_config()

    settings.configure(
        SECRET_KEY=os.environ.get("DJANGO_SECRET_KEY", "fairwddi-cli-default-secret-key"),
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "fairwddi",
        ],
        DATABASES={
            "default": db_config,
        },
        USE_TZ=True,
    )
    django.setup()
