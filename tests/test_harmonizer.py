"""Tests for Harmonization & Resource Elevation helpers."""

from __future__ import annotations

from pathlib import Path

import pytest
from dartfx.ddi.harmonizer import MatchType

from fairwddi.ingest.comparator import discover_candidates
from fairwddi.ingest.harmonizer import (
    absorb_resource,
    apply_harmonization,
    elevate_resource,
    migrate_urn,
    plan_harmonization,
    undo_harmonization,
)
from fairwddi.models import (
    Category,
    CodeItem,
    CodeList,
    ConceptualVariable,
    Group,
    Instrument,
    InstrumentQuestion,
    QuestionItem,
    QuestionVariable,
    RepresentedVariable,
    SemanticRelationship,
    URNAlias,
    UrnRegistry,
)
from fairwddi.utils.urn import generate_generic_urn, slugify, validate_ddi_urn


def test_urn_validation_and_slug_generation() -> None:
    """Test canonical DDI URN syntax validation and slug generation."""
    # Valid canonical URNs
    assert validate_ddi_urn("urn:ddi:fr.cdsp:QI-trust-national-assembly-4f2a:1.0.0") is True
    assert validate_ddi_urn("urn:ddi:fr.cdsp:qi_V124_q1:3.0.0") is True
    assert validate_ddi_urn("urn:ddi:cessda.nesstar:study-01:1.0") is True

    # Invalid URNs
    assert validate_ddi_urn("not-a-urn") is False
    assert validate_ddi_urn("urn:ddi:fr.cdsp:too:many:colons:here:1.0.0") is False
    assert validate_ddi_urn("urn:ddi:fr.cdsp::1.0.0") is False
    assert validate_ddi_urn("urn:ddi:fr.cdsp:test-id:") is False

    # Slug generation
    assert slugify("Trust in National Assembly") == "trust-in-national-assembly"
    assert slugify("Confiance à l'Assemblée nationale !") == "confiance-a-lassemblee-nationale"
    assert slugify(None) == "generic"
    assert slugify("") == "generic"

    # Generic URN generation
    gen_urn = generate_generic_urn("QuestionItem", "Trust in National Assembly", agency="fr.cdsp")
    assert gen_urn.startswith("urn:ddi:fr.cdsp:QI-trust-in-national-assembly-")
    assert gen_urn.endswith(":1.0.0")
    assert validate_ddi_urn(gen_urn) is True


