"""Tests for non-destructive Harmonization, Origin Categorization & W3C Lineage."""

from __future__ import annotations

from pathlib import Path

import pytest
from dartfx.ddi.harmonizer import MatchType

from fairwddi.ingest.comparator import discover_candidates
from fairwddi.ingest.harmonizer import (
    apply_harmonization,
    create_harmonized_resource,
    link_to_harmonized_resource,
    plan_harmonization,
    undo_harmonization,
)
from fairwddi.models import (
    Category,
    CodeItem,
    CodeList,
    ConceptualVariable,
    Group,
    QuestionItem,
    QuestionVariable,
    RepresentedVariable,
    SemanticRelationship,
    UrnRegistry,
)
from fairwddi.utils.urn import generate_generic_urn, slugify, validate_ddi_urn


def test_urn_validation_and_slug_generation() -> None:
    """Test canonical DDI URN syntax validation and slug generation."""
    assert validate_ddi_urn("urn:ddi:fr.cdsp:QI-trust-national-assembly-4f2a:1.0.0") is True
    assert validate_ddi_urn("urn:ddi:fr.cdsp:qi_V124_q1:3.0.0") is True
    assert validate_ddi_urn("urn:ddi:cessda.nesstar:study-01:1.0") is True

    assert validate_ddi_urn("not-a-urn") is False
    assert validate_ddi_urn("urn:ddi:fr.cdsp:too:many:colons:here:1.0.0") is False
    assert validate_ddi_urn("urn:ddi:fr.cdsp::1.0.0") is False
    assert validate_ddi_urn("urn:ddi:fr.cdsp:test-id:") is False

    assert slugify("Trust in National Assembly") == "trust-in-national-assembly"
    assert slugify("Confiance à l'Assemblée nationale !") == "confiance-a-lassemblee-nationale"
    assert slugify(None) == "generic"
    assert slugify("") == "generic"

    gen_urn = generate_generic_urn("QuestionItem", "Trust in National Assembly", agency="fr.cdsp")
    assert gen_urn.startswith("urn:ddi:fr.cdsp:QI-trust-in-national-assembly-")
    assert gen_urn.endswith(":1.0.0")
    assert validate_ddi_urn(gen_urn) is True


@pytest.mark.django_db
def test_create_harmonized_question_items_preserves_sources() -> None:
    """Test creating a generated harmonized QuestionItem while keeping imported sources intact."""
    qi1 = QuestionItem.objects.create(
        urn="urn:ddi:fr.cdsp:elipss.2015.q01:1.0.0",
        name=[{"value": "q01_2015"}],
        label=[{"lang": "fr", "value": "Confiance Assemblée (2015)"}],
        question_text=[{"lang": "fr", "value": "Faites-vous confiance à l'Assemblée ?"}],
        origin="imported",
    )
    qi2 = QuestionItem.objects.create(
        urn="urn:ddi:fr.cdsp:elipss.2016.q01:1.0.0",
        name=[{"value": "q01_2016"}],
        label=[{"lang": "en", "value": "Trust National Assembly (2016)"}],
        question_text=[{"lang": "en", "value": "Do you trust the National Assembly?"}],
        origin="imported",
    )

    rv = RepresentedVariable.objects.create(
        urn="urn:ddi:fr.cdsp:rv_trust:1.0.0",
        name=[{"value": "rv_trust"}],
        origin="imported",
    )
    qv = QuestionVariable.objects.create(question_item=qi1, represented_variable=rv)

    generic_urn = "urn:ddi:fr.cdsp:QI-trust-national-assembly:1.0.0"

    res = create_harmonized_resource(
        source_urns=[qi1.urn, qi2.urn],
        target_urn=generic_urn,
        name="Trust in National Assembly (Harmonized)",
        origin="generated",
    )

    assert res["target_urn"] == generic_urn
    assert res["resource_type"] == "QuestionItem"
    assert res["origin"] == "generated"
    assert res["semantic_links_created"] == 2

    gen_qi = QuestionItem.objects.get(urn=generic_urn)
    assert gen_qi.name == [{"value": "Trust in National Assembly (Harmonized)"}]
    assert gen_qi.question_text == [
        {"lang": "en", "value": "Do you trust the National Assembly?"},
        {"lang": "fr", "value": "Faites-vous confiance à l'Assemblée ?"},
    ]
    assert UrnRegistry.objects.get(urn=generic_urn).origin == "generated"

    # Imported sources are NEVER deleted or retired, and study cascade stays intact
    assert QuestionItem.objects.filter(urn=qi1.urn).exists() is True
    assert QuestionItem.objects.filter(urn=qi2.urn).exists() is True
    qv.refresh_from_db()
    assert qv.question_item_id == qi1.urn

    # Lineage recorded with W3C prov:wasDerivedFrom
    assert SemanticRelationship.objects.filter(
        subject_urn=generic_urn, predicate="prov:wasDerivedFrom", object_urn=qi1.urn
    ).exists()
    assert SemanticRelationship.objects.filter(
        subject_urn=generic_urn, predicate="prov:wasDerivedFrom", object_urn=qi2.urn
    ).exists()

    # Undo removes only the generated resource and lineage links
    undo_res = undo_harmonization(res["job_id"])
    assert undo_res["status"] == "reverted"
    assert undo_res["removed_target_urn"] == generic_urn
    assert QuestionItem.objects.filter(urn=generic_urn).exists() is False
    assert QuestionItem.objects.filter(urn=qi1.urn).exists() is True
    assert QuestionItem.objects.filter(urn=qi2.urn).exists() is True


