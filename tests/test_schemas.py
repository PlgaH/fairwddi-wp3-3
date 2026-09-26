"""Tests for Pydantic v2 schemas and MultilingualText array-of-objects."""

import pytest
from pydantic import ValidationError

from fairwddi.schemas import (
    CategorySchema,
    CategorySchemeSchema,
    CodeListSchema,
    CodeSchema,
    ConceptSchema,
    ConceptSchemeSchema,
    ConceptualVariableSchema,
    ConceptualVariableSchemeSchema,
    EventLogSchema,
    GroupReferenceSchema,
    GroupSchema,
    InstanceVariableSchema,
    InstanceVariableSchemeSchema,
    InstrumentQuestionSchema,
    InstrumentSchema,
    MultilingualItem,
    MultilingualText,
    OrganizationSchema,
    QuestionItemSchema,
    QuestionSchemeSchema,
    QuestionVariableSchema,
    RepresentedVariableSchema,
    RepresentedVariableSchemeSchema,
    SemanticRelationshipSchema,
    StagedImportSchema,
    StagedResourceNodeSchema,
    StudyUnitSchema,
    StudyUnitVariableSchema,
    UrnRegistrySchema,
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
    org_schema = OrganizationSchema(
        urn="urn:ddi:fr.sciencespo:Organization.CDSP:1.0.0",
        name=MultilingualText.from_dict(
            {
                "fr": "Centre de Données Socio-Politiques",
                "en": "Center for Socio-Political Data",
            }
        ),
        organization_type="distributor",
        extended_attributes=[{"type": "acronym", "value": "CDSP"}],
    )
    assert org_schema.urn == "urn:ddi:fr.sciencespo:Organization.CDSP:1.0.0"
    assert org_schema.agency == "fr.sciencespo"
    assert org_schema.name.get("fr") == "Centre de Données Socio-Politiques"
    assert org_schema.organization_type == "distributor"
    assert len(org_schema.extended_attributes) == 1

    group_schema = GroupSchema(
        urn="urn:ddi:fr.sciencespo:group-bpf:1.0.0",
        name=MultilingualText.from_single("Baromètre Politique Français", lang="fr"),
        group_type="study_series",
        references=[
            GroupReferenceSchema(
                resource_type="StudyUnit",
                urn="urn:ddi:fr.sciencespo:su-2007:1.0.0",
            )
        ],
        hashes={"sha256": "group_hash"},
    )
    assert group_schema.urn == "urn:ddi:fr.sciencespo:group-bpf:1.0.0"
    assert group_schema.agency == "fr.sciencespo"
    assert group_schema.identifier == "group-bpf"
    assert group_schema.group_type == "study_series"
    assert len(group_schema.references) == 1
    assert group_schema.references[0].resource_type == "StudyUnit"
    assert group_schema.hashes["sha256"] == "group_hash"

    q_schema = QuestionItemSchema(
        urn="urn:ddi:fr.sciencespo:qi-fr-001:1.0.0",
        scheme_urn="urn:ddi:fr.sciencespo:qs-pol:1.0.0",
        code_list_urn="urn:ddi:fr.sciencespo:cl-fr-001:1.0.0",
        response_domain={
            "type": "code",
            "code_list_urn": "urn:ddi:fr.sciencespo:cl-fr-001:1.0.0",
        },
        question_text=MultilingualText.from_dict({"fr": "Êtes-vous intéressé par la politique ?"}),
        hashes={"sha256": "abc1234", "v2_unordered": "xyz9876"},
        extended_attributes=[{"type": "scope", "value": "core"}],
    )
    assert q_schema.urn == "urn:ddi:fr.sciencespo:qi-fr-001:1.0.0"
    assert q_schema.agency == "fr.sciencespo"
    assert q_schema.scheme_urn == "urn:ddi:fr.sciencespo:qs-pol:1.0.0"
    assert q_schema.code_list_urn == "urn:ddi:fr.sciencespo:cl-fr-001:1.0.0"
    assert q_schema.response_domain["type"] == "code"
    assert q_schema.question_text.get("fr") == "Êtes-vous intéressé par la politique ?"
    assert q_schema.hashes["v2_unordered"] == "xyz9876"
    assert q_schema.extended_attributes[0]["value"] == "core"

    qs_schema = QuestionSchemeSchema(
        urn="urn:ddi:fr.sciencespo:qs-pol:1.0.0",
        name=MultilingualText.from_single("Schéma Questions Politiques", lang="fr"),
        questions=[q_schema],
    )
    assert qs_schema.urn == "urn:ddi:fr.sciencespo:qs-pol:1.0.0"
    assert len(qs_schema.questions) == 1
    assert qs_schema.questions[0].urn == "urn:ddi:fr.sciencespo:qi-fr-001:1.0.0"

    cat_schema = CategorySchema(
        urn="urn:ddi:fr.sciencespo:cat-accord:1.0.0",
        scheme_urn="urn:ddi:fr.sciencespo:cs-interest:1.0.0",
        concept_urn="urn:ddi:fr.sciencespo:concept-accord:1.0.0",
        order=1,
        is_missing=False,
        label=MultilingualText.from_single("D'accord", lang="fr"),
        parent_urn="urn:ddi:fr.sciencespo:cat-parent:1.0.0",
    )
    assert cat_schema.label.get("fr") == "D'accord"
    assert cat_schema.parent_urn == "urn:ddi:fr.sciencespo:cat-parent:1.0.0"
    assert cat_schema.scheme_urn == "urn:ddi:fr.sciencespo:cs-interest:1.0.0"
    assert cat_schema.concept_urn == "urn:ddi:fr.sciencespo:concept-accord:1.0.0"
    assert cat_schema.order == 1
    assert cat_schema.is_missing is False

    cat_missing_schema = CategorySchema(
        urn="urn:ddi:fr.sciencespo:cat-nsp:1.0.0",
        label=MultilingualText.from_single("NSP", lang="fr"),
        is_missing=True,
    )
    assert cat_missing_schema.is_missing is True

    cs_schema = CategorySchemeSchema(
        urn="urn:ddi:fr.sciencespo:cs-interest:1.0.0",
        name=MultilingualText.from_single("Échelle d'intérêt", lang="fr"),
        categories=[cat_schema],
    )
    assert cs_schema.name.get("fr") == "Échelle d'intérêt"
    assert len(cs_schema.categories) == 1

    cl_schema = CodeListSchema(
        urn="urn:ddi:fr.sciencespo:cl-interest:1.0.0",
        scheme_urn="urn:ddi:fr.sciencespo:cs-interest:1.0.0",
    )
    assert cl_schema.scheme_urn == "urn:ddi:fr.sciencespo:cs-interest:1.0.0"

    code_schema = CodeSchema(
        urn="urn:ddi:fr.sciencespo:cl-interest.1:1.0.0",
        code_list_urn="urn:ddi:fr.sciencespo:cl-interest:1.0.0",
        category_urn="urn:ddi:fr.sciencespo:cat-accord:1.0.0",
        code_value="1",
        parent_urn="urn:ddi:fr.sciencespo:cl-interest.0:1.0.0",
        is_missing=False,
    )
    assert code_schema.code_value == "1"
    assert code_schema.parent_urn == "urn:ddi:fr.sciencespo:cl-interest.0:1.0.0"
    assert code_schema.is_missing is False

    code_missing = CodeSchema(
        code_list_urn="urn:ddi:fr.sciencespo:cl-interest:1.0.0",
        category_urn="urn:ddi:fr.sciencespo:cat-nsp:1.0.0",
        code_value="88",
        is_missing=True,
    )
    assert code_missing.is_missing is True

    concept_scheme_schema = ConceptSchemeSchema(
        urn="urn:ddi:fr.sciencespo:cs-thesaurus:1.0.0",
        name=MultilingualText.from_single("Schéma Concepts", lang="fr"),
    )
    assert concept_scheme_schema.urn == "urn:ddi:fr.sciencespo:cs-thesaurus:1.0.0"

    concept_schema = ConceptSchema(
        urn="urn:ddi:fr.sciencespo:concept-pol:1.0.0",
        scheme_urn="urn:ddi:fr.sciencespo:cs-thesaurus:1.0.0",
        uri="https://elsst.cessda.eu/id/4/Politics",
        vocabulary="ELSST",
        notation="POL",
        label=MultilingualText.from_single("Politique", lang="fr"),
        hashes={"sha256": "concept_pol_hash"},
    )
    assert concept_schema.urn == "urn:ddi:fr.sciencespo:concept-pol:1.0.0"
    assert concept_schema.agency == "fr.sciencespo"
    assert concept_schema.scheme_urn == "urn:ddi:fr.sciencespo:cs-thesaurus:1.0.0"
    assert concept_schema.uri == "https://elsst.cessda.eu/id/4/Politics"
    assert concept_schema.vocabulary == "ELSST"
    assert concept_schema.label.get("fr") == "Politique"
    assert concept_schema.hashes["sha256"] == "concept_pol_hash"

    cv_scheme_schema = ConceptualVariableSchemeSchema(
        urn="urn:ddi:fr.sciencespo:cvs-pol:1.0.0",
        name=MultilingualText.from_single("Schéma Variables Conceptuelles", lang="fr"),
    )
    assert cv_scheme_schema.urn == "urn:ddi:fr.sciencespo:cvs-pol:1.0.0"

    cv_schema = ConceptualVariableSchema(
        urn="urn:ddi:fr.sciencespo:cv-interest:1.0.0",
        scheme_urn="urn:ddi:fr.sciencespo:cvs-pol:1.0.0",
        name=MultilingualText.from_single("INTERET_POL", lang="fr"),
        label=MultilingualText.from_single("Concept", lang="fr"),
        description=MultilingualText.from_single("Description du concept", lang="fr"),
    )
    assert cv_schema.scheme_urn == "urn:ddi:fr.sciencespo:cvs-pol:1.0.0"
    assert cv_schema.name.get("fr") == "INTERET_POL"
    assert cv_schema.label.get("fr") == "Concept"
    assert cv_schema.description.get("fr") == "Description du concept"

    rv_scheme_schema = RepresentedVariableSchemeSchema(
        urn="urn:ddi:fr.sciencespo:rvs-bpf:1.0.0",
        name=MultilingualText.from_single("Schéma Variables Représentées", lang="fr"),
    )
    assert rv_scheme_schema.urn == "urn:ddi:fr.sciencespo:rvs-bpf:1.0.0"

    rv_schema = RepresentedVariableSchema(
        urn="urn:ddi:fr.sciencespo:rv-interest:1.0.0",
        scheme_urn="urn:ddi:fr.sciencespo:rvs-bpf:1.0.0",
        conceptual_variable_urn="urn:ddi:fr.sciencespo:cv-interest:1.0.0",
        value_representation={
            "type": "code",
            "code_list_urn": "urn:ddi:fr.sciencespo:cl-interest:1.0.0",
        },
        name=MultilingualText.from_single("RV_INTERET_POL", lang="fr"),
        label=MultilingualText.from_single("Intérêt politique RV", lang="fr"),
        description=MultilingualText.from_single(
            "Description de la variable représentée", lang="fr"
        ),
    )
    assert rv_schema.scheme_urn == "urn:ddi:fr.sciencespo:rvs-bpf:1.0.0"
    assert rv_schema.conceptual_variable_urn == "urn:ddi:fr.sciencespo:cv-interest:1.0.0"
    assert rv_schema.value_representation["type"] == "code"
    assert (
        rv_schema.value_representation["code_list_urn"] == "urn:ddi:fr.sciencespo:cl-interest:1.0.0"
    )
    assert rv_schema.name.get("fr") == "RV_INTERET_POL"
    assert rv_schema.label.get("fr") == "Intérêt politique RV"
    assert rv_schema.description.get("fr") == "Description de la variable représentée"

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
        title=MultilingualText.from_single("Study 2007", lang="fr"),
    )
    assert su_schema.title.get("fr") == "Study 2007"

    iv_scheme_schema = InstanceVariableSchemeSchema(
        urn="urn:ddi:fr.sciencespo:ivs-bpf:1.0.0",
        name=MultilingualText.from_single("Schéma Variables d'Instance", lang="fr"),
    )
    assert iv_scheme_schema.urn == "urn:ddi:fr.sciencespo:ivs-bpf:1.0.0"

    iv_schema = InstanceVariableSchema(
        urn="urn:ddi:fr.sciencespo:iv-q01a:1.0.0",
        scheme_urn="urn:ddi:fr.sciencespo:ivs-bpf:1.0.0",
        represented_variable_urn="urn:ddi:fr.sciencespo:rv-interest:1.0.0",
        name="q01a",
        label=MultilingualText.from_single("Intérêt politique Q1", lang="fr"),
        description=MultilingualText.from_single("Variable q01a", lang="fr"),
    )
    assert iv_schema.scheme_urn == "urn:ddi:fr.sciencespo:ivs-bpf:1.0.0"
    assert iv_schema.name.get() == "q01a"
    assert iv_schema.description.get("fr") == "Variable q01a"

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


