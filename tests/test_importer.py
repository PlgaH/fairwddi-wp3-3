"""Tests for `fairwddi.importer` format detection, profiles, streaming, and direct loader."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from fairwddi.cli import app
from fairwddi.importer import (
    ImportProfile,
    ImportStrategies,
    compute_resource_hashes,
    detect_metadata_format,
    execute_import,
    get_import_batch_status,
    list_available_profiles,
    list_import_batches,
    load_profile,
    plan_import,
    stream_resources,
    undo_import,
)
from fairwddi.models import (
    Category,
    DatafileVariableFrequency,
    IngestBatch,
    InstanceVariable,
    MetadataQuarantine,
)

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


def test_load_profile_request() -> None:
    profile = load_profile("request")
    assert profile.name == "request"
    assert "QuestionItem" in profile.include_types
    assert "Instruction" in profile.include_types
    assert "Instrument" in profile.include_types
    assert "Sequence" in profile.include_types
    assert "PhysicalInstance" in profile.include_types
    assert "ControlConstructScheme" in profile.include_types
    assert "VariableStatistics" in profile.exclude_types
    assert "Archive" in profile.exclude_types
    assert profile.include_referenced_resources is True

    assert profile.should_include("VariableStatistics") is False
    assert profile.should_include("Archive") is False
    assert profile.should_include("Instrument") is True
    assert profile.should_include("PhysicalInstance") is True
    assert profile.should_include("Sequence") is True
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
    assert "request" in names
    assert "all_ddi" in names


# -----------------------------------------------------------------------------
# Streaming & Extraction Tests
# -----------------------------------------------------------------------------


def test_stream_resources_ddi33_xml(sample_cso_xml: Path) -> None:
    profile = load_profile("request")
    nodes = list(stream_resources(sample_cso_xml, profile))
    assert len(nodes) > 100
    types = {n.resource_type for n in nodes}
    assert "QuestionItem" in types
    assert "Category" in types
    assert "CodeList" in types
    assert all(n.raw_urn.startswith("urn:ddi:") for n in nodes)
    assert all(isinstance(n.raw_value, dict) for n in nodes)


def test_stream_resources_ddi40_json(sample_ddi40_json: Path) -> None:
    profile = load_profile("request")
    nodes = list(stream_resources(sample_ddi40_json, profile))
    assert len(nodes) > 50
    types = {n.resource_type for n in nodes}
    assert "Category" in types
    assert "QuestionItem" in types or "Variable" in types or "CodeList" in types


def test_stream_resources_ddic_xml(sample_fsd_ddic: Path) -> None:
    profile = load_profile("request")
    nodes = list(stream_resources(sample_fsd_ddic, profile))
    assert len(nodes) > 100
    types = {n.resource_type for n in nodes}
    assert "Variable" in types
    assert "Category" in types
    assert "CodeList" in types
    assert "PhysicalInstance" in types


# -----------------------------------------------------------------------------
# Direct Ingestion Plan, Apply, Duplicate Skip, Quarantine & Batch Receipts
# -----------------------------------------------------------------------------


@pytest.mark.django_db
def test_plan_import_zero_db_writes(sample_fsd_ddic: Path, tmp_path: Path) -> None:
    initial_batches = IngestBatch.objects.count()
    initial_vars = InstanceVariable.objects.count()

    plan = plan_import(sample_fsd_ddic, profile="request", output_dir=tmp_path)

    assert plan.stage == "import"
    assert plan.summary["streamed_nodes"] > 100
    assert plan.summary["create"] > 0
    assert (tmp_path / f"{sample_fsd_ddic.stem}.import.plan.yaml").exists()
    assert (tmp_path / f"{sample_fsd_ddic.stem}.import.report.md").exists()
    assert IngestBatch.objects.count() == initial_batches
    assert InstanceVariable.objects.count() == initial_vars


@pytest.mark.django_db
def test_execute_import_live_duplicate_skip_and_force_reload(sample_fsd_ddic: Path) -> None:
    # 1. First direct ingestion into core tables + IngestBatch receipt
    res1 = execute_import(sample_fsd_ddic, profile="request", auto_approve=True)
    assert res1["status"] == "completed"
    batch_id = res1["batch_id"]
    assert batch_id is not None
    assert res1["created_count"] > 0
    assert res1["frequency_rows_count"] > 0
    assert IngestBatch.objects.filter(id=batch_id, status="completed").exists()
    assert DatafileVariableFrequency.objects.count() == res1["frequency_rows_count"]

    # 2. Re-ingesting identical file triggers SHA-256 duplicate skip
    res2 = execute_import(sample_fsd_ddic, profile="request", auto_approve=True)
    assert res2["status"] == "already_imported"
    assert res2["batch_id"] == batch_id

    # 3. Force reload rolls back old batch and creates a fresh receipt
    res3 = execute_import(sample_fsd_ddic, profile="request", force_reload=True, auto_approve=True)
    assert res3["status"] == "completed"
    assert res3["batch_id"] != batch_id
    assert IngestBatch.objects.get(id=batch_id).status == "undone"
    assert IngestBatch.objects.get(id=res3["batch_id"]).status == "completed"

    # 4. Batch listing and status helpers
    batches = list_import_batches(status="completed")
    assert any(b["id"] == res3["batch_id"] for b in batches)
    info = get_import_batch_status(res3["batch_id"])
    assert info["file_name"] == sample_fsd_ddic.name
    assert info["stats"]["InstanceVariable"] > 0

    # 5. Clean undo removes created core resources and frequencies
    undo_res = undo_import(res3["batch_id"])
    assert undo_res["status"] == "undone"
    assert InstanceVariable.objects.count() == 0
    assert DatafileVariableFrequency.objects.count() == 0


@pytest.mark.django_db
def test_content_drift_quarantine_during_direct_ingestion(tmp_path: Path) -> None:
    # Seed an existing Category with a specific canonical URN and content hash
    existing_urn = "urn:ddi:fr.cdsp:cat_drift_01:1.0.0"
    Category.objects.create(
        urn=existing_urn,
        name="CAT_DRIFT",
        label={"en": "Original Category Label"},
        hashes=compute_resource_hashes(
            "Category", {"name": "CAT_DRIFT", "label": {"en": "Original Category Label"}}
        ),
    )

    # Create a minimal DDI 4 JSON file carrying the SAME URN with drifted label text
    drift_json = tmp_path / "drift_test.json"
    drift_json.write_text(
        """{
          "items": [
            {
              "$type": "Category",
              "URN": "urn:ddi:fr.cdsp:cat_drift_01:1.0.0",
              "Agency": "fr.cdsp",
              "ID": "cat_drift_01",
              "Version": "1.0.0",
              "CategoryName": [{"String": {"language": "en", "value": "CAT_DRIFT"}}],
              "Label": [{"Content": {"language": "en", "value": "Modified Category Label"}}]
            }
          ]
        }""",
        encoding="utf-8",
    )

    custom_profile = ImportProfile(
        name="drift_profile",
        include_types=["Category"],
        strategies=ImportStrategies(on_content_drift="quarantine"),
    )

    # 1. Plan flags ING-DRIFT-001 and requires review
    plan = plan_import(drift_json, profile=custom_profile)
    assert plan.summary["quarantine"] == 1
    assert plan.pending_review_count == 1
    assert not plan.is_ready_to_execute(auto_approve=False)

    # 2. Apply with auto_approve records MetadataQuarantine without overwriting Category
    res = execute_import(plan, profile=custom_profile, auto_approve=True)
    assert res["status"] == "quarantined"
    assert res["quarantine_count"] == 1
    assert MetadataQuarantine.objects.filter(incoming_urn=existing_urn).exists()
    assert Category.objects.get(urn=existing_urn).label == {"en": "Original Category Label"}

    # 3. Undo cleans up quarantine record
    undo_import(res["batch_id"])
    assert not MetadataQuarantine.objects.filter(incoming_urn=existing_urn).exists()


# -----------------------------------------------------------------------------
# CLI Command Tests (`preflight profiles`, `ingest plan/apply/list/status/undo`)
# -----------------------------------------------------------------------------


def test_cli_preflight_profiles(runner: CliRunner) -> None:
    result = runner.invoke(app, ["preflight", "profiles"])
    assert result.exit_code == 0
    assert "Available Import Profiles" in result.stdout
    assert "request" in result.stdout


@pytest.mark.django_db
def test_cli_preflight_check_default_output(
    runner: CliRunner,
    sample_fsd_ddic: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import json

    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["preflight", "check", str(sample_fsd_ddic)])
    assert result.exit_code == 0, result.stdout
    stem = sample_fsd_ddic.stem
    json_file = tmp_path / f"{stem}.preflight.json"
    md_file = tmp_path / f"{stem}.preflight.report.md"
    yaml_file = tmp_path / f"{stem}.preflight.plan.yaml"
    assert json_file.exists()
    assert md_file.exists()
    assert yaml_file.exists()
    payload = json.loads(json_file.read_text(encoding="utf-8"))
    assert payload["stage"] == "preflight"
    assert payload["source_file"] == sample_fsd_ddic.name
    assert "# FAIRwDDI `PREFLIGHT` Report" in md_file.read_text(encoding="utf-8")


def test_cli_preflight_profile_default_output(
    runner: CliRunner,
    sample_fsd_ddic: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import json

    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["preflight", "profile", str(sample_fsd_ddic)])
    assert result.exit_code == 0, result.stdout
    stem = sample_fsd_ddic.stem
    json_file = tmp_path / f"{stem}.profile.json"
    md_file = tmp_path / f"{stem}.profile.md"
    assert json_file.exists()
    assert md_file.exists()
    payload = json.loads(json_file.read_text(encoding="utf-8"))
    assert payload["source_file"] == sample_fsd_ddic.name
    assert "# DDI-Codebook Profile:" in md_file.read_text(encoding="utf-8")


@pytest.mark.django_db
def test_cli_import_plan_execute_list_status_and_undo(
    runner: CliRunner, sample_fsd_ddic: Path, tmp_path: Path
) -> None:
    # 1. fairwddi import plan (zero DB writes)
    plan_res = runner.invoke(
        app, ["import", "plan", str(sample_fsd_ddic), "--output-dir", str(tmp_path)]
    )
    assert plan_res.exit_code == 0, plan_res.stdout
    assert "Import Plan" in plan_res.stdout
    assert IngestBatch.objects.count() == 0

    # 2. fairwddi import execute
    plan_yaml = tmp_path / f"{sample_fsd_ddic.stem}.import.plan.yaml"
    exec_res = runner.invoke(app, ["import", "execute", str(plan_yaml), "--auto-approve"])
    assert exec_res.exit_code == 0, exec_res.stdout

    batch = IngestBatch.objects.latest("id")

    # 3. fairwddi import list & status
    list_res = runner.invoke(app, ["import", "list"])
    assert list_res.exit_code == 0, list_res.stdout
    assert str(batch.id) in list_res.stdout

    status_res = runner.invoke(app, ["import", "status", str(batch.id)])
    assert status_res.exit_code == 0, status_res.stdout
    assert str(batch.id) in status_res.stdout

    # 4. fairwddi import undo
    undo_res = runner.invoke(app, ["import", "undo", str(batch.id)])
    assert undo_res.exit_code == 0, undo_res.stdout
    assert IngestBatch.objects.get(id=batch.id).status == "undone"


@pytest.mark.django_db
def test_same_urn_identical_content_triggers_review(tmp_path: Path) -> None:
    """Same-URN collisions across files with identical content must trigger review ('reuse')."""
    from fairwddi.importer import compute_resource_hashes
    from fairwddi.models import QuestionItem

    shared_urn = "urn:ddi:fr.cdsp:qi_shared_01:1.0.0"
    QuestionItem.objects.create(
        urn=shared_urn,
        name="QI_SHARED",
        question_text={"en": "Do you vote regularly?"},
        hashes=compute_resource_hashes(
            "QuestionItem",
            {
                "name": "QI_SHARED",
                "label": None,
                "description": None,
                "question_text": {"en": "Do you vote regularly?"},
            },
        ),
        origin="imported",
    )

    incoming_json = tmp_path / "same_urn_reuse.json"
    incoming_json.write_text(
        """{
          "items": [
            {
              "$type": "QuestionItem",
              "URN": "urn:ddi:fr.cdsp:qi_shared_01:1.0.0",
              "Agency": "fr.cdsp",
              "ID": "qi_shared_01",
              "Version": "1.0.0",
              "QuestionItemName": [{"String": {"language": "en", "value": "QI_SHARED"}}],
              "QuestionText": [
                {"LiteralText": {"Text": {"language": "en", "value": "Do you vote regularly?"}}}
              ]
            }
          ]
        }""",
        encoding="utf-8",
    )

    plan = plan_import(incoming_json, profile="request")
    assert plan.summary["reuse"] == 1
    assert plan.pending_review_count == 1
    assert plan.is_ready_to_execute(auto_approve=False) is False
    assert any(i.code == "IMP-URN-REUSE-001" for i in plan.issues)
    reuse_act = next(a for a in plan.actions if a.action == "reuse")
    assert reuse_act.requires_review is True
    assert reuse_act.target_urn == shared_urn

    with pytest.raises(PermissionError):
        execute_import(plan, auto_approve=False)

    res = execute_import(plan, auto_approve=True)
    assert res["reused_count"] == 1
    assert res["created_count"] == 0


@pytest.mark.django_db
def test_multi_wave_import_remains_pure_imported_only(tmp_path: Path) -> None:
    """Importing overlapping waves creates only origin='imported' resources (zero harmonization)."""
    from fairwddi.importer.pipeline import run_import
    from fairwddi.models import QuestionItem, SemanticRelationship, UrnRegistry

    w1_file = tmp_path / "wave1.json"
    w1_file.write_text(
        """{
          "items": [
            {
              "$type": "QuestionItem",
              "URN": "urn:ddi:fr.cdsp:w1.qi_org:1.0.0",
              "QuestionItemName": [{"String": {"language": "fr", "value": "QI_ORG_W1"}}],
              "QuestionText": [
                {
                  "LiteralText": {
                    "Text": {"language": "fr", "value": "Êtes-vous satisfait des institutions ?"}
                  }
                }
              ]
            }
          ]
        }""",
        encoding="utf-8",
    )
    w2_file = tmp_path / "wave2.json"
    w2_file.write_text(
        """{
          "items": [
            {
              "$type": "QuestionItem",
              "URN": "urn:ddi:fr.cdsp:w2.qi_org:1.0.0",
              "QuestionItemName": [{"String": {"language": "fr", "value": "QI_ORG_W2"}}],
              "QuestionText": [
                {
                  "LiteralText": {
                    "Text": {"language": "fr", "value": "Êtes-vous satisfait(e) des institutions ?"}
                  }
                }
              ]
            }
          ]
        }""",
        encoding="utf-8",
    )

    r1 = run_import(w1_file, profile="request")
    r2 = run_import(w2_file, profile="request")
    assert r1["status"] == "completed"
    assert r2["status"] == "completed"
    assert QuestionItem.objects.count() == 2
    assert UrnRegistry.objects.filter(origin="generated").count() == 0
    assert SemanticRelationship.objects.filter(predicate="prov:wasDerivedFrom").count() == 0