@pytest.mark.django_db
def test_elevate_question_items_into_generic_resource() -> None:
    """Test merging and elevating two study-specific QuestionItems into a generic QuestionItem."""
    # 1. Setup two study-specific QuestionItems
    qi1 = QuestionItem.objects.create(
        urn="urn:ddi:fr.cdsp:elipss.2015.q01:1.0.0",
        name=[{"value": "q01_2015"}],
        label=[{"lang": "fr", "value": "Confiance Assemblée (2015)"}],
        question_text=[{"lang": "fr", "value": "Faites-vous confiance à l'Assemblée ?"}],
    )
    qi2 = QuestionItem.objects.create(
        urn="urn:ddi:fr.cdsp:elipss.2016.q01:1.0.0",
        name=[{"value": "q01_2016"}],
        label=[{"lang": "en", "value": "Trust National Assembly (2016)"}],
        question_text=[{"lang": "en", "value": "Do you trust the National Assembly?"}],
    )

    # Setup a RepresentedVariable linked to qi1
    rv = RepresentedVariable.objects.create(
        urn="urn:ddi:fr.cdsp:rv_trust:1.0.0",
        name=[{"value": "rv_trust"}],
    )
    qv = QuestionVariable.objects.create(
        question_item=qi1,
        represented_variable=rv,
    )

    generic_urn = "urn:ddi:fr.cdsp:QI-trust-national-assembly:1.0.0"

    # 2. Elevate into generic QuestionItem (omitting resource_type to test auto-inference)
    res = elevate_resource(
        source_urns=[qi1.urn, qi2.urn],
        generic_urn=generic_urn,
        generic_name="Trust in National Assembly (Harmonized)",
        update_references=True,
        retire_sources=True,
    )

    assert res["generic_urn"] == generic_urn
    assert res["resource_type"] == "QuestionItem"
    assert res["aliases_created"] == 2
    assert res["semantic_links_created"] == 2
    assert res["updated_references"]["QuestionVariable"] == 1

    # Verify newly created generic QuestionItem
    gen_qi = QuestionItem.objects.get(urn=generic_urn)
    assert gen_qi.name == [{"value": "Trust in National Assembly (Harmonized)"}]
    # Multilingual fusion check: both fr and en must be present
    assert gen_qi.question_text == [
        {"lang": "en", "value": "Do you trust the National Assembly?"},
        {"lang": "fr", "value": "Faites-vous confiance à l'Assemblée ?"},
    ]
    assert gen_qi.label == [
        {"lang": "en", "value": "Trust National Assembly (2016)"},
        {"lang": "fr", "value": "Confiance Assemblée (2015)"},
    ]

    # Verify UrnRegistry statuses & elevation JSONB metadata
    reg_gen = UrnRegistry.objects.get(urn=generic_urn)
    assert reg_gen.status == "elevated"
    assert reg_gen.resource_type == "QuestionItem"
    assert isinstance(reg_gen.extended_attributes, list)
    assert reg_gen.extended_attributes[0]["type"] == "elevation"
    assert reg_gen.extended_attributes[0]["is_elevated"] is True

    reg_src1 = UrnRegistry.objects.get(urn=qi1.urn)
    assert reg_src1.status == "superseded"
    reg_src2 = UrnRegistry.objects.get(urn=qi2.urn)
    assert reg_src2.status == "superseded"

    # Verify URNAlias links
    alias1 = URNAlias.objects.get(alias_urn=qi1.urn)
    assert alias1.canonical_urn == generic_urn
    alias2 = URNAlias.objects.get(alias_urn=qi2.urn)
    assert alias2.canonical_urn == generic_urn

    # Verify SemanticRelationship
    assert SemanticRelationship.objects.filter(
        subject_urn=qi1.urn, object_urn=generic_urn, predicate="skos:exactMatch"
    ).exists()

    # Verify QuestionVariable was updated to point to generic_urn
    qv.refresh_from_db()
    assert qv.question_item_id == generic_urn

    # Verify source rows retired from QuestionItem table
    assert QuestionItem.objects.filter(urn=qi1.urn).exists() is False
    assert QuestionItem.objects.filter(urn=qi2.urn).exists() is False

    # 3. Test Undo / Rollback
    undo_res = undo_harmonization(res["job_id"])
    assert undo_res["status"] == "reverted"
    assert undo_res["restored_sources"] == 2
    assert undo_res["removed_generic_urn"] == generic_urn

    # Sources restored in database
    assert QuestionItem.objects.filter(urn=qi1.urn).exists() is True
    assert QuestionItem.objects.filter(urn=qi2.urn).exists() is True
    assert QuestionItem.objects.filter(urn=generic_urn).exists() is False

    # Reference restored back to primary source
    qv.refresh_from_db()
    assert qv.question_item_id == qi1.urn

    # Registry status restored
    assert UrnRegistry.objects.get(urn=qi1.urn).status == "active"
    assert UrnRegistry.objects.get(urn=qi2.urn).status == "active"


@pytest.mark.django_db
def test_elevate_conceptual_variables_and_update_cascade() -> None:
    """Test elevating ConceptualVariables with auto-slug generation and cascade updates."""
    cv1 = ConceptualVariable.objects.create(
        urn="urn:ddi:fr.cdsp:cv_trust_w1:1.0.0",
        name=[{"value": "cv_trust_w1"}],
        label=[{"lang": "fr", "value": "Confiance politique (W1)"}],
        description=[{"lang": "fr", "value": "Mesure de la confiance politique"}],
    )
    cv2 = ConceptualVariable.objects.create(
        urn="urn:ddi:fr.cdsp:cv_trust_w2:1.0.0",
        name=[{"value": "cv_trust_w2"}],
        label=[{"lang": "en", "value": "Political Trust (W2)"}],
    )

    # Linked RepresentedVariable
    rv = RepresentedVariable.objects.create(
        urn="urn:ddi:fr.cdsp:rv_test_cascade:1.0.0",
        name=[{"value": "rv_test_cascade"}],
        conceptual_variable=cv1,
    )

    # Elevate without explicit target URN -> auto-slug generation
    res = elevate_resource(
        source_urns=[cv1.urn, cv2.urn],
        generic_urn=None,
        resource_type="ConceptualVariable",
        generic_name="Political Trust Concept",
        update_references=True,
    )

    gen_urn = res["generic_urn"]
    assert gen_urn.startswith("urn:ddi:fr.cdsp:CV-political-trust-concept-")
    assert validate_ddi_urn(gen_urn) is True

    # Check RepresentedVariable was updated across the cascade
    rv.refresh_from_db()
    assert rv.conceptual_variable_id == gen_urn

    # Check URNAlias
    assert URNAlias.objects.filter(alias_urn=cv1.urn, canonical_urn=gen_urn).exists()
    assert URNAlias.objects.filter(alias_urn=cv2.urn, canonical_urn=gen_urn).exists()


