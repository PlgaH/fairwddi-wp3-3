"""Comprehensive tests for the Phase 2 Ingestion & Harmonization Pipeline (`fairwddi.ingest`).

Covers:
1. Use Case 1: Classic DDI-Codebook -> preflight -> upgrade (ddi4-json/jsonl) -> direct ingest.
2. Use Case 2: Multilingual DDI-Codebook (fr/en) -> upgrade -> direct ingest (JSONB + frequencies).
3. Use Case 3: DDI-Lifecycle 3.3 XML & 4.0 JSON -> preflight -> direct ingest (shortcuts).
4. Lightweight `IngestBatch` receipts & 1-click Rollback (`undo_ingestion`).
5. Stage 3 Comparison (`discover_candidates`, `compare_batch`) & Harmonization (`plan/apply/undo`).
6. CLI command groups (`preflight`, `ingest`, `compare`, `harmonize`).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from fairwddi.cli import app
from fairwddi.ingest import (
    apply_harmonization,
    apply_ingestion,
    discover_candidates,
    plan_harmonization,
    plan_ingestion,
    run_preflight_check,
    undo_harmonization,
    undo_ingestion,
    upgrade_ddic_to_ddil,
)
from fairwddi.models import (
    Category,
    CodeItem,
    CodeList,
    Datafile,
    DatafileVariable,
    DatafileVariableFrequency,
    IngestBatch,
    InstanceVariable,
    Instrument,
    InstrumentQuestion,
    QuestionItem,
    QuestionVariable,
    RepresentedVariable,
    SemanticRelationship,
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
# Use Case 1 & 2: DDI-Codebook (Classic & Multilingual) Upgrade, Ingest & Undo
# -----------------------------------------------------------------------------


@pytest.mark.django_db
def test_bilingual_ddic_preflight_upgrade_ingest_and_undo(
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

    # 3. Direct Ingestion Plan (zero DB writes) & Apply into ReQuest core tables
    ing_plan = plan_ingestion(upg_jsonl["output_file"], profile="request", output_dir=out_dir)
    assert ing_plan.stage == "ingest"
    assert ing_plan.is_ready_to_execute() is True
    assert ing_plan.summary["planned_frequency_rows"] == 4
    assert IngestBatch.objects.count() == 0

    ing_res = apply_ingestion(ing_plan)
    assert ing_res["status"] == "completed"
    batch_id = ing_res["batch_id"]
    assert batch_id is not None
    assert ing_res["created_count"] > 0
    assert ing_res["frequency_rows_count"] == 4

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

    # Verify Datafile, DatafileVariable (sumStat dict) & DatafileVariableFrequency (bulk SQL rows)
    assert Datafile.objects.count() >= 1
    assert DatafileVariable.objects.count() >= 2
    dfv = DatafileVariable.objects.exclude(statistics={}).first()
    assert dfv is not None and dfv.statistics.get("valid") == 1180
    assert DatafileVariableFrequency.objects.count() == 4

    # 4. Undo ingestion and verify clean cascading rollback (including SQL frequencies)
    undo_res = undo_ingestion(batch_id)
    assert undo_res["status"] == "undone"
    assert undo_res["deleted_core_resources_count"] > 0
    assert InstanceVariable.objects.count() == 0
    assert DatafileVariableFrequency.objects.count() == 0
    assert IngestBatch.objects.get(id=batch_id).status == "undone"


# -----------------------------------------------------------------------------
# Use Case 3: DDI-Lifecycle 3.3 XML -> Direct Ingest (InstrumentQuestion)
# -----------------------------------------------------------------------------


@pytest.mark.django_db
def test_ddil33_preflight_ingest_and_instrument_shortcuts(sample_cso_xml: Path) -> None:
    plan = run_preflight_check(sample_cso_xml)
    assert plan.summary["specification"] == "DDI-L"
    assert "quality_score" in plan.summary
    assert "quality_grade" in plan.summary

    ing_res = apply_ingestion(
        sample_cso_xml, profile="request", force_reload=True, auto_approve=True
    )
    batch_id = ing_res["batch_id"]
    assert batch_id is not None
    assert ing_res["created_count"] > 0
    assert Category.objects.count() > 0
    assert CodeList.objects.count() > 0
    assert QuestionItem.objects.count() > 0
    assert Instrument.objects.count() >= 1
    assert StudyInstrument.objects.count() >= 1
    assert InstrumentQuestion.objects.count() > 0

    undo_res = undo_ingestion(batch_id)
    assert undo_res["status"] == "undone"
    assert InstrumentQuestion.objects.count() == 0


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
    )
    StudyUnit.objects.create(
        urn="urn:ddi:fr.cdsp:study_w2:1.0.0",
        agency="fr.cdsp",
        identifier="study_w2",
        version="1.0.0",
        name="Wave 2",
    )

    # Wave 1 has FR + EN; Wave 2 has FR only (MULTILINGUAL_OVERLAP)
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

    # 2. fairwddi ingest run (end-to-end preflight -> upgrade -> direct ingest)
    res_run = runner.invoke(
        app,
        [
            "ingest",
            "run",
            str(bilingual_ddic_file),
            "--output-dir",
            str(out_dir),
            "--auto-approve",
            "--force-reload",
        ],
    )
    assert res_run.exit_code == 0
    assert "completed" in res_run.stdout

    batch = IngestBatch.objects.latest("id")

    # 3. fairwddi compare batch & discover
    res_cmp = runner.invoke(app, ["compare", "batch", str(batch.id)])
    assert res_cmp.exit_code == 0
    res_disc = runner.invoke(app, ["compare", "discover", "--threshold", "0.5"])
    assert res_disc.exit_code == 0

    # 4. fairwddi ingest undo
    res_undo = runner.invoke(app, ["ingest", "undo", str(batch.id)])
    assert res_undo.exit_code == 0
    assert "Rolled back Batch" in res_undo.stdout


@pytest.mark.django_db
def test_ddic_custom_profile_variables_and_questions(tmp_path: Path) -> None:
    """Verify request.ddic.yaml enforces variable presence and warns on missing questions."""
    # 1. Codebook with NO variables -> Must produce an ERROR
    no_vars_xml = tmp_path / "no_vars.ddic.xml"
    no_vars_xml.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<codeBook xmlns="ddi:codebook:2_5" version="2.5" ID="STUDY_001">
  <stdyDscr>
    <citation>
      <titlStmt>
        <titl>Empty Study Without Variables</titl>
      </titlStmt>
    </citation>
  </stdyDscr>
  <dataDscr/>
</codeBook>""",
        encoding="utf-8",
    )
    plan_no_vars = run_preflight_check(no_vars_xml, profile="request")
    assert plan_no_vars.summary["profile_id"] == "request.ddic"
    var_err = [i for i in plan_no_vars.issues if i.code == "request.ddic.variables_required"]
    assert len(var_err) == 1
    assert var_err[0].severity == "error"

    # 2. Codebook with variables but NO questions -> Must produce a WARNING
    vars_no_qstn_xml = tmp_path / "vars_no_qstn.ddic.xml"
    vars_no_qstn_xml.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<codeBook xmlns="ddi:codebook:2_5" version="2.5" ID="STUDY_002">
  <stdyDscr>
    <citation>
      <titlStmt>
        <titl>Study With Variables but No Questions</titl>
      </titlStmt>
    </citation>
  </stdyDscr>
  <dataDscr>
    <var ID="V1" name="AGE">
      <labl>Age of respondent</labl>
    </var>
  </dataDscr>
