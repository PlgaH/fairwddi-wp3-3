"""Tests for FAIRwDDI CLI database commands and configuration resolution."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from typer.testing import CliRunner

from fairwddi.cli import app
from fairwddi.db.config import get_database_config, parse_database_url

runner = CliRunner()


def test_parse_database_url_postgresql() -> None:
    """Test parsing PostgreSQL DATABASE_URL into Django DATABASES settings."""
    url = "postgresql://myuser:secretpass@db.example.org:5433/fairwddi_prod"
    cfg = parse_database_url(url)
    assert cfg["ENGINE"] == "django.db.backends.postgresql"
    assert cfg["NAME"] == "fairwddi_prod"
    assert cfg["USER"] == "myuser"
    assert cfg["PASSWORD"] == "secretpass"
    assert cfg["HOST"] == "db.example.org"
    assert cfg["PORT"] == "5433"


def test_parse_database_url_sqlite() -> None:
    """Test parsing SQLite DATABASE_URL."""
    url = "sqlite:///custom/path/db.sqlite3"
    cfg = parse_database_url(url)
    assert cfg["ENGINE"] == "django.db.backends.sqlite3"
    assert cfg["NAME"] == "custom/path/db.sqlite3"


def test_get_database_config_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test discrete PostgreSQL environment variable resolution."""
    monkeypatch.setenv("POSTGRES_DB", "cdsp_request")
    monkeypatch.setenv("POSTGRES_USER", "cdsp_admin")
    monkeypatch.setenv("POSTGRES_PASSWORD", "topsecret")
    monkeypatch.setenv("POSTGRES_HOST", "postgres.cdsp.internal")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    # Make sure DATABASE_URL is unset
    monkeypatch.delenv("DATABASE_URL", raising=False)

    cfg = get_database_config()
    assert cfg["ENGINE"] == "django.db.backends.postgresql"
    assert cfg["NAME"] == "cdsp_request"
    assert cfg["USER"] == "cdsp_admin"
    assert cfg["PASSWORD"] == "topsecret"
    assert cfg["HOST"] == "postgres.cdsp.internal"


def test_cli_info() -> None:
    """Test fairwddi info outputs environment details."""
    result = runner.invoke(app, ["info"])
    assert result.exit_code == 0
    assert "FAIRwDDI Lifecycle" in result.stdout
    assert "Active DB Engine" in result.stdout


def test_cli_db_export_ddl_stdout() -> None:
    """Test that fairwddi db export-ddl prints valid PostgreSQL DDL SQL."""
    result = runner.invoke(app, ["db", "export-ddl"])
    assert result.exit_code == 0
    assert "CREATE TABLE IF NOT EXISTS request_ddi_distributor" in result.stdout
    assert "CREATE TABLE IF NOT EXISTS request_ddi_questionitem" in result.stdout
    assert "CREATE TABLE IF NOT EXISTS request_ddi_codelist" in result.stdout
    assert "CREATE TABLE IF NOT EXISTS request_ddi_studyunit" in result.stdout
    assert "CREATE TABLE IF NOT EXISTS request_ddi_stagedresourcenode" in result.stdout


def test_cli_db_export_ddl_file() -> None:
    """Test exporting DDL to a destination file."""
    with TemporaryDirectory() as tmpdir:
        output_file = Path(tmpdir) / "test_init.sql"
        result = runner.invoke(app, ["db", "export-ddl", "--output", str(output_file)])
        assert result.exit_code == 0
        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")
        assert "CREATE TABLE IF NOT EXISTS request_ddi_distributor" in content


@pytest.mark.django_db
def test_cli_db_init() -> None:
    """Test fairwddi db init runs migrations successfully."""
    result = runner.invoke(app, ["db", "init"])
    assert result.exit_code == 0
    assert "Database initialized successfully" in result.stdout


@pytest.mark.django_db
def test_cli_db_seed() -> None:
    """Test fairwddi db seed populates demonstration records."""
    result = runner.invoke(app, ["db", "seed"])
    assert result.exit_code == 0
    assert "Database seeded successfully" in result.stdout
    assert "Demonstration Data Seed Summary" in result.stdout

    # Test seed with reset option
    reset_result = runner.invoke(app, ["db", "seed", "--reset"])
    assert reset_result.exit_code == 0
    assert "Database seeded successfully" in reset_result.stdout


@pytest.mark.django_db
def test_cli_db_status() -> None:
    """Test fairwddi db status displays table inventory table."""
    result = runner.invoke(app, ["db", "status"])
    assert result.exit_code == 0
    assert "FAIRwDDI Model Inventory" in result.stdout
    assert "QuestionItem" in result.stdout
    assert "RepresentedVariable" in result.stdout