@pytest.mark.django_db
def test_migrate_urn_single_resource() -> None:
    """Test single-resource URN renaming/promotion with migrate_urn."""
    qi = QuestionItem.objects.create(
        urn="urn:ddi:fr.cdsp:qi_legacy_rename:1.0.0",
        name=[{"value": "qi_legacy_rename"}],
        question_text=[{"lang": "fr", "value": "Texte question"}],
    )
    new_urn = "urn:ddi:fr.cdsp:QI-promoted-canonical:1.0.0"

    res = migrate_urn(old_urn=qi.urn, new_urn=new_urn, resource_type="QuestionItem")

    assert res["generic_urn"] == new_urn
    assert QuestionItem.objects.filter(urn=new_urn).exists() is True
    assert QuestionItem.objects.filter(urn=qi.urn).exists() is False
    assert URNAlias.objects.filter(alias_urn=qi.urn, canonical_urn=new_urn).exists()
    assert UrnRegistry.objects.get(urn=new_urn).status == "elevated"
    assert UrnRegistry.objects.get(urn=qi.urn).status == "superseded"


@pytest.mark.django_db
def test_elevate_mismatched_types_raises_error() -> None:
    """Test that elevating sources of different resource types raises an error."""
    qi = QuestionItem.objects.create(
        urn="urn:ddi:fr.cdsp:qi_mismatch:1.0.0",
        name=[{"value": "qi_mismatch"}],
    )
    cv = ConceptualVariable.objects.create(
        urn="urn:ddi:fr.cdsp:cv_mismatch:1.0.0",
        name=[{"value": "cv_mismatch"}],
    )

    with pytest.raises(ValueError, match="mismatched resource types"):
        elevate_resource(source_urns=[qi.urn, cv.urn])


