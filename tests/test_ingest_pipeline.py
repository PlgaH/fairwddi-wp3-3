"""Comprehensive tests for the Phase 2 Ingestion & Harmonization Pipeline (`fairwddi.ingest`).

Covers:
1. Use Case 1: Classic DDI-Codebook -> preflight -> upgrade (ddi4-json/jsonl) -> stage -> promote.
2. Use Case 2: Multilingual DDI-Codebook (fr/en) -> upgrade -> stage -> promote (JSONB).
3. Use Case 3: DDI-Lifecycle 3.3 XML & 4.0 JSON -> preflight -> stage -> promote (shortcuts).
4. Storage Compaction (`cleanup_staged_import`) & Promotion Undo (`undo_promotion`).
5. Stage 3 Comparison (`discover_candidates`, `compare_batch`) & Harmonization (`plan/apply/undo`).
6. CLI command groups (`preflight`, `stage`, `promote`, `compare`, `harmonize`, `ingest`).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from fairwddi.cli import app
from fairwddi.ingest import (
    apply_harmonization,
    apply_promotion,
    cleanup_staged_import,
    discover_candidates,
    plan_harmonization,
    plan_promotion,
    run_preflight_check,
    stage_metadata_file,
    undo_harmonization,
    undo_promotion,
    upgrade_ddic_to_ddil,
)
from fairwddi.models import (
    Category,
    CodeItem,
    CodeList,
    Datafile,
    DatafileVariable,
    DatafileVariableFrequency,
    InstanceVariable,
    Instrument,
    InstrumentQuestion,
    QuestionItem,
    QuestionVariable,
    RepresentedVariable,
    SemanticRelationship,
    StagedImport,
    StagedResourceNode,
    StudyInstrument,
    StudyUnit,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"

BILINGUAL_DDIC_XML = """<?xml version="1.0" encoding="UTF-8"?>
<codeBook xmlns="ddi:codebook:2_5" version="2.5" ID="CDSP_BILINGUAL_01" xml:lang="fr">
  <stdyDscr>
    <citation>
      <titlStmt>
        <titl xml:lang="fr">Enquête électorale française 2026</titl>
        <titl xml:lang="en">French Electoral Survey 2026</titl>
        <IDNo agency="fr.cdsp">CDSP_BILINGUAL_01</IDNo>
      </titlStmt>
    </citation>
  </stdyDscr>
  <fileDscr ID="F1">
    <fileTxt>
      <fileName>eef2026.csv</fileName>
      <dimensns>
        <caseQnty>1200</caseQnty>
        <varQnty>2</varQnty>
      </dimensns>
    </fileTxt>
  </fileDscr>
  <dataDscr>
    <var ID="V1" name="Q1_TRUST" files="F1" intrvl="discrete">
      <labl xml:lang="fr">Confiance dans le parlement</labl>
      <labl xml:lang="en">Trust in parliament</labl>
      <qstn ID="Q1">
        <qstnLit xml:lang="fr">Avez-vous confiance dans le Parlement ?</qstnLit>
        <qstnLit xml:lang="en">Do you trust the Parliament?</qstnLit>
        <ivuInstr xml:lang="fr">Montrer la carte 1</ivuInstr>
        <ivuInstr xml:lang="en">Show card 1</ivuInstr>
      </qstn>
      <sumStat type="valid">1180</sumStat>
      <sumStat type="invd">20</sumStat>
      <catgry>
        <catValu>1</catValu>
        <labl xml:lang="fr">Oui, tout à fait</labl>
        <labl xml:lang="en">Yes, completely</labl>
        <catStat type="freq">450</catStat>
      </catgry>
      <catgry>
        <catValu>2</catValu>
        <labl xml:lang="fr">Non, pas du tout</labl>
        <labl xml:lang="en">No, not at all</labl>
        <catStat type="freq">730</catStat>
      </catgry>
    </var>
    <var ID="V2" name="Q2_SATISF" files="F1" intrvl="discrete">
      <labl xml:lang="fr">Satisfaction démocratie</labl>
      <labl xml:lang="en">Satisfaction with democracy</labl>
      <qstn ID="Q2">
        <qstnLit xml:lang="fr">Êtes-vous satisfait du fonctionnement de la démocratie ?</qstnLit>
        <qstnLit xml:lang="en">Are you satisfied with how democracy works?</qstnLit>
      </qstn>
      <catgry>
        <catValu>1</catValu>
        <labl xml:lang="fr">Oui, tout à fait</labl>
        <labl xml:lang="en">Yes, completely</labl>
        <catStat type="freq">500</catStat>
      </catgry>
      <catgry>
        <catValu>2</catValu>
        <labl xml:lang="fr">Non, pas du tout</labl>
        <labl xml:lang="en">No, not at all</labl>
        <catStat type="freq">700</catStat>
      </catgry>
    </var>
  </dataDscr>
