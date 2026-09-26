"""Tests for FAIRwDDI Django ORM models, relationships, and constraints."""

import pytest
from django.test import TestCase

from fairwddi.models import (
    Category,
    CategoryScheme,
    Code,
    CodeList,
    Concept,
    ConceptScheme,
    ConceptualVariable,
    ConceptualVariableScheme,
    EventLog,
    Group,
    InstanceVariable,
    InstanceVariableScheme,
    Instrument,
    InstrumentQuestion,
    MetadataQuarantine,
    Organization,
    QuestionItem,
    QuestionScheme,
    QuestionVariable,
    RepresentedVariable,
    RepresentedVariableScheme,
    SemanticRelationship,
    StagedImport,
    StagedResourceNode,
    StudyUnit,
    StudyUnitVariable,
    URNAlias,
    UrnRegistry,
)


@pytest.mark.django_db
class TestFairwDDIModels(TestCase):
    """Integration test case for all FAIRwDDI models."""

    def setUp(self) -> None:
        """Set up foundational records."""
        self.organization = Organization.objects.create(
            urn="urn:ddi:fr.sciencespo:Organization.CDSP:1.0.0",
            name=[
                {"lang": "fr", "value": "Centre de Données Socio-Politiques"},
                {"lang": "en", "value": "Center for Socio-Political Data"},
            ],
            organization_type="distributor",
            extended_attributes=[
                {"type": "acronym", "value": "CDSP"},
                {"type": "uri", "value": "https://cdsp.sciences-po.fr/"},
            ],
        )
        self.group = Group.objects.create(
            urn="urn:ddi:fr.sciencespo:group-bpf:1.0.0",
            name=[{"lang": "fr", "value": "Baromètre Politique Français"}],
            description=[{"lang": "fr", "value": "Série d'enquêtes électorales"}],
            group_type="study_series",
            references=[
                {"resource_type": "StudyUnit", "urn": "urn:ddi:fr.sciencespo:su-bpf-2007-w01:1.0.0"}
            ],
            hashes={"sha256": "group_hash_001"},
        )

    def test_organization_and_group(self) -> None:
        """Test Organization and generic Group resources."""
        assert self.organization.pk == "urn:ddi:fr.sciencespo:Organization.CDSP:1.0.0"
        assert self.organization.agency == "fr.sciencespo"
        assert self.organization.organization_type == "distributor"
        assert str(self.organization) == "Centre de Données Socio-Politiques"
        assert len(self.organization.extended_attributes) == 2

        assert self.group.pk == "urn:ddi:fr.sciencespo:group-bpf:1.0.0"
        assert self.group.agency == "fr.sciencespo"
        assert self.group.identifier == "group-bpf"
        assert self.group.version == "1.0.0"
        assert self.group.group_type == "study_series"
        assert len(self.group.references) == 1
        assert self.group.references[0]["resource_type"] == "StudyUnit"
        assert str(self.group) == "Baromètre Politique Français"
        assert self.group.hashes["sha256"] == "group_hash_001"

    def test_concept_layer_and_skos_hierarchy(self) -> None:
        """Test ConceptScheme, Concept, hierarchy, and ConceptualVariableScheme."""
        concept_scheme = ConceptScheme.objects.create(
            urn="urn:ddi:fr.sciencespo:cs-thesaurus:1.0.0",
            name=[{"lang": "fr", "value": "Schéma de concepts"}],
        )
        assert concept_scheme.pk == "urn:ddi:fr.sciencespo:cs-thesaurus:1.0.0"
        assert str(concept_scheme) == "Schéma de concepts"

        parent_concept = Concept.objects.create(
            urn="urn:ddi:fr.sciencespo:concept-pol:1.0.0",
            scheme=concept_scheme,
            uri="https://elsst.cessda.eu/id/4/Politics",
            vocabulary="ELSST",
            notation="POL",
            label=[{"lang": "fr", "value": "Politique"}, {"lang": "en", "value": "Politics"}],
            definition=[{"lang": "fr", "value": "Affaires politiques et gouvernance"}],
            concept_type="domain",
            hashes={"sha256": "concept_pol_hash"},
            extended_attributes=[{"type": "scope", "value": "core"}],
        )
        child_concept = Concept.objects.create(
            urn="urn:ddi:fr.sciencespo:concept-pol-att:1.0.0",
            scheme=concept_scheme,
            uri="https://elsst.cessda.eu/id/4/PoliticalAttitudes",
            vocabulary="ELSST",
            notation="POL.ATT",
            label=[{"lang": "fr", "value": "Attitudes politiques"}],
            parent=parent_concept,
            concept_type="concept",
            hashes={"sha256": "concept_pol_att_hash"},
        )
        assert parent_concept.pk == "urn:ddi:fr.sciencespo:concept-pol:1.0.0"
        assert str(parent_concept) == "Politique"
        assert parent_concept.vocabulary == "ELSST"
        assert parent_concept.scheme == concept_scheme
        assert concept_scheme.concepts.count() == 2
        assert parent_concept.narrower_concepts.count() == 1
        assert child_concept.parent == parent_concept
        assert parent_concept.extended_attributes[0]["value"] == "core"

        # ConceptualVariableScheme
        cv_scheme = ConceptualVariableScheme.objects.create(
            urn="urn:ddi:fr.sciencespo:cvs-pol:1.0.0",
            name=[{"lang": "fr", "value": "Schéma de variables conceptuelles"}],
        )
        assert cv_scheme.pk == "urn:ddi:fr.sciencespo:cvs-pol:1.0.0"
        assert str(cv_scheme) == "Schéma de variables conceptuelles"

        # ConceptualVariable with URN PK and hashes
        cv = ConceptualVariable.objects.create(
            scheme=cv_scheme,
            concept=child_concept,
            urn="urn:ddi:fr.sciencespo:cv-fr-001:1.0.0",
            name=[{"lang": "fr", "value": "INTERET_POL"}],
            label=[{"lang": "fr", "value": "Intérêt pour la politique"}],
            description=[{"lang": "fr", "value": "Mesure du niveau d'intérêt politique"}],
            hashes={"sha256": "abc111", "v1_strict": "abc111"},
            extended_attributes=[{"type": "domain", "value": "attitudes"}],
        )
        assert cv.pk == "urn:ddi:fr.sciencespo:cv-fr-001:1.0.0"
        assert str(cv) == "INTERET_POL"
        assert cv.scheme == cv_scheme
        assert cv_scheme.conceptual_variables.count() == 1
        assert cv.concept == child_concept
        assert cv.hashes["sha256"] == "abc111"
        assert cv.extended_attributes[0]["type"] == "domain"

    def test_representation_layer(self) -> None:
        """Test QuestionScheme, QuestionItem, Category & Code hierarchy, and QuestionVariable."""
        # QuestionScheme
        qs = QuestionScheme.objects.create(
            urn="urn:ddi:fr.sciencespo:qs-pol:1.0.0",
            name=[{"lang": "fr", "value": "Schéma de questions politiques"}],
        )

        # QuestionItem linked to QuestionScheme
        qi = QuestionItem.objects.create(
            urn="urn:ddi:fr.sciencespo:qi-fr-001:1.0.0",
            scheme=qs,
            question_text=[
                {"lang": "fr", "value": "Diriez-vous que vous vous intéressez à la politique ?"},
                {"lang": "en", "value": "Would you say you are interested in politics?"},
            ],
            hashes={"sha256": "qi_hash_001"},
            extended_attributes=[
                {"type": "interviewer_instructions", "value": "Lire les options de réponse."}
            ],
        )
        assert qi.pk == "urn:ddi:fr.sciencespo:qi-fr-001:1.0.0"
        assert qi.scheme == qs
        assert qs.questions.count() == 1
        assert qi.question_text[0]["lang"] == "fr"
        assert qi.extended_attributes[0]["type"] == "interviewer_instructions"

        # CategoryScheme
        cat_scheme = CategoryScheme.objects.create(
            urn="urn:ddi:fr.sciencespo:cs-fr-interest:1.0.0",
            name=[{"lang": "fr", "value": "Échelle d'intérêt politique"}],
        )

        # Concept anchor for category
        cat_concept = Concept.objects.create(
            urn="urn:ddi:fr.sciencespo:concept-yes:1.0.0",
            label=[{"lang": "fr", "value": "Accord positif"}],
        )

        # Categories with parent hierarchy belonging to CategoryScheme
        cat_parent = Category.objects.create(
            urn="urn:ddi:fr.sciencespo:cat-pol-general:1.0.0",
            scheme=cat_scheme,
            order=0,
            label=[{"lang": "fr", "value": "Échelle d'accord général"}],
        )
        cat_yes = Category.objects.create(
            urn="urn:ddi:fr.sciencespo:cat-fr-yes:1.0.0",
            scheme=cat_scheme,
            concept=cat_concept,
            order=1,
            label=[{"lang": "fr", "value": "Oui, beaucoup"}, {"lang": "en", "value": "Yes, a lot"}],
            parent=cat_parent,
            hashes={"sha256": "cat_yes_hash"},
        )
        cat_no = Category.objects.create(
            urn="urn:ddi:fr.sciencespo:cat-fr-no:1.0.0",
            scheme=cat_scheme,
            order=2,
            is_missing=False,
            label=[
                {"lang": "fr", "value": "Non, pas du tout"},
                {"lang": "en", "value": "No, not at all"},
            ],
            parent=cat_parent,
            hashes={"sha256": "cat_no_hash"},
        )
        cat_nsp = Category.objects.create(
            urn="urn:ddi:fr.sciencespo:cat-fr-nsp:1.0.0",
            scheme=cat_scheme,
            order=3,
            is_missing=True,
            label=[{"lang": "fr", "value": "Ne sait pas"}],
            hashes={"sha256": "cat_nsp_hash"},
        )
        assert cat_yes.parent == cat_parent
        assert cat_yes.concept == cat_concept
        assert cat_concept.categories.count() == 1
        assert cat_parent.children.count() == 2
        assert cat_scheme.categories.count() == 4
        assert cat_yes.scheme == cat_scheme
        assert cat_yes.is_missing is False
        assert cat_nsp.is_missing is True

        # CodeList & Codes with parent hierarchy
        code_list = CodeList.objects.create(
            urn="urn:ddi:fr.sciencespo:cl-fr-001:1.0.0",
            name=[{"lang": "fr", "value": "Codes intérêt"}],
            scheme=cat_scheme,
            hashes={"sha256": "cl_hash_001"},
        )
        parent_code = Code.objects.create(
            code_list=code_list,
            category=cat_parent,
            code_value="0",
            order=0,
        )
        code1 = Code.objects.create(
            code_list=code_list,
            category=cat_yes,
            code_value="1",
            parent=parent_code,
            order=1,
            is_missing=False,
        )
        Code.objects.create(
            code_list=code_list,
            category=cat_no,
            code_value="2",
            parent=parent_code,
            order=2,
            is_missing=False,
        )
        code_missing = Code.objects.create(
            code_list=code_list,
            category=cat_no,
            code_value="99",
            order=3,
            is_missing=True,
        )
        assert code_list.codes.count() == 4
        assert code1.parent == parent_code
        assert parent_code.children.count() == 2
        assert code1.is_missing is False
        assert code_missing.is_missing is True

        # Link QuestionItem with CodeList response_domain
        qi.code_list = code_list
        qi.save()
        assert qi.code_list == code_list
        assert qi.response_domain["type"] == "code"
        assert qi.response_domain["code_list_urn"] == code_list.urn
        assert code_list.question_items.count() == 1

        # QuestionItem with numeric response_domain
        qi_numeric = QuestionItem.objects.create(
            urn="urn:ddi:fr.sciencespo:qi-fr-numeric:1.0.0",
            scheme=qs,
            name=[{"lang": "fr", "value": "QI_AGE"}],
            response_domain={
                "type": "numeric",
                "numeric_type": "integer",
                "min": 18,
                "max": 99,
            },
        )
        assert qi_numeric.code_list is None
        assert qi_numeric.response_domain["type"] == "numeric"
        assert qi_numeric.response_domain["min"] == 18

        # RepresentedVariableScheme
        rv_scheme = RepresentedVariableScheme.objects.create(
            urn="urn:ddi:fr.sciencespo:rvs-pol:1.0.0",
            name=[{"lang": "fr", "value": "Schéma de variables représentées"}],
        )
        assert rv_scheme.pk == "urn:ddi:fr.sciencespo:rvs-pol:1.0.0"
        assert str(rv_scheme) == "Schéma de variables représentées"

        # ConceptualVariable
        cv = ConceptualVariable.objects.create(
            urn="urn:ddi:fr.sciencespo:cv-002:1.0.0",
            label=[{"lang": "fr", "value": "Intérêt politique"}],
        )

        # RepresentedVariable (decoupled from question_item) with code value_representation
        rv = RepresentedVariable.objects.create(
            scheme=rv_scheme,
            conceptual_variable=cv,
            code_list=code_list,
            value_representation={"type": "code", "code_list_urn": code_list.urn},
            urn="urn:ddi:fr.sciencespo:rv-fr-001:1.0.0",
            name=[{"lang": "fr", "value": "RV_INTERET_POL"}],
            label=[{"lang": "fr", "value": "Intérêt politique RV"}],
            description=[{"lang": "fr", "value": "Description de la variable représentée"}],
            hashes={"sha256": "rv_hash_001"},
        )
        assert rv.scheme == rv_scheme
        assert str(rv) == "RV_INTERET_POL"
        assert rv_scheme.represented_variables.count() == 1
        assert rv.code_list == code_list
        assert rv.conceptual_variable == cv
        assert rv.value_representation["type"] == "code"
        assert rv.value_representation["code_list_urn"] == code_list.urn

        # RepresentedVariable with numeric value_representation
        rv_numeric = RepresentedVariable.objects.create(
            scheme=rv_scheme,
            conceptual_variable=cv,
            value_representation={
                "type": "numeric",
                "numeric_type": "integer",
                "min": 0,
                "max": 100,
            },
            urn="urn:ddi:fr.sciencespo:rv-fr-numeric:1.0.0",
            name=[{"lang": "fr", "value": "RV_AGE_NUMERIC"}],
            label=[{"lang": "fr", "value": "Âge en années"}],
        )
        assert rv_numeric.code_list is None
        assert rv_numeric.value_representation["type"] == "numeric"
        assert rv_numeric.value_representation["min"] == 0

        # QuestionVariable junction
        qv = QuestionVariable.objects.create(
            question_item=qi,
            represented_variable=rv,
            path="/RepresentedVariable/QuestionItem[1]",
            order=1,
        )
        assert qv.question_item == qi
        assert qv.represented_variable == rv
        assert qv.path == "/RepresentedVariable/QuestionItem[1]"
        assert rv.question_associations.count() == 1

    def test_instrument_and_question_association(self) -> None:
        """Test Instrument and InstrumentQuestion junction."""
        instrument = Instrument.objects.create(
            urn="urn:ddi:fr.sciencespo:inst-bpf-2007:1.0.0",
            name=[{"lang": "fr", "value": "Questionnaire BPF 2007"}],
            label=[{"lang": "fr", "value": "Questionnaire Principal"}],
            hashes={"sha256": "inst_hash_001"},
            extended_attributes=[{"type": "collection_mode", "value": "CAPI"}],
        )
        qi = QuestionItem.objects.create(
            urn="urn:ddi:fr.sciencespo:qi-inst-test:1.0.0",
            question_text=[{"lang": "fr", "value": "Question Test"}],
        )
        iq = InstrumentQuestion.objects.create(
            instrument=instrument,
            question_item=qi,
            path="/Instrument/Sequence/POL/Q1",
            order=1,
        )
        assert instrument.pk == "urn:ddi:fr.sciencespo:inst-bpf-2007:1.0.0"
        assert instrument.question_associations.count() == 1
        assert iq.path == "/Instrument/Sequence/POL/Q1"
        assert iq.order == 1

    def test_dataset_layer_and_cascade(self) -> None:
        """Test StudyUnit, InstanceVariableScheme, InstanceVariable, cascade."""
        study_unit = StudyUnit.objects.create(
            urn="urn:ddi:fr.sciencespo:su-bpf-2007-1:1.0.0",
            title=[{"lang": "fr", "value": "BPF Vague 1 (2007)"}],
            external_ref="10.7303/cdsp-bpf2007-1",
            year=2007,
        )

        cv = ConceptualVariable.objects.create(
            urn="urn:ddi:fr.sciencespo:cv-cascade:1.0.0",
            label=[{"lang": "fr", "value": "Concept"}],
        )
        rv = RepresentedVariable.objects.create(
            urn="urn:ddi:fr.sciencespo:rv-cascade:1.0.0",
            conceptual_variable=cv,
        )

        iv_scheme = InstanceVariableScheme.objects.create(
            urn="urn:ddi:fr.sciencespo:ivs-bpf:1.0.0",
            name=[{"lang": "fr", "value": "Schéma de variables d'instance"}],
        )
        assert iv_scheme.pk == "urn:ddi:fr.sciencespo:ivs-bpf:1.0.0"
        assert str(iv_scheme) == "Schéma de variables d'instance"

        iv = InstanceVariable.objects.create(
            scheme=iv_scheme,
            represented_variable=rv,
            name=[{"value": "q01a"}],
            label=[{"lang": "fr", "value": "Intérêt politique Q1"}],
            description=[{"lang": "fr", "value": "Variable q01a dans le dataset"}],
            extended_attributes=[
                {"type": "universe", "value": "Ensemble des électeurs inscrits"},
                {"type": "notes", "value": "Variable filtrée"},
            ],
            urn="urn:ddi:fr.sciencespo:iv-fr-bpf2007-q01a:1.0.0",
        )
        assert iv.pk == "urn:ddi:fr.sciencespo:iv-fr-bpf2007-q01a:1.0.0"
        assert str(iv) == "q01a"
        assert iv.scheme == iv_scheme
        assert iv_scheme.instance_variables.count() == 1
        assert iv.represented_variable.conceptual_variable == cv
        assert iv.extended_attributes[0]["type"] == "universe"

        # StudyUnitVariable mapping with path
        su_var = StudyUnitVariable.objects.create(
            study_unit=study_unit,
            instance_variable=iv,
            path="/StudyUnit/DataPipeline/q01a",
            order=1,
        )
        assert study_unit.study_unit_variables.count() == 1
        assert su_var.instance_variable == iv
        assert su_var.path == "/StudyUnit/DataPipeline/q01a"

    def test_event_log(self) -> None:
        """Test EventLog model for generic DDI resource lifecycle tracking."""
        log = EventLog.objects.create(
            urn="urn:ddi:fr.sciencespo:qi-fr-001:1.0.0",
            event_type="normalized",
            event_data={"source": "importer", "status": "success"},
        )
        assert log.id is not None
        assert log.urn == "urn:ddi:fr.sciencespo:qi-fr-001:1.0.0"
        assert log.event_type == "normalized"
        assert log.event_data["source"] == "importer"
        assert EventLog.objects.filter(urn="urn:ddi:fr.sciencespo:qi-fr-001:1.0.0").count() == 1

    def test_auto_urn_generation_fallback(self) -> None:
        """Test that models inheriting DDIIdentifiable auto-generate canonical URN when omitted."""
        cat = Category.objects.create(
            label=[{"lang": "fr", "value": "Auto Generated Category"}],
            hashes={"sha256": "hash1234567890abcdef"},
        )
        assert cat.urn is not None
        assert cat.urn.startswith("urn:ddi:fr.sciencespo:hash1234567890ab:1.0.0")
        assert cat.pk == cat.urn
        assert cat.agency == "fr.sciencespo"
        assert cat.version == "1.0.0"

    def test_urn_parsing_helpers(self) -> None:
        """Test canonical and non-canonical URN helper properties."""
        # 1. Agency-scoped canonical URN
        cat_agency = Category(urn="urn:ddi:us.mpc:V321:2")
        assert cat_agency.is_canonical_ddi is True
        assert cat_agency.is_maintainable_scoped is False
        assert cat_agency.agency == "us.mpc"
        assert cat_agency.identifier == "V321"
        assert cat_agency.maintainable_id == "V321"
        assert cat_agency.object_id == "V321"
        assert cat_agency.version == "2"

        # 2. Maintainable-scoped canonical URN (MaintainableID.ObjectID)
        cat_maint = Category(urn="urn:ddi:us.mpc.ipums:CodeList01.Code02:3.0.1")
        assert cat_maint.is_canonical_ddi is True
        assert cat_maint.is_maintainable_scoped is True
        assert cat_maint.agency == "us.mpc.ipums"
        assert cat_maint.identifier == "CodeList01.Code02"
        assert cat_maint.maintainable_id == "CodeList01"
        assert cat_maint.object_id == "Code02"
        assert cat_maint.version == "3.0.1"

        # 3. Non-canonical / External URN
        cat_raw = Category(urn="raw:closer:qi:1234")
        assert cat_raw.is_canonical_ddi is False
        assert cat_raw.is_maintainable_scoped is False
        assert cat_raw.agency == "fr.sciencespo"  # fallback
        assert cat_raw.identifier == "raw:closer:qi:1234"
        assert cat_raw.maintainable_id is None
        assert cat_raw.object_id == "raw:closer:qi:1234"
        assert cat_raw.version == "1.0.0"

    def test_infrastructure_and_staging_layer(self) -> None:
        """Test URNAlias, MetadataQuarantine, StagedImport, and StagedResourceNode."""
        # UrnRegistry
        reg = UrnRegistry.objects.create(
            urn="urn:ddi:fr.sciencespo:qi-fr-001:1.0.0",
            resource_type="QuestionItem",
            extended_attributes=[{"type": "source", "value": "test"}],
        )
        assert reg.urn == "urn:ddi:fr.sciencespo:qi-fr-001:1.0.0"
        assert reg.resource_type == "QuestionItem"
        assert str(reg) == "urn:ddi:fr.sciencespo:qi-fr-001:1.0.0 (QuestionItem)"

        # External non-DDI URN / URI registration
        reg_ext = UrnRegistry.objects.create(
            urn="https://elsst.cessda.eu/id/4/PoliticalAttitudes",
            resource_type="Concept",
            extended_attributes=[{"type": "vocabulary", "value": "ELSST"}],
        )
        assert reg_ext.resource_type == "Concept"

        # URNAlias
        alias = URNAlias.objects.create(
            alias_urn="raw:colectica:random-uuid-1234",
            canonical_urn="urn:ddi:fr.sciencespo:qi-fr-001:1.0.0",
            entity_type="QuestionItem",
            hash_strategy="v1_strict_sha256",
            source_file="survey2007.xml",
        )
        assert alias.canonical_urn == "urn:ddi:fr.sciencespo:qi-fr-001:1.0.0"

        # MetadataQuarantine
        quarantine = MetadataQuarantine.objects.create(
            incoming_urn="urn:incoming:001",
            existing_urn="urn:existing:001",
            entity_type="Category",
            incoming_content={"label": [{"lang": "fr", "value": "Label Modifié"}]},
            existing_content_hash="hash_old",
            incoming_content_hash="hash_new",
            conflict_type="hash_mismatch",
        )
        assert quarantine.conflict_type == "hash_mismatch"
        assert quarantine.resolution is None

        # StagedImport & StagedResourceNode
        staged_import = StagedImport.objects.create(
            source_format="ddi-l:4.0:json",
            file_name="closer_sample.json",
            import_options={"agency": "fr.sciencespo", "strict": True},
            total_resources=1,
            processed_resources=0,
        )
        node = StagedResourceNode.objects.create(
            staged_import=staged_import,
            resource_type="QuestionItem",
            raw_urn="urn:closer:qi:999",
            raw_value={"question_text": [{"lang": "en", "value": "Are you employed?"}]},
        )
        assert staged_import.nodes.count() == 1
        assert node.staged_import == staged_import

    def test_semantic_relationship_triple(self) -> None:
        """Test SemanticRelationship model, RDF triple structure, constraints, and queries."""
        from django.db import IntegrityError

        rel = SemanticRelationship.objects.create(
            subject_type="ConceptualVariable",
            subject_urn="urn:ddi:fr.sciencespo:cv-fr-001:1.0.0",
            predicate="skos:exactMatch",
            object_type="Concept",
            object_urn="https://elsst.cessda.eu/id/4/Politics",
            extended_attributes=[
                {"type": "confidence", "value": 0.99},
                {"type": "curator", "value": "CDSP"},
            ],
        )

        assert rel.id is not None
        assert rel.subject_type == "ConceptualVariable"
        assert rel.predicate == "skos:exactMatch"
        assert rel.object_urn == "https://elsst.cessda.eu/id/4/Politics"
        assert len(rel.extended_attributes) == 2
        assert rel.extended_attributes[0]["value"] == 0.99
        assert str(rel) == (
            "urn:ddi:fr.sciencespo:cv-fr-001:1.0.0 "
            "--[skos:exactMatch]--> "
            "https://elsst.cessda.eu/id/4/Politics"
        )

        # Query filtering by subject_urn & predicate
        matched = SemanticRelationship.objects.filter(
            subject_urn="urn:ddi:fr.sciencespo:cv-fr-001:1.0.0",
            predicate="skos:exactMatch",
        )
        assert matched.count() == 1

        # Test duplicate triple uniqueness constraint
        with pytest.raises(IntegrityError):
            SemanticRelationship.objects.create(
                subject_type="ConceptualVariable",
                subject_urn="urn:ddi:fr.sciencespo:cv-fr-001:1.0.0",
                predicate="skos:exactMatch",
                object_type="Concept",
                object_urn="https://elsst.cessda.eu/id/4/Politics",
            )

    def test_all_resources_require_urn_and_name_and_other_fields_nullable(self) -> None:
        """Verify that all DDI resources require urn and name, and all other fields are nullable."""
        # 1. Organization
        org = Organization.objects.create(
            urn="urn:ddi:fr.sciencespo:org-minimal:1.0.0",
            name=[{"value": "Minimal Org"}],
            hashes=None,
        )
        assert org.organization_type is None
        assert org.extended_attributes == []
        assert org.hashes is None

        # 2. Group
        grp = Group.objects.create(
            urn="urn:ddi:fr.sciencespo:grp-minimal:1.0.0",
            name=[{"value": "Minimal Group"}],
        )
        assert grp.description == []
        assert grp.group_type is None
        assert grp.references == []

        # 3. ConceptScheme & Concept
        cs = ConceptScheme.objects.create(
            urn="urn:ddi:fr.sciencespo:cs-minimal:1.0.0",
            name=[{"value": "Minimal CS"}],
        )
        assert cs.description == []
        assert not hasattr(cs, "hashes")
        concept = Concept.objects.create(
            urn="urn:ddi:fr.sciencespo:concept-minimal:1.0.0",
        )
        assert concept.scheme is None
        assert concept.uri is None
        assert concept.vocabulary is None
        assert concept.notation is None
        assert concept.label == []
        assert concept.description == []
        assert concept.definition == []
        assert concept.parent is None
        assert concept.concept_type is None
        assert hasattr(concept, "hashes")

        # 4. ConceptualVariableScheme & ConceptualVariable
        cvs = ConceptualVariableScheme.objects.create(
            urn="urn:ddi:fr.sciencespo:cvs-minimal:1.0.0",
            name=[{"value": "Minimal CVS"}],
        )
        assert cvs.description == []
        assert not hasattr(cvs, "hashes")
        cv = ConceptualVariable.objects.create(
            urn="urn:ddi:fr.sciencespo:cv-minimal:1.0.0",
            name=[{"value": "Minimal CV"}],
        )
        assert cv.scheme is None
        assert cv.concept is None
        assert cv.label == []
        assert cv.description == []
        assert hasattr(cv, "hashes")

        # 5. QuestionScheme & QuestionItem
        qs = QuestionScheme.objects.create(
            urn="urn:ddi:fr.sciencespo:qs-minimal:1.0.0",
            name=[{"value": "Minimal QS"}],
        )
        assert qs.description == []
        assert not hasattr(qs, "hashes")
        qi = QuestionItem.objects.create(
            urn="urn:ddi:fr.sciencespo:qi-minimal:1.0.0",
            name=[{"value": "Minimal QI"}],
        )
        assert qi.scheme is None
        assert qi.code_list is None
        assert qi.response_domain == {}
        assert qi.question_text == []
        assert qi.extended_attributes == []
        assert hasattr(qi, "hashes")

        # 6. CategoryScheme & Category
        cats = CategoryScheme.objects.create(
            urn="urn:ddi:fr.sciencespo:cats-minimal:1.0.0",
            name=[{"value": "Minimal CatS"}],
        )
        assert cats.description == []
        assert not hasattr(cats, "hashes")
        cat = Category.objects.create(
            urn="urn:ddi:fr.sciencespo:cat-minimal:1.0.0",
            name=[{"value": "Minimal Cat"}],
        )
        assert cat.scheme is None
        assert cat.concept is None
        assert cat.label == []
        assert cat.parent is None
        assert cat.order == 0
        assert cat.is_missing is False
        assert hasattr(cat, "hashes")

        # 7. CodeList
        cl = CodeList.objects.create(
            urn="urn:ddi:fr.sciencespo:cl-minimal:1.0.0",
            name=[{"value": "Minimal CL"}],
        )
        assert cl.scheme is None
        assert cl.description == []
        assert hasattr(cl, "hashes")

        # 8. RepresentedVariableScheme & RepresentedVariable
        rvs = RepresentedVariableScheme.objects.create(
            urn="urn:ddi:fr.sciencespo:rvs-minimal:1.0.0",
            name=[{"value": "Minimal RVS"}],
        )
        assert rvs.description == []
        assert not hasattr(rvs, "hashes")
        rv = RepresentedVariable.objects.create(
            urn="urn:ddi:fr.sciencespo:rv-minimal:1.0.0",
            name=[{"value": "Minimal RV"}],
        )
        assert rv.scheme is None
        assert rv.conceptual_variable is None
        assert rv.code_list is None
        assert rv.label == []
        assert rv.description == []
        assert hasattr(rv, "hashes")

        # 9. StudyUnit
        su = StudyUnit.objects.create(
            urn="urn:ddi:fr.sciencespo:su-minimal:1.0.0",
            name=[{"value": "Minimal SU"}],
        )
        assert su.title == []
        assert su.external_ref is None
        assert su.year is None
        assert su.description == []
        assert hasattr(su, "hashes")

        # 10. InstanceVariableScheme & InstanceVariable
        ivs = InstanceVariableScheme.objects.create(
            urn="urn:ddi:fr.sciencespo:ivs-minimal:1.0.0",
            name=[{"value": "Minimal IVS"}],
        )
        assert ivs.description == []
        assert not hasattr(ivs, "hashes")
        iv = InstanceVariable.objects.create(
            urn="urn:ddi:fr.sciencespo:iv-minimal:1.0.0",
            name=[{"value": "Minimal IV"}],
        )
        assert iv.scheme is None
        assert iv.represented_variable is None
        assert iv.label == []
        assert iv.description == []
        assert hasattr(iv, "hashes")

        # 11. Instrument
        inst = Instrument.objects.create(
            urn="urn:ddi:fr.sciencespo:inst-minimal:1.0.0",
            name=[{"value": "Minimal Instrument"}],
        )
        assert inst.label == []
        assert inst.description == []
        assert inst.extended_attributes == []
        assert hasattr(inst, "hashes")

        # 12. UrnRegistry
        reg_min = UrnRegistry.objects.create(
            urn="urn:ddi:fr.sciencespo:min-reg:1.0.0",
            resource_type="Unknown",
        )
        assert reg_min.extended_attributes == []