@pytest.mark.django_db
def test_link_to_instantiated_resource_enriches_metadata() -> None:
    """Test linking an imported question into an existing instantiated harmonized resource."""
    generic_urn = "urn:ddi:fr.cdsp:QI-trust-institutions:1.0.0"
    inst_qi = QuestionItem.objects.create(
        urn=generic_urn,
        name=[{"value": "Trust Institutions Harmonized"}],
        label=[{"lang": "fr", "value": "Confiance institutions"}],
        question_text=[{"lang": "fr", "value": "Avez-vous confiance dans les institutions ?"}],
        origin="instantiated",
    )

    qi_wave3 = QuestionItem.objects.create(
        urn="urn:ddi:fr.cdsp:elipss.2017.q01:1.0.0",
        name=[{"value": "q01_2017"}],
        label=[{"lang": "es", "value": "Confianza en las instituciones"}],
        question_text=[
            {"lang": "fr", "value": "Avez-vous confiance dans les institutions?"},
            {"lang": "es", "value": "¿Confía en las instituciones?"},
        ],
        interviewer_instructions=[{"lang": "es", "value": "Leer pausadamente"}],
        origin="imported",
    )

    res = link_to_harmonized_resource(
        source_urns=[qi_wave3.urn],
        target_urn=generic_urn,
        provenance_note="Wave 3 longitudinal linkage",
    )

    assert res["target_urn"] == generic_urn
    assert res["target_origin"] == "instantiated"
    assert res["semantic_links_created"] == 1

    inst_qi.refresh_from_db()
    assert inst_qi.question_text == [
        {"lang": "es", "value": "¿Confía en las instituciones?"},
        {"lang": "fr", "value": "Avez-vous confiance dans les institutions ?"},
    ]
    assert inst_qi.interviewer_instructions == [{"lang": "es", "value": "Leer pausadamente"}]

    # Alternate French spelling recorded in extended_attributes
    variants = [
        a for a in (inst_qi.extended_attributes or []) if a.get("type") == "wording_variant"
    ]
    assert any(
        v["lang"] == "fr" and v["value"] == "Avez-vous confiance dans les institutions?"
        for v in variants
    )

    assert SemanticRelationship.objects.filter(
        subject_urn=generic_urn, predicate="prov:wasDerivedFrom", object_urn=qi_wave3.urn
    ).exists()

    # Undo cleanly restores inst_qi and preserves qi_wave3
    undo_res = undo_harmonization(res["job_id"])
    assert undo_res["status"] == "reverted"
    inst_qi.refresh_from_db()
    assert inst_qi.question_text == [
        {"lang": "fr", "value": "Avez-vous confiance dans les institutions ?"}
    ]
    assert inst_qi.interviewer_instructions is None
    assert QuestionItem.objects.filter(urn=qi_wave3.urn).exists() is True


