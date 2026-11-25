"""Tests for policy-driven harmonization (`fairwddi.harmonize`) & CLI `plan`/`execute`."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from fairwddi.compare import run_comparison
from fairwddi.harmonize import (
    HarmonizationPlan,
    approve_high_actions,
    create_harmonized_resource,
    execute_harmonization,
    link_to_harmonized_resource,
    load_harmonization_policy,
    plan_harmonization,
    undo_harmonization,
)


@pytest.mark.django_db
def test_harmonize_plan_approve_high_guardrails_execute_and_undo(tmp_path: Path) -> None:
    """Verify policy `--approve-high`, `--keep-pending`, CodeList guardrails, execute & undo."""
    from fairwddi.models import (
        Category,
        Code,
        CodeList,
        QuestionItem,
        RepresentedVariable,
        SemanticRelationship,
        UrnRegistry,
    )

    # 1. Exact/near-exact syntactic QuestionItem pair (should qualify as 'high')
    q1 = QuestionItem.objects.create(
        urn="urn:ddi:fr.cdsp:qi_h1:1.0.0",
        name="QH1",
        question_text={"fr": "Êtes-vous satisfait(e) de votre vie ?"},
        origin="imported",
    )
    q2 = QuestionItem.objects.create(
        urn="urn:ddi:fr.cdsp:qi_h2:1.0.0",
        name="QH2",
        question_text={"fr": "Êtes-vous satisfait de votre vie ?"},
        origin="imported",
    )

    # 2. RepresentedVariable pair with matching label but divergent 4 vs 5 scale (must downgrade!)
    cl4 = CodeList.objects.create(urn="urn:ddi:fr.cdsp:cl_h4:1.0.0", name="CL4", origin="imported")
    for idx, lbl in enumerate(("Très", "Assez", "Peu", "Pas du tout"), start=1):
        c = Category.objects.create(
            urn=f"urn:ddi:fr.cdsp:cat_h4_{idx}:1.0.0",
            name=f"H4_{idx}",
            label={"fr": lbl},
            origin="imported",
        )
        Code.objects.create(
            urn=f"urn:ddi:fr.cdsp:code_h4_{idx}:1.0.0",
            code_list=cl4,
            category=c,
            code_value=str(idx),
            order=idx,
            origin="imported",
        )
    cl5 = CodeList.objects.create(urn="urn:ddi:fr.cdsp:cl_h5:1.0.0", name="CL5", origin="imported")
    for idx, lbl in enumerate(("Énormément", "Très", "Assez", "Peu", "Pas du tout"), start=1):
        c = Category.objects.create(
            urn=f"urn:ddi:fr.cdsp:cat_h5_{idx}:1.0.0",
            name=f"H5_{idx}",
            label={"fr": lbl},
            origin="imported",
        )
        Code.objects.create(
            urn=f"urn:ddi:fr.cdsp:code_h5_{idx}:1.0.0",
            code_list=cl5,
            category=c,
            code_value=str(idx),
            order=idx,
            origin="imported",
        )
    rv1 = RepresentedVariable.objects.create(
        urn="urn:ddi:fr.cdsp:rv_h4:1.0.0",
        name="RVH4",
        label={"fr": "Satisfaction vie actuelle"},
        code_list=cl4,
        origin="imported",
    )
    rv2 = RepresentedVariable.objects.create(
        urn="urn:ddi:fr.cdsp:rv_h5:1.0.0",
        name="RVH5",
        label={"fr": "Satisfaction vie actuelle"},
        code_list=cl5,
        origin="imported",
    )

    cmp_res = run_comparison(
        source=f"urn:{q1.urn},{rv1.urn}",
        target=f"urn:{q2.urn},{rv2.urn}",
        levels=["syntactic"],
    )

    pol = load_harmonization_policy("default")
    assert pol.auto_approve_high.min_confidence == 0.90

    # Without --approve-high: all actions start pending review
    pending_plan = plan_harmonization(cmp_res)
    assert pending_plan.approved_count == 0
    assert pending_plan.pending_review_count == len(pending_plan.actions)
    assert pending_plan.review_gate.approved is False
    with pytest.raises(PermissionError):
        execute_harmonization(pending_plan)

    # With --keep-pending overriding --approve-high
    kept_plan = plan_harmonization(cmp_res, approve_high=True, keep_pending=True)
    assert kept_plan.approved_count == 0
    assert kept_plan.review_gate.approved is False

    # With --approve-high: QuestionItem approved; SCALE_CARDINALITY_DIFF RV downgraded & pending
    auto_plan = plan_harmonization(cmp_res, approve_high=True, output_dir=tmp_path)
    assert (tmp_path / f"{auto_plan.job_id}.harmonize.plan.yaml").exists()
    q_act = next(a for a in auto_plan.actions if a.resource_type == "QuestionItem")
    rv_act = next(a for a in auto_plan.actions if a.resource_type == "RepresentedVariable")
    assert q_act.approval_tier == "high"
    assert q_act.approved is True
    assert rv_act.action == "link_semantic"
    assert rv_act.approval_tier == "review_required"
    assert rv_act.approved is False
    assert auto_plan.review_gate.approved is True

    # Execute plan WITHOUT needing a separate approve-high or --auto-approve call!
    exec_res = execute_harmonization(tmp_path / f"{auto_plan.job_id}.harmonize.plan.yaml")
    assert exec_res["generated_count"] == 1
    assert exec_res["skipped_unapproved_count"] == 1
    assert UrnRegistry.objects.filter(resource_type="QuestionItem", origin="generated").count() == 1
    # Check extended_attributes carry correspondence_level & codelist_qualification
    rel = SemanticRelationship.objects.filter(predicate="prov:wasDerivedFrom").first()
    assert rel is not None
    attr_map = {d["type"]: d["value"] for d in rel.extended_attributes if isinstance(d, dict)}
    assert attr_map.get("correspondence_level") == "syntactic"
    assert "codelist_qualification" in attr_map

    # Standalone approve_high_actions works on saved pending plan YAML
    p_yaml = tmp_path / "pending.harmonize.plan.yaml"
    pending_plan.to_yaml(p_yaml)
    triaged = approve_high_actions(p_yaml)
    assert triaged.approved_count >= 1
    reloaded = HarmonizationPlan.from_yaml(p_yaml)
    assert reloaded.approved_count == triaged.approved_count

    # Full rollback via undo_harmonization
    undo_res = undo_harmonization(exec_res["job_id"])
    assert undo_res["status"] == "reverted"
    assert UrnRegistry.objects.filter(resource_type="QuestionItem", origin="generated").count() == 0
    assert SemanticRelationship.objects.filter(predicate="prov:wasDerivedFrom").count() == 0


@pytest.mark.django_db
def test_cli_harmonize_plan_approve_high_and_execute(tmp_path: Path) -> None:
    """Test CLI cycle: `compare run` -> `harmonize plan --approve-high` -> `harmonize execute`."""
    from fairwddi.cli import app
    from fairwddi.models import QuestionItem

    q_inst = QuestionItem.objects.create(
        urn="urn:ddi:fr.cdsp:qi_inst:1.0.0",
        name="Q_INST",
        question_text={"fr": "Faites-vous confiance au parlement ?"},
        origin="instantiated",
    )
    q_imp = QuestionItem.objects.create(
        urn="urn:ddi:fr.cdsp:qi_imp:1.0.0",
        name="Q_IMP",
        question_text={"fr": "Faites-vous confiance au parlement"},
        origin="imported",
    )

    runner = CliRunner()
    cmp_dir = tmp_path / "cmp"
    r_cmp = runner.invoke(
        app,
        [
            "compare",
            "run",
            "--source",
            f"urn:{q_imp.urn}",
            "--target",
            f"urn:{q_inst.urn}",
            "--level",
            "syntactic",
            "--output-dir",
            str(cmp_dir),
        ],
    )
    assert r_cmp.exit_code == 0, r_cmp.output
    cmp_file = next(cmp_dir.glob("*.comparison.yaml"))

    plan_dir = tmp_path / "harm"
    r_plan = runner.invoke(
        app,
        [
            "harmonize",
            "plan",
            str(cmp_file),
            "--approve-high",
            "--output-dir",
            str(plan_dir),
        ],
    )
    assert r_plan.exit_code == 0, r_plan.output
    plan_file = next(plan_dir.glob("*.harmonize.plan.yaml"))

    r_exec = runner.invoke(app, ["harmonize", "execute", str(plan_file)])
    assert r_exec.exit_code == 0, r_exec.output
    assert "linked=1" in r_exec.output


@pytest.mark.django_db
def test_manual_create_and_link_harmonized_resources() -> None:
    """Verify manual create_harmonized_resource and link_to_harmonized_resource + undo."""
    from fairwddi.models import QuestionItem

    q1 = QuestionItem.objects.create(
        urn="urn:ddi:fr.cdsp:q_m1:1.0.0",
        name="QM1",
        question_text={"fr": "Question 1"},
        origin="imported",
    )
    q2 = QuestionItem.objects.create(
        urn="urn:ddi:fr.cdsp:q_m2:1.0.0",
        name="QM2",
        question_text={"en": "Question 1"},
        origin="imported",
    )
    c_res = create_harmonized_resource(source_urns=[q1.urn], origin="instantiated")
    l_res = link_to_harmonized_resource(source_urns=[q2.urn], target_urn=c_res["target_urn"])
    assert l_res["semantic_links_created"] == 1
    assert undo_harmonization(l_res["job_id"])["status"] == "reverted"
    assert undo_harmonization(c_res["job_id"])["status"] == "reverted"
