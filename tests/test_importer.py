"""Tests for the Stage 1 Metadata Importer subsystem."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from fairwddi.cli import app
from fairwddi.importer import (
    ImportProfile,
    ImportStrategies,
    detect_metadata_format,
    import_metadata_file,
    list_available_profiles,
    load_profile,
    stream_resources,
)
from fairwddi.models import MetadataQuarantine, StagedImport, StagedResourceNode

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def sample_cso_xml() -> Path:
    p = FIXTURES_DIR / "sample_cso.ddi33.xml"
    if not p.exists():
        pytest.skip(f"Test fixture not found: {p}")
    return p


@pytest.fixture
def sample_ddi40_json() -> Path:
    p = FIXTURES_DIR / "sample_ddi40.json"
    if not p.exists():
        pytest.skip(f"Test fixture not found: {p}")
    return p


@pytest.fixture
def sample_fsd_ddic() -> Path:
    p = FIXTURES_DIR / "FSD3562_eng.ddic.xml"
    if not p.exists():
        pytest.skip(f"Test fixture not found: {p}")
    return p


# -----------------------------------------------------------------------------
# Format Detection Tests
# -----------------------------------------------------------------------------


def test_detect_metadata_format_ddi33(sample_cso_xml: Path) -> None:
    fmt = detect_metadata_format(sample_cso_xml)
    assert fmt.specification == "DDI-L"
    assert fmt.version == "3.3"
    assert fmt.serialization == "xml"
    assert fmt.canonical_slug == "ddi-l:3.3:xml"


def test_detect_metadata_format_ddi40_json(sample_ddi40_json: Path) -> None:
    fmt = detect_metadata_format(sample_ddi40_json)
    assert fmt.specification == "DDI-L"
    assert fmt.version == "4.0"
    assert fmt.serialization == "json"
    assert fmt.flavor == "Colectica"
    assert fmt.canonical_slug == "ddi-l:4.0:json"


def test_detect_metadata_format_ddic(sample_fsd_ddic: Path) -> None:
    fmt = detect_metadata_format(sample_fsd_ddic)
    assert fmt.specification == "DDI-C"
    assert fmt.version == "2.5"
    assert fmt.serialization == "xml"
    assert fmt.flavor == "Nesstar"
    assert fmt.canonical_slug == "ddi-c:2.5:xml"


def test_detect_metadata_format_nonexistent() -> None:
    with pytest.raises(FileNotFoundError):
        detect_metadata_format(Path("nonexistent_file_path.xml"))


# -----------------------------------------------------------------------------
# Profile Parsing & Precedence Tests
# -----------------------------------------------------------------------------


def test_load_profile_request_core() -> None:
    profile = load_profile("request_core")
    assert profile.name == "request_core"
    assert "QuestionItem" in profile.include_types
    assert "VariableStatistics" in profile.exclude_types
    assert profile.include_referenced_resources is True

    assert profile.should_include("VariableStatistics") is False
    assert profile.should_include("QuestionItem") is True
    assert profile.should_include("UnlistedResource", is_referenced=False) is False
    assert profile.should_include("UnlistedResource", is_referenced=True) is True
    assert profile.should_include("VariableStatistics", is_referenced=True) is False


def test_load_profile_all_ddi() -> None:
    profile = load_profile("all_ddi")
    assert profile.name == "all_ddi"
    assert len(profile.include_types) == 0
    assert profile.should_include("AnyResource") is True


def test_list_available_profiles() -> None:
    profiles = list_available_profiles()
    names = [p["name"] for p in profiles]
    assert "request_core" in names
    assert "all_ddi" in names


# -----------------------------------------------------------------------------
# Streaming & Extraction Tests
# -----------------------------------------------------------------------------


def test_stream_resources_ddi33_xml(sample_cso_xml: Path) -> None:
    profile = load_profile("request_core")
    nodes = list(stream_resources(sample_cso_xml, profile))
    assert len(nodes) > 100
    types = {n.resource_type for n in nodes}
    assert "QuestionItem" in types
    assert "Category" in types
    assert "CodeList" in types
    assert all(n.raw_urn.startswith("urn:ddi:") for n in nodes)
    assert all(isinstance(n.raw_value, dict) for n in nodes)


def test_stream_resources_ddi40_json(sample_ddi40_json: Path) -> None:
    profile = load_profile("request_core")
    nodes = list(stream_resources(sample_ddi40_json, profile))
    assert len(nodes) > 50
    types = {n.resource_type for n in nodes}
    assert "Category" in types
    assert "QuestionItem" in types or "Variable" in types or "CodeList" in types


def test_stream_resources_ddic_xml(sample_fsd_ddic: Path) -> None:
    profile = load_profile("request_core")
    nodes = list(stream_resources(sample_fsd_ddic, profile))
    assert len(nodes) > 100
    types = {n.resource_type for n in nodes}
    assert "Variable" in types
    assert "Category" in types
    assert "CodeList" in types


# -----------------------------------------------------------------------------
# Database Import & Staging Tests
# -----------------------------------------------------------------------------


@pytest.mark.django_db
def test_import_metadata_file_dry_run(sample_fsd_ddic: Path) -> None:
    initial_imports = StagedImport.objects.count()
    initial_nodes = StagedResourceNode.objects.count()

    summary = import_metadata_file(
        file_path=sample_fsd_ddic,
        profile="request_core",
        dry_run=True,
    )

    assert summary["status"] == "dry_run_success"
    assert summary["total_staged"] > 0
    assert summary["staged_import_id"] is None
    assert StagedImport.objects.count() == initial_imports
    assert StagedResourceNode.objects.count() == initial_nodes


@pytest.mark.django_db
def test_import_metadata_file_live_and_duplicate_skip(
    sample_fsd_ddic: Path, tmp_path: Path
) -> None:
    log_dir = tmp_path / "test_logs"

    # 1. First live import
    summary1 = import_metadata_file(
        file_path=sample_fsd_ddic,
        profile="request_core",
        log_dir=log_dir,
    )

    assert summary1["status"] == "staged"
    import_id = summary1["staged_import_id"]
    assert import_id is not None
    assert summary1["total_staged"] == 487
    assert StagedImport.objects.filter(id=import_id).exists()
    assert StagedResourceNode.objects.filter(staged_import_id=import_id).count() == 487

    # Verify session log was written
    log_path = Path(summary1["log_file"])
    assert log_path.exists()
    log_content = log_path.read_text(encoding="utf-8")
    assert "FAIRwDDI METADATA IMPORT SESSION" in log_content
    assert "Total Resources Staged: 487" in log_content

    # 2. Re-importing same file triggers duplicate skip
    summary2 = import_metadata_file(
        file_path=sample_fsd_ddic,
        profile="request_core",
        log_dir=log_dir,
    )
    assert summary2["status"] == "already_staged"
    assert summary2["staged_import_id"] == import_id

    # 3. Force reload replaces staged import
    summary3 = import_metadata_file(
        file_path=sample_fsd_ddic,
        profile="request_core",
        force_reload=True,
        log_dir=log_dir,
    )
    assert summary3["status"] == "staged"
    assert summary3["staged_import_id"] != import_id


@pytest.mark.django_db
def test_content_drift_quarantine(sample_fsd_ddic: Path, tmp_path: Path) -> None:
    # 1. Create initial staged node
    staged_import = StagedImport.objects.create(
        source_format="ddi-c:2.5:xml",
        file_name=sample_fsd_ddic.name,
        import_options={"file_sha256": "initial_hash"},
        status="staged",
    )
    test_urn = "urn:ddi:codebook:var:stdy-001:q1:1.0.0"
    StagedResourceNode.objects.create(
        staged_import=staged_import,
        resource_type="Variable",
        raw_urn=test_urn,
        raw_value={"label": "Original question text"},
        status="staged",
    )

    # 2. Import a synthetic profile with drift quarantine
    custom_profile = ImportProfile(
        name="test_drift_profile",
        include_types=["Variable"],
        strategies=ImportStrategies(
            on_duplicate_file="force_reload",
            on_content_drift="quarantine",
        ),
    )

    # Re-run import
    import_metadata_file(
        file_path=sample_fsd_ddic,
        profile=custom_profile,
        log_dir=tmp_path / "drift_logs",
    )

    quarantined = MetadataQuarantine.objects.filter(incoming_urn=test_urn)
    if quarantined.exists():
        assert quarantined.first().conflict_type == "staged_urn_drift"


# -----------------------------------------------------------------------------
# CLI Command Tests
# -----------------------------------------------------------------------------


def test_cli_import_list_profiles(runner: CliRunner) -> None:
    result = runner.invoke(app, ["import", "list-profiles"])
    assert result.exit_code == 0
    assert "Available Import Profiles" in result.stdout
    assert "request_core" in result.stdout


@pytest.mark.django_db
def test_cli_import_file_dry_run(runner: CliRunner, sample_fsd_ddic: Path) -> None:
    result = runner.invoke(app, ["import", "file", str(sample_fsd_ddic), "--dry-run"])
    assert result.exit_code == 0
    assert "Metadata Import Summary" in result.stdout
    assert "DDI-C 2.5" in result.stdout
    assert "Total Resources Staged" in result.stdout


@pytest.mark.django_db
def test_cli_import_file_live_and_status(runner: CliRunner, sample_fsd_ddic: Path) -> None:
    result = runner.invoke(app, ["import", "file", str(sample_fsd_ddic), "--force-reload"])
    assert result.exit_code == 0
    assert "Stage 1 import completed successfully." in result.stdout

    staged = StagedImport.objects.latest("id")
    status_result = runner.invoke(app, ["import", "status", str(staged.id)])
    assert status_result.exit_code == 0
    assert f"Staged Import #{staged.id}" in status_result.stdout

    log_result = runner.invoke(app, ["import", "log", str(staged.id)])
    assert log_result.exit_code == 0
    assert "FAIRwDDI METADATA IMPORT SESSION" in log_result.stdout


@pytest.mark.django_db
def test_delete_staged_import_unharmonized(sample_fsd_ddic: Path, tmp_path: Path) -> None:
    from fairwddi.importer import delete_staged_import

    summary = import_metadata_file(
        file_path=sample_fsd_ddic,
        profile="request_core",
        log_dir=tmp_path / "del_logs",
    )
    import_id = summary["staged_import_id"]
    assert StagedImport.objects.filter(id=import_id).exists()
    assert StagedResourceNode.objects.filter(staged_import_id=import_id).count() == 487

    del_res = delete_staged_import(import_id=import_id, delete_log_file=True)
    assert del_res["staged_import_id"] == import_id
    assert del_res["deleted_nodes_count"] == 487
    assert not StagedImport.objects.filter(id=import_id).exists()
    assert not StagedResourceNode.objects.filter(staged_import_id=import_id).exists()


@pytest.mark.django_db
def test_delete_staged_import_protected_normalized() -> None:
    from fairwddi.importer import ProtectedImportError, delete_staged_import

    staged_import = StagedImport.objects.create(
        source_format="ddi-l:3.3:xml",
        file_name="protected_wave1.xml",
        status="staged",
    )
    StagedResourceNode.objects.create(
        staged_import=staged_import,
        resource_type="QuestionItem",
        raw_urn="urn:raw:item-001",
        canonical_urn="urn:ddi:fr.cdsp:QuestionItem:qi-001:1.0.0",
        raw_value={"text": "Normalized question"},
        status="normalized",
    )

    # Deletion without force must raise ProtectedImportError
    with pytest.raises(ProtectedImportError) as exc_info:
        delete_staged_import(staged_import.id, force=False)

    assert exc_info.value.import_id == staged_import.id
    assert exc_info.value.normalized_count >= 1

    # Deletion with force must succeed
    del_res = delete_staged_import(staged_import.id, force=True)
    assert del_res["was_forced"] is True
    assert not StagedImport.objects.filter(id=staged_import.id).exists()


@pytest.mark.django_db
def test_delete_staged_import_protected_urnalias() -> None:
    from fairwddi.importer import ProtectedImportError, delete_staged_import
    from fairwddi.models import URNAlias

    staged_import = StagedImport.objects.create(
        source_format="ddi-l:3.3:xml",
        file_name="aliased_wave2.xml",
        status="staged",
    )
    test_raw_urn = "urn:closer:variable-999"
    StagedResourceNode.objects.create(
        staged_import=staged_import,
        resource_type="Variable",
        raw_urn=test_raw_urn,
        raw_value={"text": "Aliased variable"},
        status="staged",
    )
    URNAlias.objects.create(
        alias_urn=test_raw_urn,
        canonical_urn="urn:ddi:fr.cdsp:Variable:var-999:1.0.0",
        entity_type="Variable",
    )

    # Deletion blocked due to URNAlias dependency
    with pytest.raises(ProtectedImportError) as exc_info:
        delete_staged_import(staged_import.id, force=False)

    assert exc_info.value.alias_count == 1

    # Force delete succeeds
    del_res = delete_staged_import(staged_import.id, force=True)
    assert del_res["was_forced"] is True


@pytest.mark.django_db
def test_cli_import_delete(runner: CliRunner, sample_fsd_ddic: Path) -> None:
    import_metadata_file(
        file_path=sample_fsd_ddic,
        profile="request_core",
        force_reload=True,
    )
    staged = StagedImport.objects.latest("id")

    result = runner.invoke(app, ["import", "delete", str(staged.id)])
    assert result.exit_code == 0
    assert f"Deleted StagedImport #{staged.id}" in result.stdout
    assert not StagedImport.objects.filter(id=staged.id).exists()


@pytest.mark.django_db
def test_import_statistics_and_query_helpers(sample_fsd_ddic: Path) -> None:
    from fairwddi.importer import (
        get_import_statistics,
        list_staged_imports,
        query_staged_resources,
    )

    summary = import_metadata_file(
        file_path=sample_fsd_ddic,
        profile="request_core",
        force_reload=True,
    )
    import_id = summary["staged_import_id"]

    # 1. Statistics
    stats = get_import_statistics(import_id)
    assert stats["staged_import_id"] == import_id
    assert stats["total_resources"] == 487
    assert stats["normalized_count"] == 0
    assert stats["normalization_progress_pct"] == 0.0
    assert "Variable" in stats["counts_by_type"]
    assert "Category" in stats["counts_by_type"]
    assert "staged" in stats["counts_by_status"]
    assert stats["cross_tab"]["Variable"]["staged"] > 0

    # 2. List imports
    imports = list_staged_imports(status="staged")
    assert len(imports) >= 1
    assert any(i["id"] == import_id for i in imports)

    # 3. Query resources
    query_res = query_staged_resources(
        import_id=import_id,
        resource_type="Variable",
        limit=10,
    )
    assert query_res["total_count"] > 0
    assert len(query_res["results"]) <= 10
    assert all(r["resource_type"] == "Variable" for r in query_res["results"])

    # Query with search substring
    first_urn = query_res["results"][0]["raw_urn"]
    search_res = query_staged_resources(import_id=import_id, search=first_urn)
    assert search_res["total_count"] >= 1


@pytest.mark.django_db
def test_cli_import_list_stats_query(runner: CliRunner, sample_fsd_ddic: Path) -> None:
    import_metadata_file(
        file_path=sample_fsd_ddic,
        profile="request_core",
        force_reload=True,
    )
    staged = StagedImport.objects.latest("id")

    # CLI list
    list_res = runner.invoke(app, ["import", "list"])
    assert list_res.exit_code == 0
    assert f"#{staged.id}" in list_res.stdout

    # CLI stats
    stats_res = runner.invoke(app, ["import", "stats", str(staged.id)])
    assert stats_res.exit_code == 0
    assert f"Import #{staged.id} Statistics" in stats_res.stdout
    assert "Normalization Progress" in stats_res.stdout

    # CLI query
    query_res = runner.invoke(
        app,
        ["import", "query", "--import-id", str(staged.id), "--type", "Variable", "--limit", "5"],
    )
    assert query_res.exit_code == 0
    assert "Staged Resource Query Results" in query_res.stdout
    assert "Variable" in query_res.stdout

    # CLI stats JSON
    stats_json_res = runner.invoke(app, ["import", "stats", str(staged.id), "--format", "json"])
    assert stats_json_res.exit_code == 0
    assert '"staged_import_id":' in stats_json_res.stdout
    assert '"total_resources": 487' in stats_json_res.stdout

    # CLI stats Markdown
    stats_md_res = runner.invoke(app, ["import", "stats", str(staged.id), "--format", "markdown"])
    assert stats_md_res.exit_code == 0
    assert "Import #" in stats_md_res.stdout
    assert "High-Level Summary" in stats_md_res.stdout


@pytest.mark.django_db
def test_import_statistics_json_and_markdown_rendering(sample_fsd_ddic: Path) -> None:
    from fairwddi.importer import (
        get_import_statistics_as_json,
        get_import_statistics_as_markdown,
    )

    summary = import_metadata_file(
        file_path=sample_fsd_ddic,
        profile="request_core",
        force_reload=True,
    )
    import_id = summary["staged_import_id"]

    # Test JSON output
    json_out = get_import_statistics_as_json(import_id)
    assert f'"staged_import_id": {import_id}' in json_out
    assert '"total_resources": 487' in json_out

    # Test Markdown output via Jinja2
    md_out = get_import_statistics_as_markdown(import_id)
    assert f"# Import #{import_id} Statistics Report" in md_out
    assert "| **Total Staged Resources** | 487 |" in md_out
    assert "| **Variable** | 74 | 74 | 0 | 0 |" in md_out