@pytest.mark.django_db
def test_harmonizer_error_handling() -> None:
    """Test error conditions for create_harmonized_resource and link_to_harmonized_resource."""
    qi = QuestionItem.objects.create(
        urn="urn:ddi:fr.cdsp:qi_err_test:1.0.0",
        name=[{"value": "qi_err_test"}],
        origin="imported",
    )
    cv = ConceptualVariable.objects.create(
        urn="urn:ddi:fr.cdsp:cv_mismatch:1.0.0",
        name=[{"value": "cv_mismatch"}],
        origin="imported",
    )
    existing_gen = QuestionItem.objects.create(
        urn="urn:ddi:fr.cdsp:QI-already-existing:1.0.0",
        name=[{"value": "QI-already-existing"}],
        origin="generated",
    )

    with pytest.raises(ValueError, match="mismatched resource types"):
        create_harmonized_resource(source_urns=[qi.urn, cv.urn])

    with pytest.raises(ValueError, match="already exists in UrnRegistry"):
        create_harmonized_resource(source_urns=[qi.urn], target_urn=existing_gen.urn)

    with pytest.raises(ValueError, match="does not exist in UrnRegistry"):
        link_to_harmonized_resource(
            source_urns=[qi.urn],
            target_urn="urn:ddi:fr.cdsp:QI-non-existent:1.0.0",
        )

    with pytest.raises(ValueError, match="distinct from target_urn"):
        link_to_harmonized_resource(source_urns=[qi.urn], target_urn=qi.urn)


@pytest.mark.django_db
def test_near_exact_punctuation_and_tier1_link_in_plan(tmp_path: Path) -> None:
    """Test NEAR_EXACT punctuation variant detection and Tier 1 link_existing priority."""
    cat_2015 = Category.objects.create(
        urn="urn:ddi:fr.cdsp:QI-cat_ouvrier:3.0.0",
        name=[{"value": "cat_2_Ouvrier"}],
        label={"fr": "Ouvrier(e) qualifié(e) ou hautement qualifié(e), technicien(ne) d'atelier"},
        origin="generated",
    )
    cat_2013 = Category.objects.create(
        urn="urn:ddi:fr.cdsp:elipss.2013.cat_ouvrier:3.0.0",
        name=[{"value": "cat_2_Ouvrier_q"}],
        label={"fr": "Ouvrier(e) qualifié(e) ou hautement qualifié(e), technicien(ne) d'atelier ?"},
        origin="imported",
    )

    cands = discover_candidates(resource_type="Category", threshold=0.75)
    assert len(cands) == 1
    cand = cands[0]
    assert cand["match_type"] == "NEAR_EXACT"
    assert cand["confidence"] == 0.98
    assert cand["requires_review"] is True
    assert cand["source_urn"] == cat_2013.urn
    assert cand["target_urn"] == cat_2015.urn
    assert cand["recommended_action"] == "link_existing"

    plan = plan_harmonization(resource_type="Category", output_dir=tmp_path)
    assert plan.pending_review_count == 1
    assert plan.is_ready_to_execute(auto_approve=False) is False

    res = apply_harmonization(plan, auto_approve=True)
    assert res["linked_existing_count"] == 1

    # Verify alternate punctuation variant was added and imported source kept intact
    cat_2015.refresh_from_db()
    assert Category.objects.filter(urn=cat_2013.urn).exists() is True
    assert SemanticRelationship.objects.filter(
        subject_urn=cat_2015.urn, predicate="prov:wasDerivedFrom", object_urn=cat_2013.urn
    ).exists()

    undo_res = undo_harmonization(plan.job_id)
    assert undo_res["status"] == "reverted"