@pytest.mark.django_db
def test_absorb_resource_into_existing_harmonized_resource() -> None:
    """Test absorbing a newly discovered study question into an existing elevated resource."""
    # 1. Existing elevated generic QuestionItem (previously elevated with fr text)
    generic_urn = "urn:ddi:fr.cdsp:QI-trust-institutions:1.0.0"
    gen_qi = QuestionItem.objects.create(
        urn=generic_urn,
        name=[{"value": "Trust Institutions Harmonized"}],
        label=[{"lang": "fr", "value": "Confiance institutions"}],
        question_text=[{"lang": "fr", "value": "Avez-vous confiance dans les institutions ?"}],
    )
    UrnRegistry.objects.filter(urn=generic_urn).update(
        status="elevated",
        extended_attributes=[{"type": "elevation", "is_elevated": True}],
    )

    # 2. Third wave study-specific question with new Spanish translation & interviewer instructions
    qi_wave3 = QuestionItem.objects.create(
        urn="urn:ddi:fr.cdsp:elipss.2017.q01:1.0.0",
        name=[{"value": "q01_2017"}],
        label=[{"lang": "es", "value": "Confianza en las instituciones"}],
        question_text=[{"lang": "es", "value": "¿Confía en las instituciones?"}],
        interviewer_instructions=[{"lang": "es", "value": "Leer pausadamente"}],
    )

    # Linked QuestionVariable and InstrumentQuestion for qi_wave3
    rv = RepresentedVariable.objects.create(
        urn="urn:ddi:fr.cdsp:rv_trust_w3:1.0.0",
        name=[{"value": "rv_trust_w3"}],
    )
    qv = QuestionVariable.objects.create(
        question_item=qi_wave3,
        represented_variable=rv,
    )
    inst = Instrument.objects.create(
        urn="urn:ddi:fr.cdsp:inst_2017:1.0.0",
        name=[{"value": "Questionnaire 2017"}],
    )
    iq = InstrumentQuestion.objects.create(
        instrument=inst,
        question_item=qi_wave3,
    )

    # 3. Perform absorption
    res = absorb_resource(
        source_urns=[qi_wave3.urn],
        into_urn=generic_urn,
        update_references=True,
        retire_sources=True,
        provenance_note="Wave 3 longitudinal absorption",
    )

    assert res["is_absorption"] is True
    assert res["target_urn"] == generic_urn
    assert res["generic_urn"] == generic_urn
    assert res["aliases_created"] == 1
    assert res["semantic_links_created"] == 1
    assert res["updated_references"]["QuestionVariable"] == 1
    assert res["updated_references"]["InstrumentQuestion"] == 1

    # Check target QuestionItem received fused Spanish translation & instructions
    gen_qi.refresh_from_db()
    assert gen_qi.question_text == [
        {"lang": "es", "value": "¿Confía en las instituciones?"},
        {"lang": "fr", "value": "Avez-vous confiance dans les institutions ?"},
    ]
    assert gen_qi.interviewer_instructions == [
        {"lang": "es", "value": "Leer pausadamente"},
    ]
    assert gen_qi.label == [
        {"lang": "es", "value": "Confianza en las instituciones"},
        {"lang": "fr", "value": "Confiance institutions"},
    ]
    ext_types = [attr.get("type") for attr in (gen_qi.extended_attributes or [])]
    assert "absorption" in ext_types

    # Check registry statuses
    assert UrnRegistry.objects.get(urn=qi_wave3.urn).status == "superseded"
    assert UrnRegistry.objects.get(urn=generic_urn).status == "elevated"

    # Check URNAlias
    alias = URNAlias.objects.get(alias_urn=qi_wave3.urn)
    assert alias.canonical_urn == generic_urn
    assert alias.hash_strategy == "harmonization_absorption"

    # Check repointed references
    qv.refresh_from_db()
    assert qv.question_item_id == generic_urn
    iq.refresh_from_db()
    assert iq.question_item_id == generic_urn

    # Check source row retired from entity table
    assert QuestionItem.objects.filter(urn=qi_wave3.urn).exists() is False

    # 4. Test Undo / Rollback
    undo_res = undo_harmonization(res["job_id"])
    assert undo_res["status"] == "reverted"
    assert undo_res["is_absorption"] is True
    assert undo_res["target_urn"] == generic_urn
    assert undo_res["restored_sources"] == 1

    # Generic object was NOT deleted!
    assert QuestionItem.objects.filter(urn=generic_urn).exists() is True
    gen_qi.refresh_from_db()
    # Spanish text was cleanly stripped back to original French only
    assert gen_qi.question_text == [
        {"lang": "fr", "value": "Avez-vous confiance dans les institutions ?"},
    ]
    assert gen_qi.interviewer_instructions is None
    assert gen_qi.label == [
        {"lang": "fr", "value": "Confiance institutions"},
    ]

    # Source was restored
    assert QuestionItem.objects.filter(urn=qi_wave3.urn).exists() is True
    restored_qi = QuestionItem.objects.get(urn=qi_wave3.urn)
    assert restored_qi.question_text == [{"lang": "es", "value": "¿Confía en las instituciones?"}]
    assert UrnRegistry.objects.get(urn=qi_wave3.urn).status == "active"

    # References repointed back to source
    qv.refresh_from_db()
    assert qv.question_item_id == qi_wave3.urn
    iq.refresh_from_db()
    assert iq.question_item_id == qi_wave3.urn

    # Alias deleted
    assert URNAlias.objects.filter(alias_urn=qi_wave3.urn).exists() is False


