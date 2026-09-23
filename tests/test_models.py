"""Tests for FAIRwDDI Django ORM models, relationships, and constraints."""

import pytest
from django.test import TestCase

from fairwddi.models import (
    Category,
    CategoryScheme,
    Code,
    CodeList,
    Collection,
    Concept,
    ConceptualVariable,
    Distributor,
    EventLog,
    InstanceVariable,
    Instrument,
    InstrumentQuestion,
    MetadataQuarantine,
    QuestionGroup,
    QuestionGroupItem,
    QuestionItem,
    QuestionVariable,
    RepresentedVariable,
    SemanticRelationship,
    StagedImport,
    StagedResourceNode,
    StudyUnit,
    StudyUnitVariable,
    Subcollection,
    URNAlias,
)


@pytest.mark.django_db
class TestFairwDDIModels(TestCase):
    """Integration test case for all FAIRwDDI models."""

    def setUp(self) -> None:
        """Set up foundational records."""
        self.distributor = Distributor.objects.create(name="CDSP")
        self.collection = Collection.objects.create(
            distributor=self.distributor,
            name="Baromètre Politique Français",
            description=[{"lang": "fr", "value": "Série d'enquêtes électorales"}],
            urn="urn:ddi:fr.sciencespo:BPF:1.0.0",
            hashes={"sha256": "hash_coll_001"},
        )
        self.subcollection = Subcollection.objects.create(
            collection=self.collection,
            name="Vagues 2007",
            urn="urn:ddi:fr.sciencespo:BPF_2007:1.0.0",
            hashes={"sha256": "hash_subcoll_001"},
        )

    def test_organization_hierarchy(self) -> None:
        """Test Distributor -> Collection -> Subcollection hierarchy."""
        assert self.distributor.collections.count() == 1
        assert self.collection.subcollections.count() == 1
        assert str(self.subcollection) == "Baromètre Politique Français - Vagues 2007"
        assert self.collection.pk == "urn:ddi:fr.sciencespo:BPF:1.0.0"
        assert self.subcollection.pk == "urn:ddi:fr.sciencespo:BPF_2007:1.0.0"
        assert self.collection.agency == "fr.sciencespo"
        assert self.collection.identifier == "BPF"
        assert self.collection.version == "1.0.0"
        assert self.collection.hashes["sha256"] == "hash_coll_001"

    def test_concept_layer_and_skos_hierarchy(self) -> None:
        """Test Concept, hierarchy, SKOS relationships, and ConceptualVariable."""
        parent_concept = Concept.objects.create(
            uri="https://elsst.cessda.eu/id/4/Politics",
            vocabulary="ELSST",
            notation="POL",
            label=[{"lang": "fr", "value": "Politique"}, {"lang": "en", "value": "Politics"}],
            definition=[{"lang": "fr", "value": "Affaires politiques et gouvernance"}],
            concept_type="domain",
            extended_attributes=[{"type": "scope", "value": "core"}],
        )
        child_concept = Concept.objects.create(
            uri="https://elsst.cessda.eu/id/4/PoliticalAttitudes",
            vocabulary="ELSST",
            notation="POL.ATT",
            label=[{"lang": "fr", "value": "Attitudes politiques"}],
            parent=parent_concept,
            concept_type="concept",
        )
        assert parent_concept.vocabulary == "ELSST"
        assert parent_concept.narrower_concepts.count() == 1
        assert child_concept.parent == parent_concept
        assert parent_concept.extended_attributes[0]["value"] == "core"

        # ConceptualVariable with URN PK and hashes
        cv = ConceptualVariable.objects.create(
            concept=child_concept,
            urn="urn:ddi:fr.sciencespo:cv-fr-001:1.0.0",
            label=[{"lang": "fr", "value": "Intérêt pour la politique"}],
            description=[{"lang": "fr", "value": "Mesure du niveau d'intérêt politique"}],
            hashes={"sha256": "abc111", "v1_strict": "abc111"},
            extended_attributes=[{"type": "domain", "value": "attitudes"}],
        )
        assert cv.pk == "urn:ddi:fr.sciencespo:cv-fr-001:1.0.0"
        assert cv.concept == child_concept
        assert cv.hashes["sha256"] == "abc111"
        assert cv.extended_attributes[0]["type"] == "domain"

    def test_representation_layer(self) -> None:
        """Test QuestionItem, QuestionGroup, Category & Code hierarchy, and QuestionVariable."""
        # QuestionItem
        qi = QuestionItem.objects.create(
            urn="urn:ddi:fr.sciencespo:qi-fr-001:1.0.0",
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
        assert qi.question_text[0]["lang"] == "fr"
        assert qi.extended_attributes[0]["type"] == "interviewer_instructions"

        # QuestionGroup & QuestionGroupItem
        qg = QuestionGroup.objects.create(
            urn="urn:ddi:fr.sciencespo:qg-pol-interest:1.0.0",
            label=[{"lang": "fr", "value": "Questions d'intérêt"}],
        )
        qg_item = QuestionGroupItem.objects.create(
            question_group=qg,
            question_item=qi,
            order=1,
        )
        assert qg.items.count() == 1
        assert qg_item.question_item == qi

        # CategoryScheme
        cat_scheme = CategoryScheme.objects.create(
            urn="urn:ddi:fr.sciencespo:cs-fr-interest:1.0.0",
            name=[{"lang": "fr", "value": "Échelle d'intérêt politique"}],
            hashes={"sha256": "cs_hash_001"},
        )

        # Categories with parent hierarchy belonging to CategoryScheme
        cat_parent = Category.objects.create(
            urn="urn:ddi:fr.sciencespo:cat-pol-general:1.0.0",
            category_scheme=cat_scheme,
            order=0,
            label=[{"lang": "fr", "value": "Échelle d'accord général"}],
        )
        cat_yes = Category.objects.create(
            urn="urn:ddi:fr.sciencespo:cat-fr-yes:1.0.0",
            category_scheme=cat_scheme,
            order=1,
            label=[{"lang": "fr", "value": "Oui, beaucoup"}, {"lang": "en", "value": "Yes, a lot"}],
            parent=cat_parent,
            hashes={"sha256": "cat_yes_hash"},
        )
        cat_no = Category.objects.create(
            urn="urn:ddi:fr.sciencespo:cat-fr-no:1.0.0",
            category_scheme=cat_scheme,
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
            category_scheme=cat_scheme,
            order=3,
            is_missing=True,
            label=[{"lang": "fr", "value": "Ne sait pas"}],
            hashes={"sha256": "cat_nsp_hash"},
        )
        assert cat_yes.parent == cat_parent
        assert cat_parent.children.count() == 2
        assert cat_scheme.categories.count() == 4
        assert cat_yes.category_scheme == cat_scheme
        assert cat_yes.is_missing is False
        assert cat_nsp.is_missing is True

        # CodeList & Codes with parent hierarchy
        code_list = CodeList.objects.create(
            urn="urn:ddi:fr.sciencespo:cl-fr-001:1.0.0",
            name=[{"lang": "fr", "value": "Codes intérêt"}],
            category_scheme=cat_scheme,
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

        # ConceptualVariable
        cv = ConceptualVariable.objects.create(
            urn="urn:ddi:fr.sciencespo:cv-002:1.0.0",
            label=[{"lang": "fr", "value": "Intérêt politique"}],
        )

        # RepresentedVariable (decoupled from question_item)
        rv = RepresentedVariable.objects.create(
            conceptual_variable=cv,
            code_list=code_list,
            urn="urn:ddi:fr.sciencespo:rv-fr-001:1.0.0",
            label=[{"lang": "fr", "value": "Intérêt politique RV"}],
            hashes={"sha256": "rv_hash_001"},
        )
        assert rv.code_list == code_list
        assert rv.conceptual_variable == cv

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
        """Test StudyUnit, InstanceVariable, StudyUnitVariable with path, and variable cascade."""
        study_unit = StudyUnit.objects.create(
            subcollection=self.subcollection,
            title=[{"lang": "fr", "value": "BPF Vague 1 (2007)"}],
            external_ref="10.7303/cdsp-bpf2007-1",
            year=2007,
            urn="urn:ddi:fr.sciencespo:su-bpf2007-1:1.0.0",
        )

        cv = ConceptualVariable.objects.create(
            urn="urn:ddi:fr.sciencespo:cv-cascade:1.0.0",
            label=[{"lang": "fr", "value": "Concept"}],
        )
        rv = RepresentedVariable.objects.create(
            urn="urn:ddi:fr.sciencespo:rv-cascade:1.0.0",
            conceptual_variable=cv,
        )

        iv = InstanceVariable.objects.create(
            represented_variable=rv,
            name="q01a",
            label=[{"lang": "fr", "value": "Intérêt politique Q1"}],
            extended_attributes=[
                {"type": "universe", "value": "Ensemble des électeurs inscrits"},
                {"type": "notes", "value": "Variable filtrée"},
            ],
            urn="urn:ddi:fr.sciencespo:iv-fr-bpf2007-q01a:1.0.0",
        )
        assert iv.pk == "urn:ddi:fr.sciencespo:iv-fr-bpf2007-q01a:1.0.0"
        assert iv.name == "q01a"
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
