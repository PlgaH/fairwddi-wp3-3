"""Tests for `fairwddi.ingest` format detection, profiles, streaming, and direct loader."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from fairwddi.cli import app
from fairwddi.ingest import (
    ImportProfile,
    ImportStrategies,
    apply_ingestion,
    compute_resource_hashes,
    detect_metadata_format,
    get_ingest_batch_status,
    list_available_profiles,
    list_ingest_batches,
    load_profile,
    plan_ingestion,
    stream_resources,
    undo_ingestion,
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
def test_plan_ingestion_zero_db_writes(sample_fsd_ddic: Path, tmp_path: Path) -> None:
    initial_batches = IngestBatch.objects.count()
    initial_vars = InstanceVariable.objects.count()

    plan = plan_ingestion(sample_fsd_ddic, profile="request", output_dir=tmp_path)

    assert plan.stage == "ingest"
    assert plan.summary["streamed_nodes"] > 100
    assert plan.summary["create"] > 0
    assert (tmp_path / f"{sample_fsd_ddic.stem}.ingest.plan.yaml").exists()
    assert (tmp_path / f"{sample_fsd_ddic.stem}.ingest.report.md").exists()
    assert IngestBatch.objects.count() == initial_batches
    assert InstanceVariable.objects.count() == initial_vars


@pytest.mark.django_db
def test_apply_ingestion_live_duplicate_skip_and_force_reload(sample_fsd_ddic: Path) -> None:
    # 1. First direct ingestion into core tables + IngestBatch receipt
    res1 = apply_ingestion(sample_fsd_ddic, profile="request", auto_approve=True)
    assert res1["status"] == "completed"
    batch_id = res1["batch_id"]
    assert batch_id is not None
    assert res1["created_count"] > 0
    assert res1["frequency_rows_count"] > 0
    assert IngestBatch.objects.filter(id=batch_id, status="completed").exists()
    assert DatafileVariableFrequency.objects.count() == res1["frequency_rows_count"]

    # 2. Re-ingesting identical file triggers SHA-256 duplicate skip
    res2 = apply_ingestion(sample_fsd_ddic, profile="request", auto_approve=True)
    assert res2["status"] == "already_ingested"
    assert res2["batch_id"] == batch_id

    # 3. Force reload rolls back old batch and creates a fresh receipt
    res3 = apply_ingestion(sample_fsd_ddic, profile="request", force_reload=True, auto_approve=True)
    assert res3["status"] == "completed"
    assert res3["batch_id"] != batch_id
    assert IngestBatch.objects.get(id=batch_id).status == "undone"
    assert IngestBatch.objects.get(id=res3["batch_id"]).status == "completed"

    # 4. Batch listing and status helpers
    batches = list_ingest_batches(status="completed")
    assert any(b["id"] == res3["batch_id"] for b in batches)
    info = get_ingest_batch_status(res3["batch_id"])
    assert info["file_name"] == sample_fsd_ddic.name
    assert info["stats"]["InstanceVariable"] > 0

    # 5. Clean undo removes created core resources and frequencies
    undo_res = undo_ingestion(res3["batch_id"])
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
    plan = plan_ingestion(drift_json, profile=custom_profile)
    assert plan.summary["quarantine"] == 1
    assert plan.pending_review_count == 1
    assert not plan.is_ready_to_execute(auto_approve=False)

    # 2. Apply with auto_approve records MetadataQuarantine without overwriting Category
    res = apply_ingestion(plan, profile=custom_profile, auto_approve=True)
    assert res["status"] == "quarantined"
    assert res["quarantine_count"] == 1
    assert MetadataQuarantine.objects.filter(incoming_urn=existing_urn).exists()
    assert Category.objects.get(urn=existing_urn).label == {"en": "Original Category Label"}

    # 3. Undo cleans up quarantine record
    undo_ingestion(res["batch_id"])
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
def test_cli_ingest_plan_execute_list_status_and_undo(
    runner: CliRunner, sample_fsd_ddic: Path, tmp_path: Path
) -> None:
    # 1. fairwddi ingest plan (zero DB writes)
    plan_res = runner.invoke(
        app, ["ingest", "plan", str(sample_fsd_ddic), "--output-dir", str(tmp_path)]
    )
    assert plan_res.exit_code == 0
    assert "Ingestion Plan" in plan_res.stdout
    assert IngestBatch.objects.count() == 0

    # 2. fairwddi ingest execute
    plan_yaml = tmp_path / f"{sample_fsd_ddic.stem}.ingest.plan.yaml"
    exec_res = runner.invoke(app, ["ingest", "execute", str(plan_yaml), "--auto-approve"])
    assert exec_res.exit_code == 0
    assert "Ingestion Completed" in exec_res.stdout

    batch = IngestBatch.objects.latest("id")

    # 3. fairwddi ingest list & status
    list_res = runner.invoke(app, ["ingest", "list"])
    assert list_res.exit_code == 0
    assert f"#{batch.id}" in list_res.stdout

    status_res = runner.invoke(app, ["ingest", "status", str(batch.id)])
    assert status_res.exit_code == 0
    assert f"IngestBatch #{batch.id}" in status_res.stdout
    assert "Ingested Entities Breakdown" in status_res.stdout

    # 4. fairwddi ingest undo
    undo_res = runner.invoke(app, ["ingest", "undo", str(batch.id)])
    assert undo_res.exit_code == 0
    assert f"Rolled back Batch #{batch.id}" in undo_res.stdout
    assert IngestBatch.objects.get(id=batch.id).status == "undone"


@pytest.mark.django_db
def test_same_urn_identical_content_triggers_review(tmp_path: Path) -> None:
    """Same-URN collisions across files with identical content must trigger review ('reuse')."""
    from fairwddi.ingest import compute_resource_hashes
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

    plan = plan_ingestion(incoming_json, profile="request")
    assert plan.summary["reuse"] == 1
    assert plan.pending_review_count == 1
    assert plan.is_ready_to_execute(auto_approve=False) is False
    assert any(i.code == "ING-URN-REUSE-001" for i in plan.issues)
    reuse_act = next(a for a in plan.actions if a.action == "reuse")
    assert reuse_act.requires_review is True
    assert reuse_act.target_urn == shared_urn

    with pytest.raises(PermissionError):
        apply_ingestion(plan, auto_approve=False)

    res = apply_ingestion(plan, auto_approve=True)
    assert res["reused_count"] == 1
    assert res["created_count"] == 0


@pytest.mark.django_db
def test_three_wave_non_destructive_import_and_two_tier_matching(tmp_path: Path) -> None:
    """Test the complete 3-wave import lifecycle:

    - Wave 1: Creates `imported` resources only (no `generated` resources).
    - Wave 2: Matches Wave 1 `imported` resource -> creates Wave 2 `imported` resource
      AND spawns a `generated` resource linking both via `prov:wasDerivedFrom` with
      alternate spelling preserved.
    - Wave 3: Prioritizes the `generated` resource in Tier 1 -> creates Wave 3 `imported`
      resource, links it to the existing `generated` resource via `prov:wasDerivedFrom`,
      and enriches the `generated` resource without spawning a duplicate `generated` resource.
    - Also verifies deletion protection during undo.
    """
    from fairwddi.models import QuestionItem, SemanticRelationship, UrnRegistry
    from fairwddi.utils.integrity import ResourceReferencedError

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
                    "Text": {
                      "language": "fr",
                      "value": "Êtes-vous satisfait des institutions ?"
                    }
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
                    "Text": {
                      "language": "fr",
                      "value": "Êtes-vous satisfait(e) des institutions ?"
                    }
                  }
                }
              ]
            }
          ]
        }""",
        encoding="utf-8",
    )

    w3_file = tmp_path / "wave3.json"
    w3_file.write_text(
        """{
          "items": [
            {
              "$type": "QuestionItem",
              "URN": "urn:ddi:fr.cdsp:w3.qi_org:1.0.0",
              "QuestionItemName": [{"String": {"language": "fr", "value": "QI_ORG_W3"}}],
              "QuestionText": [
                {
                  "LiteralText": {
                    "Text": {
                      "language": "fr",
                      "value": "Êtes-vous satisfait(e) des institutions ?"
                    }
                  }
                },
                {
                  "LiteralText": {
                    "Text": {
                      "language": "en",
                      "value": "Are you satisfied with the institutions?"
                    }
                  }
                }
              ]
            }
          ]
        }""",
        encoding="utf-8",
    )

    # Wave 1: First import -> creates imported resource only
    p1 = plan_ingestion(w1_file, profile="request")
    assert p1.summary["create"] == 1
    assert p1.summary["generate_harmonized"] == 0
    assert p1.summary["link_existing"] == 0
    assert p1.is_ready_to_execute() is True

    r1 = apply_ingestion(p1)
    b1_id = r1["batch_id"]
    assert r1["created_count"] == 1
    assert r1["generated_count"] == 0
    assert UrnRegistry.objects.get(urn="urn:ddi:fr.cdsp:w1.qi_org:1.0.0").origin == "imported"

    # Wave 2: Second import with inclusive spelling -> Tier 2 match -> generate_harmonized
    p2 = plan_ingestion(w2_file, profile="request")
    assert p2.summary["generate_harmonized"] == 1
    assert p2.summary["link_existing"] == 0
    assert p2.pending_review_count == 1
    assert p2.is_ready_to_execute(auto_approve=False) is False
    gen_urn = p2.actions[0].details["generated_urn"]
    assert p2.actions[0].target_urn == "urn:ddi:fr.cdsp:w1.qi_org:1.0.0"

    r2 = apply_ingestion(p2, auto_approve=True)
    b2_id = r2["batch_id"]
    assert r2["created_count"] == 1
    assert r2["generated_count"] == 1

    # Both imported resources remain intact, AND new generated resource exists
    assert QuestionItem.objects.filter(urn="urn:ddi:fr.cdsp:w1.qi_org:1.0.0").exists()
    assert QuestionItem.objects.filter(urn="urn:ddi:fr.cdsp:w2.qi_org:1.0.0").exists()
    gen_qi = QuestionItem.objects.get(urn=gen_urn)
    assert gen_qi.origin == "generated"
    assert UrnRegistry.objects.get(urn="urn:ddi:fr.cdsp:w2.qi_org:1.0.0").origin == "imported"

    # Lineage links from generated -> both imported resources
    derived_targets = set(
        SemanticRelationship.objects.filter(
            subject_urn=gen_urn, predicate="prov:wasDerivedFrom"
        ).values_list("object_urn", flat=True)
    )
    assert derived_targets == {
        "urn:ddi:fr.cdsp:w1.qi_org:1.0.0",
        "urn:ddi:fr.cdsp:w2.qi_org:1.0.0",
    }

    # Alternate spelling recorded on generated resource
    variants = [a for a in (gen_qi.extended_attributes or []) if a.get("type") == "wording_variant"]
    assert any(v["value"] == "Êtes-vous satisfait des institutions ?" for v in variants)

    # Wave 3: Third import -> MUST prioritize generated resource (Tier 1) -> link_existing
    p3 = plan_ingestion(w3_file, profile="request")
    assert p3.summary["link_existing"] == 1
    assert p3.summary["generate_harmonized"] == 0
    assert p3.actions[0].target_urn == gen_urn

    r3 = apply_ingestion(p3, auto_approve=True)
    b3_id = r3["batch_id"]
    assert r3["created_count"] == 1
    assert r3["generated_count"] == 0
    assert r3["linked_count"] == 1
    assert UrnRegistry.objects.get(urn="urn:ddi:fr.cdsp:w3.qi_org:1.0.0").origin == "imported"

    gen_qi.refresh_from_db()
    en_vals = [
        e["value"]
        for e in (gen_qi.question_text or [])
        if isinstance(e, dict) and e.get("lang") == "en"
    ]
    assert en_vals == ["Are you satisfied with the institutions?"]

    derived_targets_after = set(
        SemanticRelationship.objects.filter(
            subject_urn=gen_urn, predicate="prov:wasDerivedFrom"
        ).values_list("object_urn", flat=True)
    )
    assert derived_targets_after == {
        "urn:ddi:fr.cdsp:w1.qi_org:1.0.0",
        "urn:ddi:fr.cdsp:w2.qi_org:1.0.0",
        "urn:ddi:fr.cdsp:w3.qi_org:1.0.0",
    }

    # Deletion protection: cannot roll back Wave 1 while generated resource derives from w1
    with pytest.raises(ResourceReferencedError):
        undo_ingestion(b1_id)

    # Rolling back Wave 2 while Wave 3 still links to gen_urn protects gen_urn & w1
    undo_ingestion(b2_id)
    assert QuestionItem.objects.filter(urn=gen_urn).exists() is True
    assert QuestionItem.objects.filter(urn="urn:ddi:fr.cdsp:w2.qi_org:1.0.0").exists() is False

    # Rolling back Wave 3 leaves only w1 and gen_urn; clean up
    undo_ingestion(b3_id)
    assert QuestionItem.objects.filter(urn="urn:ddi:fr.cdsp:w3.qi_org:1.0.0").exists() is False