@pytest.mark.django_db
def test_absorb_and_elevate_error_handling() -> None:
    """Test error conditions for elevate and absorb."""
    qi = QuestionItem.objects.create(
        urn="urn:ddi:fr.cdsp:qi_err_test:1.0.0",
        name=[{"value": "qi_err_test"}],
    )
    existing_gen = QuestionItem.objects.create(
        urn="urn:ddi:fr.cdsp:QI-already-existing:1.0.0",
        name=[{"value": "QI-already-existing"}],
    )

    # 1. Elevating into an already existing generic URN raises ValueError recommending absorb
    with pytest.raises(ValueError, match="already exists in UrnRegistry. Use 'absorb"):
        elevate_resource(
            source_urns=[qi.urn],
            generic_urn=existing_gen.urn,
        )

    # 2. Absorbing into a non-existent URN raises ValueError
    with pytest.raises(ValueError, match="does not exist in UrnRegistry. Cannot absorb"):
        absorb_resource(
            source_urns=[qi.urn],
            into_urn="urn:ddi:fr.cdsp:QI-non-existent:1.0.0",
        )

    # 3. Source URN identical to into URN
    with pytest.raises(ValueError, match="distinct from target URN"):
        absorb_resource(
            source_urns=[qi.urn],
            into_urn=qi.urn,
        )


@pytest.mark.django_db
def test_near_exact_punctuation_and_target_aware_absorb_in_plan(tmp_path: Path) -> None:
    """Test NEAR_EXACT punctuation variant detection and target-aware absorb in plan."""
    # 1. Category pair differing only by trailing ' ?' (like cmp-0783)
    cat_2015 = Category.objects.create(
        urn="urn:ddi:fr.cdsp:elipss.2015.cat_ouvrier:3.0.0",
        name=[{"value": "cat_2_Ouvrier"}],
        label={"fr": "Ouvrier(e) qualifié(e) ou hautement qualifié(e), technicien(ne) d'atelier"},
    )
    cat_2013 = Category.objects.create(
        urn="urn:ddi:fr.cdsp:elipss.2013.cat_ouvrier:3.0.0",
        name=[{"value": "cat_2_Ouvrier_q"}],
        label={"fr": "Ouvrier(e) qualifié(e) ou hautement qualifié(e), technicien(ne) d'atelier ?"},
    )
    # Mark cat_2015 as already elevated to test target-aware 'absorb' recommendation
    UrnRegistry.objects.filter(urn=cat_2015.urn).update(
        status="elevated",
        extended_attributes=[{"type": "elevation", "is_elevated": True}],
    )

    cands = discover_candidates(resource_type="Category", threshold=0.75)
    assert len(cands) == 1
    cand = cands[0]
    assert cand["match_type"] == "NEAR_EXACT"
    assert cand["confidence"] == 0.98
    assert cand["requires_review"] is True
    assert cand["details"]["punctuation_variant"] is True
    # Because cat_2015 is elevated, source is oriented to cat_2013 and action is 'absorb'
    assert cand["source_urn"] == cat_2013.urn
    assert cand["target_urn"] == cat_2015.urn
    assert cand["recommended_action"] == "absorb"

    # Plan and apply declarative absorption
    plan = plan_harmonization(resource_type="Category", output_dir=tmp_path)
    assert plan.pending_review_count == 1
    assert plan.is_ready_to_execute(auto_approve=False) is False

    res = apply_harmonization(plan, auto_approve=True)
    assert res["absorbed_count"] == 1

    # Verify cat_2013 was absorbed into cat_2015 without keeping the stray '?' variant
    cat_2015.refresh_from_db()
    assert cat_2015.label == {
        "fr": "Ouvrier(e) qualifié(e) ou hautement qualifié(e), technicien(ne) d'atelier"
    }
    wording_vars = [
        a for a in (cat_2015.extended_attributes or []) if a.get("type") == "wording_variant"
    ]
    assert wording_vars == []
    assert URNAlias.objects.filter(alias_urn=cat_2013.urn, canonical_urn=cat_2015.urn).exists()

    # Undo plan restores cat_2013
    undo_res = undo_harmonization(plan.job_id)
    assert undo_res["status"] == "reverted"
    assert undo_res["reverted_sub_jobs"] == 1
    assert Category.objects.filter(urn=cat_2013.urn).exists() is True