@pytest.mark.django_db
def test_shared_stem_question_grid_detection_and_generic_group(tmp_path: Path) -> None:
    """Test SHARED_STEM_GRID detection and Group creation with dcterms:isPartOf."""
    q_green = QuestionItem.objects.create(
        urn="urn:ddi:fr.cdsp:elipss.2015.qi_quartier_verts:1.0.0",
        name=[{"value": "qi_quartier_verts"}],
        question_text=[
            {
                "lang": "fr",
                "value": (
                    "Êtes-vous confronté(e) à un ou plusieurs des problèmes suivants "
                    "concernant votre quartier ? Manque d'espaces verts"
                ),
            }
        ],
        origin="imported",
    )
    q_sec = QuestionItem.objects.create(
        urn="urn:ddi:fr.cdsp:elipss.2015.qi_quartier_sec:1.0.0",
        name=[{"value": "qi_quartier_sec"}],
        question_text=[
            {
                "lang": "fr",
                "value": (
                    "Êtes-vous confronté(e) à un ou plusieurs des problèmes suivants "
                    "concernant votre quartier ? Manque de sécurité"
                ),
            }
        ],
        origin="imported",
    )

    cl1 = CodeList.objects.create(
        urn="urn:ddi:fr.cdsp:cl_yesno:1.0.0", name="cl_yesno", origin="imported"
    )
    cl2 = CodeList.objects.create(
        urn="urn:ddi:fr.cdsp:cl_scale:1.0.0", name="cl_scale", origin="imported"
    )
    rv_green = RepresentedVariable.objects.create(
        urn="urn:ddi:fr.cdsp:rv_quartier_verts:1.0.0",
        name="rv_quartier_verts",
        code_list=cl1,
        origin="imported",
    )
    rv_sec = RepresentedVariable.objects.create(
        urn="urn:ddi:fr.cdsp:rv_quartier_sec:1.0.0",
        name="rv_quartier_sec",
        code_list=cl2,
        origin="imported",
    )
    QuestionVariable.objects.create(question_item=q_green, represented_variable=rv_green)
    QuestionVariable.objects.create(question_item=q_sec, represented_variable=rv_sec)

    cands = discover_candidates(resource_type="QuestionItem", threshold=0.75)
    assert len(cands) == 1
    cand = cands[0]
    assert cand["match_type"] in (
        MatchType.SHARED_STEM,
        MatchType.SHARED_STEM_GRID,
        "SHARED_STEM",
        "SHARED_STEM_GRID",
    )
    assert cand["recommended_action"] == "group"
    assert cand["requires_review"] is True

    plan = plan_harmonization(resource_type="QuestionItem", output_dir=tmp_path)
    assert plan.pending_review_count == 1
    md = plan.to_markdown()
    assert "Shared-Stem Grids & Resource Groups" in md

    res = apply_harmonization(plan, auto_approve=True)
    assert res["grouped_count"] == 1

    groups = list(Group.objects.filter(group_type="question_grid"))
    assert len(groups) == 1
    grp = groups[0]
    assert grp.origin == "generated"
    ref_urns = {r["urn"] for r in (grp.references or [])}
    assert q_green.urn in ref_urns
    assert q_sec.urn in ref_urns
    assert SemanticRelationship.objects.filter(
        subject_urn=q_green.urn, predicate="dcterms:isPartOf", object_urn=grp.urn
    ).exists()

    undo_res = undo_harmonization(plan.job_id)
    assert undo_res["removed_groups"] == 1
    assert Group.objects.filter(urn=grp.urn).exists() is False


