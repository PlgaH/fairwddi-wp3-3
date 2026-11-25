"""Tests for the read-only two-set, three-layer comparison engine (`fairwddi.compare`)."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from fairwddi.compare import (
    CodeListQualification,
    ComparisonResultSet,
    CorrespondenceLevel,
    list_comparison_configs,
    run_comparison,
)


def _create_var_with_codes(
    suffix: str,
    *,
    question_fr: str,
    var_label_fr: str,
    codes: list[tuple[str, str, bool]],
    origin: str = "imported",
    concept: object | None = None,
) -> tuple[str, str, str]:
    from fairwddi.models import (
        Category,
        Code,
        CodeList,
        ConceptualVariable,
        QuestionItem,
        QuestionVariable,
        RepresentedVariable,
    )

    cl_urn = f"urn:ddi:fr.cdsp:cl_{suffix}:1.0.0"
    cl = CodeList.objects.create(urn=cl_urn, name=f"CL_{suffix}", origin=origin)
    for idx, (c_val, lbl_fr, is_miss) in enumerate(codes, start=1):
        cat = Category.objects.create(
            urn=f"urn:ddi:fr.cdsp:cat_{suffix}_{idx}:1.0.0",
            name=f"CAT_{suffix}_{idx}",
            label={"fr": lbl_fr},
            is_missing=is_miss,
            origin=origin,
        )
        Code.objects.create(
            urn=f"urn:ddi:fr.cdsp:code_{suffix}_{idx}:1.0.0",
            code_list=cl,
            category=cat,
            code_value=c_val,
            order=idx,
            is_missing=is_miss,
            origin=origin,
        )

    cv = None
    if concept is not None:
        cv = ConceptualVariable.objects.create(
            urn=f"urn:ddi:fr.cdsp:cv_{suffix}:1.0.0",
            name=f"CV_{suffix}",
            label={"fr": var_label_fr},
            concept=concept,
            origin=origin,
        )

    qi_urn = f"urn:ddi:fr.cdsp:qi_{suffix}:1.0.0"
    qi = QuestionItem.objects.create(
        urn=qi_urn,
        name=f"QI_{suffix}",
        question_text={"fr": question_fr},
        origin=origin,
    )
    rv_urn = f"urn:ddi:fr.cdsp:rv_{suffix}:1.0.0"
    rv = RepresentedVariable.objects.create(
        urn=rv_urn,
        name=f"RV_{suffix}",
        label={"fr": var_label_fr},
        code_list=cl,
        conceptual_variable=cv,
        origin=origin,
    )
    QuestionVariable.objects.create(question_item=qi, represented_variable=rv, order=1)
    return qi_urn, rv_urn, cl_urn


@pytest.mark.django_db
def test_compare_is_strictly_read_only_and_covers_three_layers_and_qualifications(
    tmp_path: Path,
) -> None:
    """Verify read-only execution across syntactic, semantic, conceptual & CodeList checks."""
    from fairwddi.groups import create_group
    from fairwddi.models import (
        Concept,
        ConceptScheme,
        SemanticRelationship,
        UrnRegistry,
    )

    cs = ConceptScheme.objects.create(
        urn="urn:ddi:elsst:cs_politics:1.0.0",
        name={"en": "ELSST Politics"},
        origin="instantiated",
    )
    con_root = Concept.objects.create(
        urn="urn:ddi:elsst:con_politics:1.0.0",
        scheme=cs,
        label={"en": "POLITICAL BEHAVIOUR", "fr": "COMPORTEMENT POLITIQUE"},
        vocabulary="ELSST",
        origin="instantiated",
    )
    con_interest = Concept.objects.create(
        urn="urn:ddi:elsst:con_interest:1.0.0",
        scheme=cs,
        parent=con_root,
        label={"en": "POLITICAL INTEREST", "fr": "INTÉRÊT POLITIQUE"},
        vocabulary="ELSST",
        origin="instantiated",
    )
    con_trust = Concept.objects.create(
        urn="urn:ddi:elsst:con_trust:1.0.0",
        scheme=cs,
        parent=con_root,
        label={"en": "POLITICAL TRUST", "fr": "CONFIANCE POLITIQUE"},
        vocabulary="ELSST",
        origin="instantiated",
    )

    # Pair A: identical wording + identical substantive scale, only missing value code differs
    q_a1, rv_a1, _ = _create_var_with_codes(
        "a1",
        question_fr="Êtes-vous satisfait(e) du fonctionnement de la démocratie ?",
        var_label_fr="Satisfaction démocratie",
        codes=[
            ("1", "Très satisfait", False),
            ("2", "Plutôt satisfait", False),
            ("3", "Pas du tout satisfait", False),
            ("9", "Ne sait pas", True),
        ],
        concept=con_interest,
    )
    q_a2, rv_a2, _ = _create_var_with_codes(
        "a2",
        question_fr="Êtes-vous satisfait du fonctionnement de la démocratie ?",
        var_label_fr="Satisfaction démocratie",
        codes=[
            ("1", "Très satisfait", False),
            ("2", "Plutôt satisfait", False),
            ("3", "Pas du tout satisfait", False),
            ("8", "NSP", True),
            ("9", "Refus", True),
        ],
        concept=con_interest,
    )

    # Pair B: Same concept family via ELSST parent + paraphrase + 4-pt vs 5-pt scale mismatch
    q_b1, rv_b1, _ = _create_var_with_codes(
        "b1",
        question_fr="Dans quelle mesure vous intéressez-vous personnellement à la vie politique ?",
        var_label_fr="Intérêt politique personnel",
        codes=[
            ("1", "Beaucoup", False),
            ("2", "Assez", False),
            ("3", "Peu", False),
            ("4", "Pas du tout", False),
        ],
        concept=con_interest,
    )
    q_b2, rv_b2, _ = _create_var_with_codes(
        "b2",
        question_fr="Quel intérêt portez-vous à l'actualité politique en général ?",
        var_label_fr="Intérêt politique général",
        codes=[
            ("1", "Énormément", False),
            ("2", "Beaucoup", False),
            ("3", "Moyennement", False),
            ("4", "Peu", False),
            ("5", "Pas du tout", False),
        ],
        concept=con_trust,
    )

    create_group("Wave Source", slug="src-w", member_urns=[q_a1, rv_a1, q_b1, rv_b1])
    create_group("Wave Target", slug="tgt-w", member_urns=[q_a2, rv_a2, q_b2, rv_b2])

    urn_before = UrnRegistry.objects.count()
    rel_before = SemanticRelationship.objects.count()

    # Run all 3 levels read-only
    res = run_comparison(
        source="group:src-w",
        target="group:tgt-w",
        levels=["syntactic", "semantic", "conceptual"],
        resource_types=["QuestionItem", "RepresentedVariable"],
        output_dir=tmp_path,
        output_format="yaml",
    )

    # Strictly zero DB writes
    assert UrnRegistry.objects.count() == urn_before
    assert SemanticRelationship.objects.count() == rel_before
    assert (tmp_path / f"{res.job_id}.comparison.yaml").exists()
    assert (tmp_path / f"{res.job_id}.comparison.report.md").exists()

    # Reload round-trip
    loaded = ComparisonResultSet.from_yaml(tmp_path / f"{res.job_id}.comparison.yaml")
    assert loaded.job_id == res.job_id

    # Syntactic match on inclusive/punctuation variant A1 vs A2 -> MISSING_VALUES_ONLY!
    a_syn = next(
        (
            c
            for c in res.candidates
            if c.source_urn == q_a1
            and c.target_urn == q_a2
            and c.level == CorrespondenceLevel.SYNTACTIC
        ),
        None,
    )
    assert a_syn is not None
    assert a_syn.confidence >= 0.90
    assert a_syn.qualification.codelist_qualification == CodeListQualification.MISSING_VALUES_ONLY
    assert a_syn.qualification.administration_context_caveat is not None

    # Conceptual hierarchy match across RV_B1 (con_interest) and RV_B2 (con_trust) via con_politics
    b_con = next(
        (
            c
            for c in res.candidates
            if c.source_urn == rv_b1
            and c.target_urn == rv_b2
            and c.level == CorrespondenceLevel.CONCEPTUAL
        ),
        None,
    )
    assert b_con is not None
    assert (
        b_con.qualification.codelist_qualification == CodeListQualification.SCALE_CARDINALITY_DIFF
    )
    assert b_con.recommended_action == "link_semantic"


@pytest.mark.django_db
def test_compare_semantic_tfidf_recoded_dimension_and_scaffolds(tmp_path: Path) -> None:
    """Test Level 2 TF-IDF + mock agent, dimension mismatch, recoding, and Level 3 scaffold."""
    from fairwddi.compare.config import (
        ComparisonConfig,
        ConceptualRuleConfig,
        ResourceTypeComparisonRule,
        SemanticRuleConfig,
    )
    from fairwddi.compare.semantic import SentenceTransformerEmbeddingProvider

    # Frequency vs. Intensity dimension mismatch on same-cardinality scales
    _, rv_freq, _ = _create_var_with_codes(
        "freq",
        question_fr="À quelle fréquence discutez-vous de politique avec vos amis ?",
        var_label_fr="Discussions politiques",
        codes=[("1", "Souvent", False), ("2", "Parfois", False), ("3", "Jamais", False)],
    )
    _, rv_int, _ = _create_var_with_codes(
        "int",
        question_fr="Parlez-vous de politique avec vos proches ?",
        var_label_fr="Discussions politiques avec proches",
        codes=[("1", "Beaucoup", False), ("2", "Un peu", False), ("3", "Pas du tout", False)],
    )

    sem_cfg = ComparisonConfig(
        name="custom-sem",
        levels=[CorrespondenceLevel.SEMANTIC],
        resource_types=["RepresentedVariable"],
        rules={
            "RepresentedVariable": ResourceTypeComparisonRule(
                fields=["label", "question_text"],
                syntactic={"enabled": False},
                semantic=SemanticRuleConfig(
                    enabled=True, threshold=0.20, provider="tfidf", agent_backend="mock"
                ),
                conceptual=ConceptualRuleConfig(enabled=False),
            )
        },
    )
    res = run_comparison(
        source=f"urn:{rv_freq}",
        target=f"urn:{rv_int}",
        config=sem_cfg,
    )
    assert len(res.candidates) == 1
    c = res.candidates[0]
    assert c.level == CorrespondenceLevel.SEMANTIC
    assert (
        c.qualification.codelist_qualification == CodeListQualification.DIMENSION_MISMATCH_SUSPECTED
    )
    assert "agent_decision" in c.details

    # ConceptAssigner raises NotImplementedError when auto_assign_concepts=True without plugin
    con_cfg = ComparisonConfig(
        levels=[CorrespondenceLevel.CONCEPTUAL],
        resource_types=["RepresentedVariable"],
        rules={
            "RepresentedVariable": ResourceTypeComparisonRule(
                conceptual=ConceptualRuleConfig(enabled=True, auto_assign_concepts=True),
            )
        },
    )
    with pytest.raises(NotImplementedError):
        run_comparison(source=f"urn:{rv_freq}", target=f"urn:{rv_int}", config=con_cfg)

    # Optional dense provider fails gracefully when sentence-transformers isn't installed
    st = SentenceTransformerEmbeddingProvider()
    try:
        st.embed_texts(["test"])
    except ImportError as exc:
        assert "sentence-transformers" in str(exc)


@pytest.mark.django_db
def test_cli_compare_configs_init_and_run(tmp_path: Path) -> None:
    """Verify `fairwddi compare configs`, `init-config`, and `run` CLI commands."""
    from fairwddi.cli import app
    from fairwddi.models import QuestionItem

    assert len(list_comparison_configs()) >= 4

    q1 = QuestionItem.objects.create(
        urn="urn:ddi:fr.cdsp:qi_c1:1.0.0",
        name="QC1",
        question_text={"fr": "Faites-vous confiance aux syndicats ?"},
        origin="imported",
    )
    q2 = QuestionItem.objects.create(
        urn="urn:ddi:fr.cdsp:qi_c2:1.0.0",
        name="QC2",
        question_text={"fr": "Faites-vous confiance aux syndicats"},
        origin="imported",
    )

    runner = CliRunner()
    assert runner.invoke(app, ["compare", "configs"]).exit_code == 0

    cfg_out = tmp_path / "my_cmp.yaml"
    init_res = runner.invoke(app, ["compare", "init-config", str(cfg_out), "--preset", "syntactic"])
    assert init_res.exit_code == 0
    assert cfg_out.exists()

    out_dir = tmp_path / "cmp_out"
    run_res = runner.invoke(
        app,
        [
            "compare",
            "run",
            "--source",
            f"urn:{q1.urn}",
            "--target",
            f"urn:{q2.urn}",
            "--level",
            "syntactic",
            "--type",
            "QuestionItem",
            "--output-dir",
            str(out_dir),
            "--format",
            "json",
        ],
    )
    assert run_res.exit_code == 0, run_res.output
    assert list(out_dir.glob("*.comparison.json"))
    assert list(out_dir.glob("*.comparison.report.md"))
