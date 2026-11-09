"""Tests for Harmonization & Resource Elevation helpers."""

from __future__ import annotations

import pytest

from fairwddi.ingest.harmonizer import (
    absorb_resource,
    elevate_resource,
    migrate_urn,
    undo_harmonization,
)
from fairwddi.models import (
    ConceptualVariable,
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