@pytest.mark.django_db
def test_phrasing_inclusive_and_typo_variants_in_plan(tmp_path: Path) -> None:
    """Test inclusive writing, phrasing, and typo variants generate harmonized resources."""
    q_inc = QuestionItem.objects.create(
        urn="urn:ddi:fr.cdsp:elipss.2015.qi_salete:1.0.0",
        name=[{"value": "qi_salete_2015"}],
        question_text=[
            {
                "lang": "fr",
                "value": (
                    "Êtes-vous confronté(e) à un ou plusieurs des problèmes suivants "
                    "concernant votre quartier ? Saleté des rues ou du quartier"
                ),
            }
        ],
        origin="imported",
    )
    QuestionItem.objects.create(
        urn="urn:ddi:fr.cdsp:elipss.2013.qi_salete:1.0.0",
        name=[{"value": "qi_salete_2013"}],
        question_text=[
            {
                "lang": "fr",
                "value": (
                    "Êtes-vous confronté à un ou plusieurs des problèmes suivants "
                    "concernant votre quartier ? Saleté des rues ou du quartier"
                ),
            }
        ],
        origin="imported",
    )

    cat_je = Category.objects.create(
        urn="urn:ddi:fr.cdsp:elipss.2015.cat_refus:1.0.0",
        name=[{"value": "cat_refus_2015"}],
        label={"fr": "Je refuse de répondre"},
        origin="imported",
    )
    Category.objects.create(
        urn="urn:ddi:fr.cdsp:elipss.2013.cat_refus:1.0.0",
        name=[{"value": "cat_refus_2013"}],
        label={"fr": "Refuse de répondre"},
        origin="imported",
    )

    cat_ma = Category.objects.create(
        urn="urn:ddi:fr.cdsp:elipss.2015.cat_mere:1.0.0",
        name=[{"value": "cat_mere_2015"}],
        label={"fr": "Ma mère était déjà décédée à l'époque"},
        origin="imported",
    )
    cat_mon = Category.objects.create(
        urn="urn:ddi:fr.cdsp:elipss.2013.cat_mere:1.0.0",
        name=[{"value": "cat_mere_2013"}],
        label={"fr": "Mon mère était déjà décédée à l'époque"},
        origin="imported",
    )

    plan = plan_harmonization(threshold=0.75, output_dir=tmp_path)
    by_match = {a.match_type: a for a in plan.actions}

    assert "INCLUSIVE_WRITING_VARIANT" in by_match
    assert by_match["INCLUSIVE_WRITING_VARIANT"].action == "generate_harmonized"
    assert "PHRASING_VARIANT" in by_match
    assert by_match["PHRASING_VARIANT"].action == "generate_harmonized"
    assert "TYPOGRAPHICAL_VARIANT" in by_match
    assert by_match["TYPOGRAPHICAL_VARIANT"].action == "generate_harmonized"

    res = apply_harmonization(plan, auto_approve=True)
    assert res["generated_count"] == 3

    # Verify generated QuestionItem derived from q_inc, with wording_variant preserved
    gen_q_urn = SemanticRelationship.objects.get(
        predicate="prov:wasDerivedFrom", object_urn=q_inc.urn
    ).subject_urn
    gen_q = QuestionItem.objects.get(urn=gen_q_urn)
    assert gen_q.origin == "generated"
    q_variants = [
        a for a in (gen_q.extended_attributes or []) if a.get("type") == "wording_variant"
    ]
    assert len(q_variants) == 1

    # Verify phrasing Category preserved alternate wording
    gen_ref_urn = SemanticRelationship.objects.get(
        predicate="prov:wasDerivedFrom", object_urn=cat_je.urn
    ).subject_urn
    gen_ref = Category.objects.get(urn=gen_ref_urn)
    assert gen_ref.label == {"fr": "Je refuse de répondre"}
    ref_variants = [
        a for a in (gen_ref.extended_attributes or []) if a.get("type") == "wording_variant"
    ]
    assert len(ref_variants) == 1
    assert ref_variants[0]["value"] == "Refuse de répondre"

    # Verify typo Category dropped discarded typo
    gen_mere_urn = SemanticRelationship.objects.get(
        predicate="prov:wasDerivedFrom", object_urn=cat_ma.urn
    ).subject_urn
    gen_mere = Category.objects.get(urn=gen_mere_urn)
    assert gen_mere.label == {"fr": "Ma mère était déjà décédée à l'époque"}
    mere_variants = [
        a for a in (gen_mere.extended_attributes or []) if a.get("type") == "wording_variant"
    ]
    assert mere_variants == []

    # Undo removes generated entities cleanly while keeping imported sources intact
    undo_res = undo_harmonization(plan.job_id)
    assert undo_res["reverted_sub_jobs"] == 3
    assert QuestionItem.objects.filter(urn=gen_q_urn).exists() is False
    assert QuestionItem.objects.filter(urn=q_inc.urn).exists() is True
    assert Category.objects.filter(urn=cat_mon.urn).exists() is True