</codeBook>
"""


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def bilingual_ddic_file(tmp_path: Path) -> Path:
    p = tmp_path / "cdsp_bilingual.ddic.xml"
    p.write_text(BILINGUAL_DDIC_XML, encoding="utf-8")
    return p


@pytest.fixture
def sample_fsd_ddic() -> Path:
    p = FIXTURES_DIR / "FSD3562_eng.ddic.xml"
    if not p.exists():
        pytest.skip(f"Fixture not found: {p}")
    return p


@pytest.fixture
def sample_cso_xml() -> Path:
    p = FIXTURES_DIR / "sample_cso.ddi33.xml"
    if not p.exists():
        pytest.skip(f"Fixture not found: {p}")
    return p


# -----------------------------------------------------------------------------
# Use Case 1 & 2: DDI-Codebook (Classic & Multilingual) Upgrade, Stage, Promote
# -----------------------------------------------------------------------------


@pytest.mark.django_db
def test_bilingual_ddic_preflight_upgrade_stage_promote_and_undo(
    bilingual_ddic_file: Path, tmp_path: Path
) -> None:
    out_dir = tmp_path / "out"

    # 1. Preflight check on bilingual DDI-C
    plan = run_preflight_check(bilingual_ddic_file, output_dir=out_dir)
    assert plan.stage == "preflight"
    assert plan.summary["specification"] == "DDI-C"
    assert plan.summary["is_multilingual"] is True
    assert set(plan.summary["languages"]) == {"fr", "en"}
    assert plan.summary["variable_count"] == 2
    assert (out_dir / "cdsp_bilingual.ddic.preflight.plan.yaml").exists()
    assert (out_dir / "cdsp_bilingual.ddic.preflight.report.md").exists()

    # 2. Explicit upgrade to DDI-L 4.0 JSON and JSONL (with content_hash ID strategy)
    upg_json = upgrade_ddic_to_ddil(
        bilingual_ddic_file,
        output_path=out_dir / "cdsp_bilingual.ddi40.json",
        output_format="ddi4-json",
        agency="fr.cdsp",
        id_strategy="content_hash",
        harmonize_codes=True,
    )
    assert Path(upg_json["output_file"]).exists()
    assert Path(upg_json["report_file"]).exists()
    # Both variables share the same 2 categories & codelist -> deduplicated to 1 CodeList!
    assert upg_json["variable_count"] == 2
    assert upg_json["codelist_count"] == 1
    assert upg_json["category_count"] == 2
    assert upg_json["question_count"] == 2

    upg_jsonl = upgrade_ddic_to_ddil(
        bilingual_ddic_file,
        output_path=out_dir / "cdsp_bilingual.ddi40.jsonl",
        output_format="ddi4-jsonl",
        agency="fr.cdsp",
        harmonize_codes=True,
    )
    assert Path(upg_jsonl["output_file"]).exists()

    # 3. Stage the upgraded DDI 4.0 JSONL file
    stage_res = stage_metadata_file(upg_jsonl["output_file"], profile="request")
    assert stage_res["status"] == "staged"
    import_id = stage_res["staged_import_id"]
    assert import_id is not None

    # 4. Plan & apply promotion
    promo_plan = plan_promotion(import_id, output_dir=out_dir)
    assert promo_plan.is_ready_to_execute() is True
    promo_res = apply_promotion(promo_plan, compact=True)
    assert promo_res["status"] == "normalized"
    assert promo_res["created_count"] > 0
    assert promo_res["compacted_nodes_count"] > 0

    # Verify ReQuest core tables & multilingual JSONB preservation
    assert StudyUnit.objects.count() >= 1
    assert Category.objects.count() >= 2
    cat_1 = Category.objects.first()
    assert cat_1 is not None and isinstance(cat_1.label, dict)
    assert "fr" in cat_1.label and "en" in cat_1.label

    assert CodeList.objects.count() >= 1
    assert CodeItem.objects.count() >= 2

    assert QuestionItem.objects.count() >= 2
    q_items = list(QuestionItem.objects.all())
    assert any(
        isinstance(q.question_text, dict) and "fr" in q.question_text and "en" in q.question_text
        for q in q_items
    )
    assert any(
        isinstance(q.interviewer_instructions, dict) and "fr" in q.interviewer_instructions
        for q in q_items
    )

    # Verify Variable Cascade & QuestionVariable shortcut table
    assert RepresentedVariable.objects.count() >= 2
    assert InstanceVariable.objects.count() == 2
    assert QuestionVariable.objects.count() >= 2

    # Verify Datafile, DatafileVariable (sumStat) & DatafileVariableFrequency (catStat)
    assert Datafile.objects.count() >= 1
    assert DatafileVariable.objects.count() >= 2
    assert DatafileVariableFrequency.objects.count() >= 4

    # 5. Undo promotion and verify clean rollback
    undo_res = undo_promotion(import_id)
    assert undo_res["status"] == "staged"
    assert undo_res["deleted_core_resources_count"] > 0
    assert InstanceVariable.objects.count() == 0
    assert StagedImport.objects.get(id=import_id).status == "staged"


# -----------------------------------------------------------------------------
# Use Case 3: DDI-Lifecycle 3.3 XML -> Stage -> Promote (InstrumentQuestion)
# -----------------------------------------------------------------------------


@pytest.mark.django_db
def test_ddil33_preflight_stage_promote_and_instrument_shortcuts(
    sample_cso_xml: Path, tmp_path: Path
) -> None:
    plan = run_preflight_check(sample_cso_xml)
    assert plan.summary["specification"] == "DDI-L"
    assert "quality_score" in plan.summary
    assert "quality_grade" in plan.summary

    stage_res = stage_metadata_file(sample_cso_xml, profile="request", force_reload=True)
    import_id = stage_res["staged_import_id"]
    assert import_id is not None

    promo_res = apply_promotion(import_id, auto_approve=True)
    assert promo_res["created_count"] > 0
    assert Category.objects.count() > 0
    assert CodeList.objects.count() > 0
    assert QuestionItem.objects.count() > 0
    assert Instrument.objects.count() >= 1
    assert StudyInstrument.objects.count() >= 1
    assert InstrumentQuestion.objects.count() > 0

    # Test storage compaction on the promoted batch
    compact_res = cleanup_staged_import(import_id=import_id, compact_only=True)
    assert compact_res["mode"] == "compacted"
    assert compact_res["compacted_nodes_count"] > 0
    sample_node = StagedResourceNode.objects.filter(staged_import_id=import_id).first()
    assert sample_node is not None and sample_node.raw_value == {"_compacted": True}


# -----------------------------------------------------------------------------
# Stage 3: Comparison, Discovery & Review-Gated Harmonization + Undo
# -----------------------------------------------------------------------------


@pytest.mark.django_db
def test_compare_discover_and_harmonize_with_undo(tmp_path: Path) -> None:
    # Seed two complementary categories & question items across two survey waves
    StudyUnit.objects.create(
        urn="urn:ddi:fr.cdsp:study_w1:1.0.0",
        agency="fr.cdsp",
        identifier="study_w1",
        version="1.0.0",
        name="Wave 1",
        label={"fr": "Vague 1"},
    )
    StudyUnit.objects.create(
        urn="urn:ddi:fr.cdsp:study_w2:1.0.0",
        agency="fr.cdsp",
        identifier="study_w2",
        version="1.0.0",
        name="Wave 2",
        label={"fr": "Vague 2"},
    )

    # Wave 1 has FR only; Wave 2 has FR + EN (MULTILINGUAL_OVERLAP)
    Category.objects.create(
        urn="urn:ddi:fr.cdsp:cat_w1_yes:1.0.0",
        agency="fr.cdsp",
        identifier="cat_w1_yes",
        version="1.0.0",
        name="Yes_W1",
        label={"fr": "Tout à fait d'accord", "en": "Strongly agree"},
    )
    Category.objects.create(
        urn="urn:ddi:fr.cdsp:cat_w2_yes:1.0.0",
        agency="fr.cdsp",
        identifier="cat_w2_yes",
        version="1.0.0",
        name="Yes_W2",
        label={"fr": "Tout à fait d'accord"},
    )

    # Near-similar QuestionItems (SYNTACTIC_SIMILAR -> requires_review=True)
    QuestionItem.objects.create(
        urn="urn:ddi:fr.cdsp:qi_w1_trust:1.0.0",
        agency="fr.cdsp",
        identifier="qi_w1_trust",
        version="1.0.0",
        name="Q_Trust_W1",
        question_text={"en": "Do you have confidence in the national parliament?"},
    )
    QuestionItem.objects.create(
        urn="urn:ddi:fr.cdsp:qi_w2_trust:1.0.0",
        agency="fr.cdsp",
        identifier="qi_w2_trust",
        version="1.0.0",
        name="Q_Trust_W2",
        question_text={"en": "Do you have confidence in the European parliament?"},
    )

    # 1. Discover candidates
    candidates = discover_candidates(threshold=0.75)
    assert len(candidates) >= 2
    match_types = {c["match_type"] for c in candidates}
    assert "MULTILINGUAL_OVERLAP" in match_types
    assert "SYNTACTIC_SIMILAR" in match_types

    # 2. Plan harmonization (without auto_approve -> requires review because of SYNTACTIC_SIMILAR)
    harm_plan = plan_harmonization(threshold=0.75, output_dir=tmp_path)
    assert harm_plan.pending_review_count >= 1
    assert harm_plan.is_ready_to_execute(auto_approve=False) is False

    # Attempting to apply without approval raises PermissionError
    with pytest.raises(PermissionError):
        apply_harmonization(harm_plan, auto_approve=False)

    # 3. Approve the plan YAML and apply harmonization
    plan_yaml_path = tmp_path / f"{harm_plan.job_id}.harmonize.plan.yaml"
    loaded_plan = harm_plan.from_yaml(plan_yaml_path)
    loaded_plan.review_gate.approved = True
    loaded_plan.review_gate.reviewer = "Archivist QA"
    loaded_plan.to_yaml(plan_yaml_path)

    apply_res = apply_harmonization(plan_yaml_path)
    assert apply_res["merged_multilingual_count"] >= 1
    assert apply_res["semantic_links_created"] >= 2

    # Check that cat_w2_yes received the English translation from cat_w1_yes
    cat_w2 = Category.objects.get(urn="urn:ddi:fr.cdsp:cat_w2_yes:1.0.0")
    assert cat_w2.label == {"en": "Strongly agree", "fr": "Tout à fait d'accord"}
    assert SemanticRelationship.objects.count() >= 2

    # 4. Undo harmonization and verify restoration
    undo_res = undo_harmonization(harm_plan.job_id)
    assert undo_res["status"] == "reverted"
    cat_w2.refresh_from_db()
    assert cat_w2.label == {"fr": "Tout à fait d'accord"}


# -----------------------------------------------------------------------------
# End-to-End Pipeline & CLI Group Tests
# -----------------------------------------------------------------------------


@pytest.mark.django_db
def test_cli_pipeline_and_subcommands(
    runner: CliRunner, bilingual_ddic_file: Path, tmp_path: Path
) -> None:
    out_dir = tmp_path / "cli_out"

    # 1. fairwddi preflight check
    res_check = runner.invoke(
        app, ["preflight", "check", str(bilingual_ddic_file), "--output-dir", str(out_dir)]
    )
    assert res_check.exit_code == 0
    assert "Preflight Readiness Check" in res_check.stdout

    # 2. fairwddi ingest run (end-to-end with --auto-approve and --compact)
    res_run = runner.invoke(
        app,
        [
            "ingest",
            "run",
            str(bilingual_ddic_file),
            "--output-dir",
            str(out_dir),
            "--auto-approve",
            "--compact",
            "--force-reload",
        ],
    )
    assert res_run.exit_code == 0
    assert "completed" in res_run.stdout

    staged = StagedImport.objects.latest("id")

    # 3. fairwddi compare batch & discover
    res_cmp = runner.invoke(app, ["compare", "batch", str(staged.id)])
    assert res_cmp.exit_code == 0
    res_disc = runner.invoke(app, ["compare", "discover", "--threshold", "0.5"])
    assert res_disc.exit_code == 0

    # 4. fairwddi promote undo
    res_undo = runner.invoke(app, ["promote", "undo", str(staged.id)])
    assert res_undo.exit_code == 0
    assert "Rolled back Batch" in res_undo.stdout