</codeBook>""",
        encoding="utf-8",
    )
    plan_no_qstn = run_preflight_check(vars_no_qstn_xml, profile="request")
    assert plan_no_qstn.summary["profile_id"] == "request.ddic"
    # Variables required passed (no error)
    assert not any(i.code == "request.ddic.variables_required" for i in plan_no_qstn.issues)
    # Questions recommended produced warning
    qstn_warn = [i for i in plan_no_qstn.issues if i.code == "request.ddic.questions_recommended"]
    assert len(qstn_warn) == 1
    assert qstn_warn[0].severity == "warning"

    # 3. Codebook with both variables and questions -> Both pass
    vars_with_qstn_xml = tmp_path / "vars_with_qstn.ddic.xml"
    vars_with_qstn_xml.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<codeBook xmlns="ddi:codebook:2_5" version="2.5" ID="STUDY_003">
  <stdyDscr>
    <citation>
      <titlStmt>
        <titl>Complete Question-Bank Study</titl>
      </titlStmt>
    </citation>
  </stdyDscr>
  <dataDscr>
    <var ID="V1" name="AGE">
      <labl>Age of respondent</labl>
      <qstn ID="Q1">
        <qstnLit>How old are you?</qstnLit>
      </qstn>
    </var>
  </dataDscr>
</codeBook>""",
        encoding="utf-8",
    )
    plan_complete = run_preflight_check(vars_with_qstn_xml, profile="request")
    assert plan_complete.summary["profile_id"] == "request.ddic"
    assert not any(i.code == "request.ddic.variables_required" for i in plan_complete.issues)
    assert not any(i.code == "request.ddic.questions_recommended" for i in plan_complete.issues)