@pytest.mark.django_db
def test_shared_stem_question_grid_detection_and_generic_group(tmp_path: Path) -> None:
    """Test SHARED_STEM_GRID detection and generic Group creation (group_type='question_grid')."""
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
    )

    # Link related RepresentedVariables with distinct CodeLists
    cl1 = CodeList.objects.create(urn="urn:ddi:fr.cdsp:cl_yesno:1.0.0", name="cl_yesno")
    cl2 = CodeList.objects.create(urn="urn:ddi:fr.cdsp:cl_scale:1.0.0", name="cl_scale")
    rv_green = RepresentedVariable.objects.create(
        urn="urn:ddi:fr.cdsp:rv_quartier_verts:1.0.0",
        name="rv_quartier_verts",
        code_list=cl1,
    )
    rv_sec = RepresentedVariable.objects.create(
        urn="urn:ddi:fr.cdsp:rv_quartier_sec:1.0.0",
        name="rv_quartier_sec",
        code_list=cl2,
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
    assert cand["details"]["group_type"] == "question_grid"
    expected_stem = (
        "Êtes-vous confronté(e) à un ou plusieurs des problèmes suivants "
        "concernant votre quartier ?"
    )
    assert cand["details"]["shared_stem"] == expected_stem
    assert {cand["details"]["sub_item_a"], cand["details"]["sub_item_b"]} == {
        "Manque d'espaces verts",
        "Manque de sécurité",
    }

    plan = plan_harmonization(resource_type="QuestionItem", output_dir=tmp_path)
    assert plan.pending_review_count == 1
    md = plan.to_markdown()
    assert "Shared-Stem Grids & Resource Groups" in md

    res = apply_harmonization(plan, auto_approve=True)
    assert res["grouped_count"] == 1

    groups = list(Group.objects.filter(group_type="question_grid"))
    assert len(groups) == 1
    grp = groups[0]
    ref_urns = {r["urn"] for r in (grp.references or [])}
    assert q_green.urn in ref_urns
    assert q_sec.urn in ref_urns
    assert rv_green.urn in ref_urns
    assert rv_sec.urn in ref_urns
    assert SemanticRelationship.objects.filter(
        subject_urn=q_green.urn, predicate="ddi:inGroup", object_urn=grp.urn
    ).exists()

    # Undo removes the created Group and SemanticRelationships
    undo_res = undo_harmonization(plan.job_id)
    assert undo_res["removed_groups"] == 1
    assert Group.objects.filter(urn=grp.urn).exists() is False


@pytest.mark.django_db
def test_phrasing_inclusive_and_typo_variants_in_plan(tmp_path: Path) -> None:
    """Test inclusive writing, stylistic phrasing, and grammatical error handling in plans."""
    # 1. Inclusive writing variant on QuestionItem
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
    )

    # 2. Stylistic phrasing variant on Category ("Je refuse de répondre" vs "Refuse de répondre")
    cat_je = Category.objects.create(
        urn="urn:ddi:fr.cdsp:elipss.2015.cat_refus:1.0.0",
        name=[{"value": "cat_refus_2015"}],
        label={"fr": "Je refuse de répondre"},
    )
    Category.objects.create(
        urn="urn:ddi:fr.cdsp:elipss.2013.cat_refus:1.0.0",
        name=[{"value": "cat_refus_2013"}],
        label={"fr": "Refuse de répondre"},
    )

    # 3. Grammatical error on Category ("Ma mère..." vs "Mon mère...")
    cat_ma = Category.objects.create(
        urn="urn:ddi:fr.cdsp:elipss.2015.cat_mere:1.0.0",
        name=[{"value": "cat_mere_2015"}],
        label={"fr": "Ma mère était déjà décédée à l'époque"},
    )
    cat_mon = Category.objects.create(
        urn="urn:ddi:fr.cdsp:elipss.2013.cat_mere:1.0.0",
        name=[{"value": "cat_mere_2013"}],
        label={"fr": "Mon mère était déjà décédée à l'époque"},
    )

    plan = plan_harmonization(threshold=0.75, output_dir=tmp_path)
    by_match = {a.match_type: a for a in plan.actions}

    assert "INCLUSIVE_WRITING_VARIANT" in by_match
    inc_act = by_match["INCLUSIVE_WRITING_VARIANT"]
    assert inc_act.action == "elevate"
    assert inc_act.requires_review is True
    assert inc_act.details["canonical_text"] == {
        "fr": (
            "Êtes-vous confronté(e) à un ou plusieurs des problèmes suivants "
            "concernant votre quartier ? Saleté des rues ou du quartier"
        )
    }

    assert "PHRASING_VARIANT" in by_match
    phr_act = by_match["PHRASING_VARIANT"]
    assert phr_act.action == "elevate"
    assert phr_act.requires_review is True
    assert phr_act.details["canonical_text"] == {"fr": "Je refuse de répondre"}
    assert phr_act.details["preserved_variants"] == ["Refuse de répondre"]

    assert "TYPOGRAPHICAL_VARIANT" in by_match
    typo_act = by_match["TYPOGRAPHICAL_VARIANT"]
    assert typo_act.action == "elevate"
    assert typo_act.requires_review is True
    assert typo_act.details["canonical_text"] == {"fr": "Ma mère était déjà décédée à l'époque"}
    assert typo_act.details["discarded_variants"] == ["Mon mère était déjà décédée à l'époque"]

    # Apply the plan and verify elevated entities
    res = apply_harmonization(plan, auto_approve=True)
    assert res["elevated_count"] == 3

    # 1. Check inclusive QuestionItem
    gen_q_urn = URNAlias.objects.get(alias_urn=q_inc.urn).canonical_urn
    gen_q = QuestionItem.objects.get(urn=gen_q_urn)
    assert gen_q.question_text == [
        {
            "lang": "fr",
            "value": (
                "Êtes-vous confronté(e) à un ou plusieurs des problèmes suivants "
                "concernant votre quartier ? Saleté des rues ou du quartier"
            ),
        }
    ]
    q_variants = [
        a for a in (gen_q.extended_attributes or []) if a.get("type") == "wording_variant"
    ]
    assert len(q_variants) == 1
    assert q_variants[0]["value"] == (
        "Êtes-vous confronté à un ou plusieurs des problèmes suivants "
        "concernant votre quartier ? Saleté des rues ou du quartier"
    )

    # 2. Check stylistic Category ("Je refuse de répondre" default + "Refuse de répondre" variant)
    gen_ref_urn = URNAlias.objects.get(alias_urn=cat_je.urn).canonical_urn
    gen_ref = Category.objects.get(urn=gen_ref_urn)
    assert gen_ref.label == {"fr": "Je refuse de répondre"}
    ref_variants = [
        a for a in (gen_ref.extended_attributes or []) if a.get("type") == "wording_variant"
    ]
    assert len(ref_variants) == 1
    assert ref_variants[0]["value"] == "Refuse de répondre"

    # 3. Check grammatical typo Category ("Ma mère..." default, "Mon mère..." dropped!)
    gen_mere_urn = URNAlias.objects.get(alias_urn=cat_ma.urn).canonical_urn
    assert URNAlias.objects.get(alias_urn=cat_mon.urn).canonical_urn == gen_mere_urn
    gen_mere = Category.objects.get(urn=gen_mere_urn)
    assert gen_mere.label == {"fr": "Ma mère était déjà décédée à l'époque"}
    mere_variants = [
        a for a in (gen_mere.extended_attributes or []) if a.get("type") == "wording_variant"
    ]
    assert mere_variants == []

    # Undo plan reverts all 3 elevations cleanly
    undo_res = undo_harmonization(plan.job_id)
    assert undo_res["reverted_sub_jobs"] == 3
    assert QuestionItem.objects.filter(urn=q_inc.urn).exists() is True
    assert Category.objects.filter(urn=cat_mon.urn).exists() is True