@pytest.mark.django_db
def test_instantiated_resource_prioritized_on_first_import(tmp_path: Path) -> None:
    """When an administrator pre-instantiates a resource, the very first import links to it."""
    from fairwddi.models import QuestionItem, SemanticRelationship

    inst_qi = QuestionItem.objects.create(
        urn="urn:ddi:fr.cdsp:QI-admin-trust:1.0.0",
        name="QI_ADMIN_TRUST",
        question_text={"fr": "Avez-vous confiance dans la justice ?"},
        origin="instantiated",
    )

    # Also seed an unharmonized imported QuestionItem with the exact same text to prove
    # Tier 1 (`instantiated`) strictly beats Tier 2 (`imported`)!
    QuestionItem.objects.create(
        urn="urn:ddi:fr.cdsp:old_imp_justice:1.0.0",
        name="OLD_IMP",
        question_text={"fr": "Avez-vous confiance dans la justice ?"},
        origin="imported",
    )

    inc_file = tmp_path / "inc_justice.json"
    inc_file.write_text(
        """{
          "items": [
            {
              "$type": "QuestionItem",
              "URN": "urn:ddi:fr.cdsp:w1.qi_justice:1.0.0",
              "QuestionItemName": [{"String": {"language": "fr", "value": "QI_JUS_W1"}}],
              "QuestionText": [
                {
                  "LiteralText": {
                    "Text": {
                      "language": "fr",
                      "value": "Avez-vous confiance dans la justice ?",
                      "lang": "fr"
                    }
                  }
                }
              ]
            }
          ]
        }""",
        encoding="utf-8",
    )

    plan = plan_ingestion(inc_file, profile="request")
    assert plan.summary["link_existing"] == 1
    assert plan.summary["generate_harmonized"] == 0
    assert plan.actions[0].target_urn == inst_qi.urn
    assert plan.actions[0].details["target_origin"] == "instantiated"

    res = apply_ingestion(plan, auto_approve=True)
    assert res["created_count"] == 1
    assert res["linked_count"] == 1
    assert SemanticRelationship.objects.filter(
        subject_urn=inst_qi.urn,
        predicate="prov:wasDerivedFrom",
        object_urn="urn:ddi:fr.cdsp:w1.qi_justice:1.0.0",
    ).exists()