def test_semantic_relationship_schema() -> None:
    """Test SemanticRelationshipSchema validation, attributes, and serialization."""
    schema = SemanticRelationshipSchema(
        subject_type="ConceptualVariable",
        subject_urn="urn:ddi:fr.sciencespo:cv-fr-001:1.0.0",
        predicate="skos:exactMatch",
        object_type="Concept",
        object_urn="https://elsst.cessda.eu/id/4/Politics",
        extended_attributes=[
            {"type": "confidence", "value": 0.95},
            {"type": "alignment_tool", "value": "ELSST Mapper"},
        ],
    )

    assert schema.subject_type == "ConceptualVariable"
    assert schema.subject_urn == "urn:ddi:fr.sciencespo:cv-fr-001:1.0.0"
    assert schema.predicate == "skos:exactMatch"
    assert schema.object_type == "Concept"
    assert schema.object_urn == "https://elsst.cessda.eu/id/4/Politics"
    assert len(schema.extended_attributes) == 2

    # Serialization roundtrip
    dumped = schema.model_dump()
    assert dumped["predicate"] == "skos:exactMatch"
    assert dumped["extended_attributes"][0]["value"] == 0.95


def test_urn_registry_schema() -> None:
    """Test UrnRegistrySchema validation for DDI and external URIs."""
    reg = UrnRegistrySchema(
        urn="urn:ddi:fr.sciencespo:qi-001:1.0.0",
        resource_type="QuestionItem",
        extended_attributes=[{"type": "tag", "value": "demo"}],
    )
    assert reg.urn == "urn:ddi:fr.sciencespo:qi-001:1.0.0"
    assert reg.resource_type == "QuestionItem"
    assert reg.extended_attributes[0]["value"] == "demo"

    # External URI
    reg_ext = UrnRegistrySchema(
        urn="https://elsst.cessda.eu/id/4/Politics",
        resource_type="Concept",
    )
    assert reg_ext.urn == "https://elsst.cessda.eu/id/4/Politics"
    assert reg_ext.extended_attributes == []