@pytest.mark.django_db
def test_represented_variable_codelist_aware_comparison_and_downgrade(tmp_path: Path) -> None:
    """Test that RepresentedVariable comparisons verify CodeList compatibility."""
    cl_5pt = CodeList.objects.create(
        urn="urn:ddi:fr.cdsp:cl_scale_5pt:1.0.0",
        name=[{"value": "cl_scale_5pt"}],
        origin="imported",
    )
    cl_10pt = CodeList.objects.create(
        urn="urn:ddi:fr.cdsp:cl_scale_10pt:1.0.0",
        name=[{"value": "cl_scale_10pt"}],
        origin="imported",
    )
    cl_5pt_dup = CodeList.objects.create(
        urn="urn:ddi:fr.cdsp:cl_scale_5pt_dup:1.0.0",
        name=[{"value": "cl_scale_5pt_dup"}],
        origin="imported",
    )

    cat_yes = Category.objects.create(
        urn="urn:ddi:fr.cdsp:cat_yes_test:1.0.0",
        name=[{"value": "yes"}],
        label={"fr": "Oui"},
        origin="imported",
    )
    cat_no = Category.objects.create(
        urn="urn:ddi:fr.cdsp:cat_no_test:1.0.0",
        name=[{"value": "no"}],
        label={"fr": "Non"},
        origin="imported",
    )

    CodeItem.objects.create(code_list=cl_5pt, code_value="1", category=cat_yes, order=1)
    CodeItem.objects.create(code_list=cl_5pt, code_value="2", category=cat_no, order=2)
    CodeItem.objects.create(code_list=cl_5pt_dup, code_value="1", category=cat_yes, order=1)
    CodeItem.objects.create(code_list=cl_5pt_dup, code_value="2", category=cat_no, order=2)
    CodeItem.objects.create(code_list=cl_10pt, code_value="10", category=cat_yes, order=1)

    rv_a = RepresentedVariable.objects.create(
        urn="urn:ddi:fr.cdsp:elipss.2014.rv_trust:1.0.0",
        name=[{"value": "rv_trust_2014"}],
        label={"fr": "Confiance dans le parlement national"},
        code_list=cl_5pt,
        origin="imported",
    )
    rv_b = RepresentedVariable.objects.create(
        urn="urn:ddi:fr.cdsp:elipss.2015.rv_trust:1.0.0",
        name=[{"value": "rv_trust_2015"}],
        label={"fr": "Confiance dans le parlement national"},
        code_list=cl_10pt,
        origin="imported",
    )
    rv_c = RepresentedVariable.objects.create(
        urn="urn:ddi:fr.cdsp:elipss.2016.rv_trust:1.0.0",
        name=[{"value": "rv_trust_2016"}],
        label={"fr": "Confiance dans le parlement national"},
        code_list=cl_5pt_dup,
        origin="imported",
    )

    cands = discover_candidates(resource_type="RepresentedVariable", threshold=0.75)
    cand_ab = next(c for c in cands if {c["source_urn"], c["target_urn"]} == {rv_a.urn, rv_b.urn})
    cand_ac = next(c for c in cands if {c["source_urn"], c["target_urn"]} == {rv_a.urn, rv_c.urn})

    assert cand_ab["match_type"] in (
        MatchType.SAME_CONCEPT_DIVERGENT_DOMAIN,
        MatchType.SAME_CONCEPT_DIFFERENT_SCALE,
        "SAME_CONCEPT_DIVERGENT_DOMAIN",
        "SAME_CONCEPT_DIFFERENT_SCALE",
    )
    assert cand_ab["recommended_action"] == "link_semantic"
    assert cand_ab["requires_review"] is True

    assert cand_ac["match_type"] == "FACET_EXACT"
    assert cand_ac["recommended_action"] == "generate_harmonized"
    assert cand_ac["details"]["codelist_status"] == "identical_code_items"

    plan = plan_harmonization(resource_type="RepresentedVariable", output_dir=tmp_path)
    md = plan.to_markdown()
    assert "Divergent Response Scale Candidates" in md
    assert "cl_scale_10pt" in md
