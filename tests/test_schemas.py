"""Tests for Pydantic v2 schemas and MultilingualText array-of-objects."""

import pytest
from pydantic import ValidationError

from fairwddi.schemas import (
    CategorySchema,
    ConceptSchema,
    ConceptualVariableSchema,
    DistributorSchema,
    InstanceVariableSchema,
    MultilingualItem,
    MultilingualText,
    QuestionItemSchema,
    RepresentedVariableSchema,
    StagedImportSchema,
    StagedResourceNodeSchema,
    StudyUnitSchema,
    VariableGroupSchema,
)


def test_multilingual_item_basic() -> None:
    """Test MultilingualItem with required value and optional fields."""
    item = MultilingualItem(value="Quel âge avez-vous?", lang="fr")
    assert item.value == "Quel âge avez-vous?"
    assert item.lang == "fr"
    assert item.type is None
    assert item.format is None


def test_multilingual_item_extensibility() -> None:
    """Test that MultilingualItem accepts arbitrary evolving fields (extra='allow')."""
    item = MultilingualItem(
        value="How old are you?",
        lang="en",
        type="literal",
        format="text/plain",
        translated=True,
        source_lang="fr",
        confidence=0.98,
    )
    assert item.value == "How old are you?"
    assert item.lang == "en"
    assert item.type == "literal"
    assert item.format == "text/plain"
    # Extra fields preserved via model_extra or dict access
    assert item.model_extra is not None
    assert item.model_extra["translated"] is True
    assert item.model_extra["source_lang"] == "fr"
    assert item.model_extra["confidence"] == 0.98

    # Serialization preserves extra attributes
    dumped = item.model_dump()
    assert dumped["translated"] is True
    assert dumped["source_lang"] == "fr"


def test_multilingual_item_validation_error() -> None:
    """Test that MultilingualItem requires a value string."""
    with pytest.raises(ValidationError):
        MultilingualItem.model_validate({"lang": "fr"})


def test_multilingual_text_container() -> None:
    """Test MultilingualText root container methods."""
    multi = MultilingualText(
        root=[
            MultilingualItem(lang="en", value="How old are you?"),
            MultilingualItem(lang="fr", value="Quel âge avez-vous?"),
            MultilingualItem(lang="fr", value="quel_age", type="normalized"),
        ]
    )

    assert len(multi) == 3
    assert multi.get("fr") == "Quel âge avez-vous?"
    assert multi.get("en") == "How old are you?"
    assert multi.get("es") == "How old are you?"  # fallback
    assert multi.get("es", fallback=False) is None

    # Iteration
    langs = [item.lang for item in multi]
    assert langs == ["en", "fr", "fr"]

    # to_dict helper
    d = multi.to_dict()
    assert d["en"] == "How old are you?"
    assert d["fr"] == "Quel âge avez-vous?"

    # from_dict helper
    rebuilt = MultilingualText.from_dict({"en": "Hello", "fr": "Bonjour"})
    assert len(rebuilt) == 2
    assert rebuilt.get("fr") == "Bonjour"

    # add helper
    rebuilt.add(value="Hola", lang="es", translated=True)
    assert len(rebuilt) == 3
    assert rebuilt.get("es") == "Hola"


def test_domain_entity_schemas() -> None:
    """Test validation of entity schemas with MultilingualText."""
    dist_schema = DistributorSchema(name="Centre de Données Socio-Politiques (CDSP)")
    assert dist_schema.name == "Centre de Données Socio-Politiques (CDSP)"

    q_schema = QuestionItemSchema(
        urn="urn:ddi:fr.cdsp:QuestionItem:qi-fr-001:1.0.0",
        agency="fr.cdsp",
        question_text=MultilingualText.from_dict({"fr": "Êtes-vous intéressé par la politique ?"}),
        pre_question_text=MultilingualText.from_single("Veuillez répondre honnêtement.", lang="fr"),
        content_hash="abc1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        content_hashes={"v1_strict_sha256": "abc1234", "v2_unordered_set": "xyz9876"},
    )
    assert q_schema.urn == "urn:ddi:fr.cdsp:QuestionItem:qi-fr-001:1.0.0"
    assert q_schema.question_text.get("fr") == "Êtes-vous intéressé par la politique ?"
    assert q_schema.content_hashes["v2_unordered_set"] == "xyz9876"

    cat_schema = CategorySchema(label=MultilingualText.from_single("D'accord", lang="fr"))
    assert cat_schema.label.get("fr") == "D'accord"

    concept_schema = ConceptSchema(
        uri="https://elsst.cessda.eu/id/4/Politics",
        vocabulary="ELSST",
        notation="POL",
        label=MultilingualText.from_single("Politique", lang="fr"),
    )
    assert concept_schema.uri == "https://elsst.cessda.eu/id/4/Politics"
    assert concept_schema.vocabulary == "ELSST"
    assert concept_schema.label.get("fr") == "Politique"

    cv_schema = ConceptualVariableSchema(label=MultilingualText.from_single("Concept", lang="fr"))
    assert cv_schema.label.get("fr") == "Concept"

    rv_schema = RepresentedVariableSchema(
        conceptual_variable_id=1,
        question_item_id=1,
    )
    assert rv_schema.conceptual_variable_id == 1

    su_schema = StudyUnitSchema(
        subcollection_id=1,
        title=MultilingualText.from_single("Study 2007", lang="fr"),
    )
    assert su_schema.title.get("fr") == "Study 2007"

    iv_schema = InstanceVariableSchema(
        study_unit_id=1,
        represented_variable_id=1,
        variable_name="q01a",
    )
    assert iv_schema.variable_name == "q01a"

    vg_schema = VariableGroupSchema(
        label=MultilingualText.from_single("Démographie", lang="fr"),
    )
    assert vg_schema.label.get("fr") == "Démographie"

    import_schema = StagedImportSchema(
        source_format="ddi_l_3.3",
        file_name="sample.xml",
        import_options={"agency": "fr.cdsp"},
        total_resources=5,
    )
    assert import_schema.source_format == "ddi_l_3.3"
    assert import_schema.import_options["agency"] == "fr.cdsp"
    assert import_schema.total_resources == 5

    staged_node = StagedResourceNodeSchema(
        staged_import_id=1,
        resource_type="QuestionItem",
        raw_urn="raw:qstn:001",
        raw_value={"question_text": [{"lang": "fr", "value": "Test question"}]},
    )
    assert staged_node.raw_urn == "raw:qstn:001"
    assert staged_node.staged_import_id == 1
    assert staged_node.status == "staged"