@pytest.mark.django_db
def test_represented_variable_codelist_aware_comparison_and_downgrade(tmp_path: Path) -> None:
    """Test that RepresentedVariable comparisons verify CodeList compatibility."""
    # 1. Setup two CodeLists with distinct response scales
    cl_5pt = CodeList.objects.create(
        urn="urn:ddi:fr.cdsp:cl_scale_5pt:1.0.0",
        name=[{"value": "cl_scale_5pt"}],
    )
    cl_10pt = CodeList.objects.create(
        urn="urn:ddi:fr.cdsp:cl_scale_10pt:1.0.0",
        name=[{"value": "cl_scale_10pt"}],
    )
    cl_5pt_dup = CodeList.objects.create(
        urn="urn:ddi:fr.cdsp:cl_scale_5pt_dup:1.0.0",
        name=[{"value": "cl_scale_5pt_dup"}],
    )

    cat_yes = Category.objects.create(
        urn="urn:ddi:fr.cdsp:cat_yes_test:1.0.0",
        name=[{"value": "yes"}],
        label={"fr": "Oui"},
    )
    cat_no = Category.objects.create(
        urn="urn:ddi:fr.cdsp:cat_no_test:1.0.0",
        name=[{"value": "no"}],
        label={"fr": "Non"},
    )

    # cl_5pt and cl_5pt_dup share identical code items
    CodeItem.objects.create(code_list=cl_5pt, code_value="1", category=cat_yes, order=1)
    CodeItem.objects.create(code_list=cl_5pt, code_value="2", category=cat_no, order=2)
    CodeItem.objects.create(code_list=cl_5pt_dup, code_value="1", category=cat_yes, order=1)
    CodeItem.objects.create(code_list=cl_5pt_dup, code_value="2", category=cat_no, order=2)

    # cl_10pt has different code items
    CodeItem.objects.create(code_list=cl_10pt, code_value="10", category=cat_yes, order=1)

    # 2. Setup RepresentedVariables:
    # rv_a (5pt) vs rv_b (10pt): identical label, divergent CodeList -> SAME_CONCEPT_DIFFERENT_SCALE
    rv_a = RepresentedVariable.objects.create(
        urn="urn:ddi:fr.cdsp:elipss.2014.rv_trust:1.0.0",
        name=[{"value": "rv_trust_2014"}],
        label={"fr": "Confiance dans le parlement national"},
        code_list=cl_5pt,
    )
    rv_b = RepresentedVariable.objects.create(
        urn="urn:ddi:fr.cdsp:elipss.2015.rv_trust:1.0.0",
        name=[{"value": "rv_trust_2015"}],
        label={"fr": "Confiance dans le parlement national"},
        code_list=cl_10pt,
    )
    # rv_c (5pt_dup): identical label, compatible CodeList with rv_a -> FACET_EXACT
    rv_c = RepresentedVariable.objects.create(
        urn="urn:ddi:fr.cdsp:elipss.2016.rv_trust:1.0.0",
        name=[{"value": "rv_trust_2016"}],
        label={"fr": "Confiance dans le parlement national"},
        code_list=cl_5pt_dup,
    )

    cands = discover_candidates(resource_type="RepresentedVariable", threshold=0.75)
    # Filter candidates for (rv_a, rv_b) and (rv_a, rv_c)
    cand_ab = next(c for c in cands if {c["source_urn"], c["target_urn"]} == {rv_a.urn, rv_b.urn})
    cand_ac = next(c for c in cands if {c["source_urn"], c["target_urn"]} == {rv_a.urn, rv_c.urn})

    # rv_a vs rv_b: Divergent scale -> link_semantic
    assert cand_ab["match_type"] in (
        MatchType.SAME_CONCEPT_DIVERGENT_DOMAIN,
        MatchType.SAME_CONCEPT_DIFFERENT_SCALE,
        "SAME_CONCEPT_DIVERGENT_DOMAIN",
        "SAME_CONCEPT_DIFFERENT_SCALE",
    )
    assert cand_ab["recommended_action"] == "link_semantic"
    assert cand_ab["requires_review"] is True
    assert cand_ab["details"]["codelist_status"] == "divergent"
    assert "divergent response scales" in cand_ab["details"]["note"]

    # rv_a vs rv_c: Compatible scale -> alias
    assert cand_ac["match_type"] == "FACET_EXACT"
    assert cand_ac["recommended_action"] == "alias"
    assert cand_ac["requires_review"] is False
    assert cand_ac["details"]["codelist_status"] == "identical_code_items"

    # Plan markdown includes divergent scale section
    plan = plan_harmonization(resource_type="RepresentedVariable", output_dir=tmp_path)
    md = plan.to_markdown()
    assert "Divergent Response Scale Candidates" in md
    assert "cl_scale_10pt" in md
