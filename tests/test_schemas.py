"""Tests for Pydantic v2 schemas and MultilingualText array-of-objects."""

import pytest
from pydantic import ValidationError

from fairwddi.schemas import (
    CategorySchema,
    CategorySchemeSchema,
    CodeListSchema,
    CodeSchema,
    CollectionSchema,
    ConceptSchema,
    ConceptualVariableSchema,
    DistributorSchema,
    EventLogSchema,
    InstanceVariableSchema,
    InstrumentQuestionSchema,
    InstrumentSchema,
    MultilingualItem,
    MultilingualText,
    QuestionGroupSchema,
    QuestionItemSchema,
    QuestionVariableSchema,
    RepresentedVariableSchema,
    StagedImportSchema,
    StagedResourceNodeSchema,
    StudyUnitSchema,
    StudyUnitVariableSchema,
    SubcollectionSchema,
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
    """Test validation of entity schemas with canonical URNs and MultilingualText."""
    dist_schema = DistributorSchema(name="Centre de Données Socio-Politiques (CDSP)")
    assert dist_schema.name == "Centre de Données Socio-Politiques (CDSP)"

    coll_schema = CollectionSchema(
        urn="urn:ddi:fr.sciencespo:BPF:1.0.0",
        distributor_id=1,
        name="Baromètre Politique Français",
        hashes={"sha256": "coll_hash"},
    )
    assert coll_schema.urn == "urn:ddi:fr.sciencespo:BPF:1.0.0"
    assert coll_schema.agency == "fr.sciencespo"
    assert coll_schema.identifier == "BPF"
    assert coll_schema.hashes["sha256"] == "coll_hash"

    subcoll_schema = SubcollectionSchema(
        urn="urn:ddi:fr.sciencespo:BPF_2007:1.0.0",
        collection_urn="urn:ddi:fr.sciencespo:BPF:1.0.0",
        name="BPF 2007",
    )
    assert subcoll_schema.collection_urn == "urn:ddi:fr.sciencespo:BPF:1.0.0"

    q_schema = QuestionItemSchema(
        urn="urn:ddi:fr.sciencespo:qi-fr-001:1.0.0",
        question_text=MultilingualText.from_dict({"fr": "Êtes-vous intéressé par la politique ?"}),
        hashes={"sha256": "abc1234", "v2_unordered": "xyz9876"},
        extended_attributes=[{"type": "scope", "value": "core"}],
    )
    assert q_schema.urn == "urn:ddi:fr.sciencespo:qi-fr-001:1.0.0"
    assert q_schema.agency == "fr.sciencespo"
    assert q_schema.question_text.get("fr") == "Êtes-vous intéressé par la politique ?"
    assert q_schema.hashes["v2_unordered"] == "xyz9876"
    assert q_schema.extended_attributes[0]["value"] == "core"

    qg_schema = QuestionGroupSchema(
        urn="urn:ddi:fr.sciencespo:qg-pol:1.0.0",
        label=MultilingualText.from_single("Module Politique", lang="fr"),
    )
    assert qg_schema.urn == "urn:ddi:fr.sciencespo:qg-pol:1.0.0"

    cat_schema = CategorySchema(
        urn="urn:ddi:fr.sciencespo:cat-accord:1.0.0",
        label=MultilingualText.from_single("D'accord", lang="fr"),
        parent_urn="urn:ddi:fr.sciencespo:cat-parent:1.0.0",
    )
    assert cat_schema.label.get("fr") == "D'accord"
    assert cat_schema.parent_urn == "urn:ddi:fr.sciencespo:cat-parent:1.0.0"

    cs_schema = CategorySchemeSchema(
        urn="urn:ddi:fr.sciencespo:cs-interest:1.0.0",
        name=MultilingualText.from_single("Échelle d'intérêt", lang="fr"),
    )
    assert cs_schema.name.get("fr") == "Échelle d'intérêt"

    cl_schema = CodeListSchema(
        urn="urn:ddi:fr.sciencespo:cl-interest:1.0.0",
        category_scheme_urn="urn:ddi:fr.sciencespo:cs-interest:1.0.0",
    )
    assert cl_schema.category_scheme_urn == "urn:ddi:fr.sciencespo:cs-interest:1.0.0"

    code_schema = CodeSchema(
        code_list_urn="urn:ddi:fr.sciencespo:cl-interest:1.0.0",
        category_urn="urn:ddi:fr.sciencespo:cat-accord:1.0.0",
        code_value="1",
        parent_id=10,
    )
    assert code_schema.code_value == "1"
    assert code_schema.parent_id == 10

    concept_schema = ConceptSchema(
        uri="https://elsst.cessda.eu/id/4/Politics",
        vocabulary="ELSST",
        notation="POL",
        label=MultilingualText.from_single("Politique", lang="fr"),
    )
    assert concept_schema.uri == "https://elsst.cessda.eu/id/4/Politics"
    assert concept_schema.vocabulary == "ELSST"
    assert concept_schema.label.get("fr") == "Politique"

    cv_schema = ConceptualVariableSchema(
        urn="urn:ddi:fr.sciencespo:cv-interest:1.0.0",
        label=MultilingualText.from_single("Concept", lang="fr"),
    )
    assert cv_schema.label.get("fr") == "Concept"

    rv_schema = RepresentedVariableSchema(
        urn="urn:ddi:fr.sciencespo:rv-interest:1.0.0",
        conceptual_variable_urn="urn:ddi:fr.sciencespo:cv-interest:1.0.0",
    )
    assert rv_schema.conceptual_variable_urn == "urn:ddi:fr.sciencespo:cv-interest:1.0.0"

    qv_schema = QuestionVariableSchema(
        question_item_urn="urn:ddi:fr.sciencespo:qi-fr-001:1.0.0",
        represented_variable_urn="urn:ddi:fr.sciencespo:rv-interest:1.0.0",
        path="/RepresentedVariable/QuestionItem[1]",
    )
    assert qv_schema.path == "/RepresentedVariable/QuestionItem[1]"

    inst_schema = InstrumentSchema(
        urn="urn:ddi:fr.sciencespo:inst-001:1.0.0",
        label=MultilingualText.from_single("Questionnaire 2007", lang="fr"),
    )
    assert inst_schema.urn == "urn:ddi:fr.sciencespo:inst-001:1.0.0"

    iq_schema = InstrumentQuestionSchema(
        instrument_urn="urn:ddi:fr.sciencespo:inst-001:1.0.0",
        question_item_urn="urn:ddi:fr.sciencespo:qi-fr-001:1.0.0",
        path="/Instrument/Sequence/Q1",
    )
    assert iq_schema.path == "/Instrument/Sequence/Q1"

    su_schema = StudyUnitSchema(
        urn="urn:ddi:fr.sciencespo:su-2007:1.0.0",
        subcollection_urn="urn:ddi:fr.sciencespo:BPF_2007:1.0.0",
        title=MultilingualText.from_single("Study 2007", lang="fr"),
    )
    assert su_schema.title.get("fr") == "Study 2007"

    iv_schema = InstanceVariableSchema(
        urn="urn:ddi:fr.sciencespo:iv-q01a:1.0.0",
        represented_variable_urn="urn:ddi:fr.sciencespo:rv-interest:1.0.0",
        name="q01a",
        label=MultilingualText.from_single("Intérêt politique Q1", lang="fr"),
    )
    assert iv_schema.name == "q01a"

    suv_schema = StudyUnitVariableSchema(
        study_unit_urn="urn:ddi:fr.sciencespo:su-2007:1.0.0",
        instance_variable_urn="urn:ddi:fr.sciencespo:iv-q01a:1.0.0",
        path="/StudyUnit/DataPipeline/q01a",
    )
    assert suv_schema.study_unit_urn == "urn:ddi:fr.sciencespo:su-2007:1.0.0"
    assert suv_schema.path == "/StudyUnit/DataPipeline/q01a"

    event_schema = EventLogSchema(
        urn="urn:ddi:fr.sciencespo:iv-q01a:1.0.0",
        event_type="indexed",
        event_data={"cluster": "node-1"},
    )
    assert event_schema.event_type == "indexed"
    assert event_schema.event_data["cluster"] == "node-1"

    import_schema = StagedImportSchema(
        source_format="ddi_l_3.3",
        file_name="sample.xml",
        import_options={"agency": "fr.sciencespo"},
        total_resources=5,
    )
    assert import_schema.source_format == "ddi_l_3.3"
    assert import_schema.import_options["agency"] == "fr.sciencespo"
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


def test_schema_urn_helpers() -> None:
    """Test schema URN properties on agency-scoped, maintainable-scoped, and raw URNs."""
    # Agency scoped
    s1 = QuestionItemSchema(
        urn="urn:ddi:us.mpc:V321:2",
        question_text=MultilingualText.from_single("Q text", lang="en"),
    )
    assert s1.is_canonical_ddi is True
    assert s1.is_maintainable_scoped is False
    assert s1.agency == "us.mpc"
    assert s1.identifier == "V321"
    assert s1.maintainable_id == "V321"
    assert s1.object_id == "V321"
    assert s1.version == "2"

    # Maintainable scoped
    s2 = QuestionItemSchema(
        urn="urn:ddi:us.mpc.ipums:Instrument01.Q1:1.0.0",
        question_text=MultilingualText.from_single("Q text", lang="en"),
    )
    assert s2.is_canonical_ddi is True
    assert s2.is_maintainable_scoped is True
    assert s2.agency == "us.mpc.ipums"
    assert s2.identifier == "Instrument01.Q1"
    assert s2.maintainable_id == "Instrument01"
    assert s2.object_id == "Q1"
    assert s2.version == "1.0.0"

    # Non-canonical raw URN
    s3 = QuestionItemSchema(
        urn="doi:10.7303/item99",
        question_text=MultilingualText.from_single("Q text", lang="en"),
    )
    assert s3.is_canonical_ddi is False
    assert s3.is_maintainable_scoped is False
    assert s3.agency == "fr.sciencespo"  # default
    assert s3.identifier == "doi:10.7303/item99"
    assert s3.maintainable_id is None
    assert s3.object_id == "doi:10.7303/item99"
    assert s3.version == "1.0.0"