def test_all_resource_schemas_require_urn_and_name_and_other_fields_nullable() -> None:
    """Verify that all DDI resource schemas validate with only urn and name."""
    min_name = MultilingualText.from_single("Test Resource")

    # 1. OrganizationSchema
    org = OrganizationSchema(urn="urn:ddi:fr.sciencespo:org:1.0.0", name=min_name)
    assert org.organization_type is None
    assert org.hashes is None

    # 2. GroupSchema
    grp = GroupSchema(urn="urn:ddi:fr.sciencespo:grp:1.0.0", name=min_name)
    assert grp.description is None
    assert grp.group_type is None
    assert grp.references == []

    # 3. ConceptSchemeSchema & ConceptSchema
    cs = ConceptSchemeSchema(urn="urn:ddi:fr.sciencespo:cs:1.0.0", name=min_name)
    assert cs.description is None
    assert "hashes" not in ConceptSchemeSchema.model_fields
    concept = ConceptSchema(urn="urn:ddi:fr.sciencespo:concept:1.0.0")
    assert concept.label is None
    assert concept.scheme_urn is None
    assert "hashes" in ConceptSchema.model_fields

    # 4. ConceptualVariableSchemeSchema & ConceptualVariableSchema
    cvs = ConceptualVariableSchemeSchema(urn="urn:ddi:fr.sciencespo:cvs:1.0.0", name=min_name)
    assert cvs.description is None
    assert "hashes" not in ConceptualVariableSchemeSchema.model_fields
    cv = ConceptualVariableSchema(urn="urn:ddi:fr.sciencespo:cv:1.0.0", name=min_name)
    assert cv.scheme_urn is None
    assert cv.concept_urn is None
    assert cv.label is None
    assert "hashes" in ConceptualVariableSchema.model_fields

    # 5. QuestionSchemeSchema & QuestionItemSchema
    qs = QuestionSchemeSchema(urn="urn:ddi:fr.sciencespo:qs:1.0.0", name=min_name)
    assert qs.description is None
    assert "hashes" not in QuestionSchemeSchema.model_fields
    qi = QuestionItemSchema(urn="urn:ddi:fr.sciencespo:qi:1.0.0", name=min_name)
    assert qi.question_text is None
    assert qi.scheme_urn is None
    assert qi.code_list_urn is None
    assert qi.response_domain is None
    assert "hashes" in QuestionItemSchema.model_fields

    # 6. CategorySchemeSchema & CategorySchema
    cats = CategorySchemeSchema(urn="urn:ddi:fr.sciencespo:cats:1.0.0", name=min_name)
    assert cats.description is None
    assert "hashes" not in CategorySchemeSchema.model_fields
    cat = CategorySchema(urn="urn:ddi:fr.sciencespo:cat:1.0.0", name=min_name)
    assert cat.label is None
    assert cat.scheme_urn is None
    assert cat.concept_urn is None
    assert "hashes" in CategorySchema.model_fields

    # 7. CodeListSchema
    cl = CodeListSchema(urn="urn:ddi:fr.sciencespo:cl:1.0.0", name=min_name)
    assert cl.description is None
    assert cl.scheme_urn is None
    assert "hashes" in CodeListSchema.model_fields

    # 8. RepresentedVariableSchemeSchema & RepresentedVariableSchema
    rvs = RepresentedVariableSchemeSchema(urn="urn:ddi:fr.sciencespo:rvs:1.0.0", name=min_name)
    assert rvs.description is None
    assert "hashes" not in RepresentedVariableSchemeSchema.model_fields
    rv = RepresentedVariableSchema(urn="urn:ddi:fr.sciencespo:rv:1.0.0", name=min_name)
    assert rv.scheme_urn is None
    assert rv.conceptual_variable_urn is None
    assert rv.code_list_urn is None
    assert rv.value_representation is None
    assert rv.label is None
    assert "hashes" in RepresentedVariableSchema.model_fields

    # 9. StudyUnitSchema
    su = StudyUnitSchema(urn="urn:ddi:fr.sciencespo:su:1.0.0", name=min_name)
    assert su.title is None
    assert su.external_ref is None
    assert su.year is None
    assert "hashes" in StudyUnitSchema.model_fields

    # 10. InstanceVariableSchemeSchema & InstanceVariableSchema
    ivs = InstanceVariableSchemeSchema(urn="urn:ddi:fr.sciencespo:ivs:1.0.0", name=min_name)
    assert ivs.description is None
    assert "hashes" not in InstanceVariableSchemeSchema.model_fields
    iv = InstanceVariableSchema(urn="urn:ddi:fr.sciencespo:iv:1.0.0", name=min_name)
    assert iv.scheme_urn is None
    assert iv.represented_variable_urn is None
    assert iv.label is None
    assert "hashes" in InstanceVariableSchema.model_fields

    # 11. InstrumentSchema
    inst = InstrumentSchema(urn="urn:ddi:fr.sciencespo:inst:1.0.0", name=min_name)
    assert inst.label is None
    assert inst.description is None
    assert "hashes" in InstrumentSchema.model_fields
