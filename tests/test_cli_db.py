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


@pytest.mark.django_db
def test_cli_db_wipe_prompt_confirm() -> None:
    """Test fairwddi db wipe with interactive string confirmation 'WIPE'."""
    runner.invoke(app, ["db", "seed"])
    result = runner.invoke(app, ["db", "wipe"], input="WIPE\n")
    assert result.exit_code == 0
    assert "Database wiped successfully" in result.stdout


@pytest.mark.django_db
def test_cli_db_wipe_prompt_reject() -> None:
    """Test fairwddi db wipe aborts when confirmation is not 'WIPE'."""
    runner.invoke(app, ["db", "seed"])
    result = runner.invoke(app, ["db", "wipe"], input="NO\n")
    assert result.exit_code != 0
    assert "Aborted" in result.stdout


@pytest.mark.django_db
def test_cli_db_wipe_confirm_flag() -> None:
    """Test fairwddi db wipe with --confirm WIPE flag."""
    runner.invoke(app, ["db", "seed"])
    result = runner.invoke(app, ["db", "wipe", "--confirm", "WIPE"])
    assert result.exit_code == 0
    assert "Database wiped successfully" in result.stdout


@pytest.mark.django_db
def test_cli_db_wipe_force() -> None:
    """Test fairwddi db wipe --force bypasses confirmation."""
    runner.invoke(app, ["db", "seed"])
    result = runner.invoke(app, ["db", "wipe", "--force"])
    assert result.exit_code == 0
    assert "Database wiped successfully" in result.stdout


@pytest.mark.django_db
def test_cli_db_check_vocab() -> None:
    """Test fairwddi db check-vocab command."""
    # Initially empty
    result = runner.invoke(app, ["db", "check-vocab", "--vocabulary", "ELSST"])
    assert result.exit_code == 0
    assert "NOT loaded" in result.stdout


@pytest.mark.django_db
def test_cli_db_load_vocab_level_1() -> None:
    """Test loading vocabulary level 1 (top concepts) from ELSST_R6.ttl."""
    vocab_path = Path(__file__).resolve().parent.parent / "vocab" / "ELSST_R6.ttl"
    if not vocab_path.exists():
        pytest.skip("vocab/ELSST_R6.ttl not present in workspace")

    # Load level 1 only
    result = runner.invoke(
        app,
        ["db", "load-vocab", str(vocab_path), "--levels", "1", "--reload"],
    )
    assert result.exit_code == 0
    assert "loaded successfully" in result.stdout
    assert "Top Concepts (Level 1)" in result.stdout

    # Test checking status after load
    check_res = runner.invoke(app, ["db", "check-vocab", "--vocabulary", "ELSST"])
    assert check_res.exit_code == 0
    assert "is LOADED" in check_res.stdout

    # Test already loaded check without reload
    already_res = runner.invoke(app, ["db", "load-vocab", str(vocab_path)])
    assert already_res.exit_code == 0
    assert "already loaded" in already_res.stdout


@pytest.mark.django_db
def test_cli_db_load_generic_skos_vocab() -> None:
    """Test loading a custom generic SKOS vocabulary in RDF Turtle format."""
    skos_content = """
    @prefix skos: <http://www.w3.org/2004/02/skos/core#> .
    @prefix dct: <http://purl.org/dc/terms/> .

    <http://example.org/topics/scheme> a skos:ConceptScheme ;
        dct:title "Custom CESSDA Topics"@en ;
        skos:hasTopConcept <http://example.org/topics/politics> .

    <http://example.org/topics/politics> a skos:Concept ;
        skos:prefLabel "Politics"@en, "Politique"@fr ;
        skos:definition "Political system, governance and political behavior."@en ;
        skos:topConceptOf <http://example.org/topics/scheme> ;
        skos:narrower <http://example.org/topics/elections> .

    <http://example.org/topics/elections> a skos:Concept ;
        skos:prefLabel "Elections"@en, "Élections"@fr ;
        skos:broader <http://example.org/topics/politics> ;
        skos:inScheme <http://example.org/topics/scheme> .
    """
    with TemporaryDirectory() as tmpdir:
        ttl_file = Path(tmpdir) / "custom_topics.ttl"
        ttl_file.write_text(skos_content, encoding="utf-8")

        result = runner.invoke(
            app,
            ["db", "load-vocab", str(ttl_file), "--vocabulary", "CustomTopics", "--levels", "2"],
        )
        assert result.exit_code == 0
        assert "loaded successfully" in result.stdout
        assert "Total Concepts Loaded" in result.stdout
        assert "2" in result.stdout
