"""Basic tests for fairwddi package initialization and dependencies."""

import dartfx.ddi
import django
import ninja
import psycopg
import pydantic
from typer.testing import CliRunner

import fairwddi
from fairwddi.cli import app

runner = CliRunner()


def test_package_version() -> None:
    """Test package version string."""
    assert fairwddi.__version__ == "0.1.0"


def test_core_dependencies_imported() -> None:
    """Test that core required dependencies are imported properly."""
    assert django.__version__ is not None
    assert ninja.__version__ is not None
    assert psycopg.__version__ is not None
    assert pydantic.__version__ is not None
    assert dartfx.ddi is not None


def test_cli_version() -> None:
    """Test CLI version command and --version flag output."""
    result_cmd = runner.invoke(app, ["version"])
    assert result_cmd.exit_code == 0
    assert "fairwddi version 0.1.0" in result_cmd.stdout

    result_flag = runner.invoke(app, ["--version"])
    assert result_flag.exit_code == 0
    assert "fairwddi version 0.1.0" in result_flag.stdout


def test_cli_info() -> None:
    """Test CLI info command output."""
    result = runner.invoke(app, ["info"])
    assert result.exit_code == 0
    assert "FAIRwDDI Lifecycle" in result.stdout
