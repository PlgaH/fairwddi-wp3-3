"""Tests for FAIRwDDI Django ORM models, relationships, and constraints."""

import pytest
from django.db import IntegrityError
from django.test import TestCase

from fairwddi.models import (
    Category,
    CategoryScheme,
    CategorySchemeItem,
    Code,
    CodeList,
    Collection,
    Concept,
    ConceptualVariable,
    Distributor,
    InstanceVariable,
    MetadataQuarantine,
    QuestionGroup,
    QuestionGroupItem,
    QuestionItem,
    RepresentedVariable,
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
        )
        self.subcollection = Subcollection.objects.create(
            collection=self.collection,
            name="Vagues 2007",
            urn="urn:ddi:fr.sciencespo:BPF_2007:1.0.0",
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

    def test_concept_layer_and_skos_hierarchy(self) -> None:
        """Test Concept, hierarchy, SKOS relationships, and ConceptualVariable."""
        parent_concept = Concept.objects.create(
            uri="https://elsst.cessda.eu/id/4/Politics",
            vocabulary="ELSST",
            notation="POL",
            label=[{"lang": "fr", "value": "Politique"}, {"lang": "en", "value": "Politics"}],
            definition=[{"lang": "fr", "value": "Affaires politiques et gouvernance"}],
            concept_type="domain",
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

        # ConceptualVariable with URN PK
        cv = ConceptualVariable.objects.create(
            concept=child_concept,
            urn="urn:ddi:fr.sciencespo:cv-fr-001:1.0.0",
            label=[{"lang": "fr", "value": "Intérêt pour la politique"}],
            description=[{"lang": "fr", "value": "Mesure du niveau d'intérêt politique"}],
            content_hash="abc111",
            content_hashes={"v1_strict_sha256": "abc111"},
        )
        assert cv.pk == "urn:ddi:fr.sciencespo:cv-fr-001:1.0.0"
        assert cv.concept == child_concept
        assert cv.content_hashes["v1_strict_sha256"] == "abc111"

    def test_representation_layer(self) -> None:
        """Test QuestionItem, QuestionGroup, CategoryScheme, CodeList, and RepresentedVariable."""
        # QuestionItem
        qi = QuestionItem.objects.create(
            urn="urn:ddi:fr.sciencespo:qi-fr-001:1.0.0",
            question_text=[
                {"lang": "fr", "value": "Diriez-vous que vous vous intéressez à la politique ?"},
                {"lang": "en", "value": "Would you say you are interested in politics?"},
            ],
            interviewer_instructions=[{"lang": "fr", "value": "Lire les options de réponse."}],
            content_hash="qi_hash_001",
        )
        assert qi.pk == "urn:ddi:fr.sciencespo:qi-fr-001:1.0.0"
        assert qi.question_text[0]["lang"] == "fr"

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

        # Categories
        cat_yes = Category.objects.create(
            urn="urn:ddi:fr.sciencespo:cat-fr-yes:1.0.0",
            label=[{"lang": "fr", "value": "Oui, beaucoup"}, {"lang": "en", "value": "Yes, a lot"}],
            content_hash="cat_yes_hash",
        )
        cat_no = Category.objects.create(
            urn="urn:ddi:fr.sciencespo:cat-fr-no:1.0.0",
            label=[
                {"lang": "fr", "value": "Non, pas du tout"},
                {"lang": "en", "value": "No, not at all"},
            ],
            content_hash="cat_no_hash",
        )

        # CategoryScheme & Items
        cat_scheme = CategoryScheme.objects.create(
            urn="urn:ddi:fr.sciencespo:cs-fr-interest:1.0.0",
            name=[{"lang": "fr", "value": "Échelle d'intérêt politique"}],
            content_hash="cs_hash_001",
        )
        CategorySchemeItem.objects.create(category_scheme=cat_scheme, category=cat_yes, order=1)
        CategorySchemeItem.objects.create(category_scheme=cat_scheme, category=cat_no, order=2)
        assert cat_scheme.items.count() == 2

        # CodeList & Codes
        code_list = CodeList.objects.create(
            urn="urn:ddi:fr.sciencespo:cl-fr-001:1.0.0",
            name=[{"lang": "fr", "value": "Codes intérêt"}],
            category_scheme=cat_scheme,
            content_hash="cl_hash_001",
        )
        Code.objects.create(code_list=code_list, category=cat_yes, code_value="1", order=1)
        Code.objects.create(code_list=code_list, category=cat_no, code_value="2", order=2)
        assert code_list.codes.count() == 2

        # ConceptualVariable for link
        cv = ConceptualVariable.objects.create(
            urn="urn:ddi:fr.sciencespo:cv-002:1.0.0",
            label=[{"lang": "fr", "value": "Intérêt politique"}],
        )

        # RepresentedVariable
        rv = RepresentedVariable.objects.create(
            conceptual_variable=cv,
            question_item=qi,
            code_list=code_list,
            urn="urn:ddi:fr.sciencespo:rv-fr-001:1.0.0",
            label=[{"lang": "fr", "value": "Intérêt politique RV"}],
            content_hash="rv_hash_001",
        )
        assert rv.question_item == qi
        assert rv.code_list == code_list
        assert rv.conceptual_variable == cv

    def test_code_unique_constraint(self) -> None:
        """Test unique constraint on Code (code_list, code_value)."""
        cat = Category.objects.create(
            urn="urn:ddi:fr.sciencespo:cat-unique-test:1.0.0",
            label=[{"lang": "fr", "value": "Test"}],
        )
        code_list = CodeList.objects.create(
            urn="urn:ddi:fr.sciencespo:cl-unique-test:1.0.0",
            name=[{"lang": "fr", "value": "Test List"}],
        )
        Code.objects.create(code_list=code_list, category=cat, code_value="1")
        with pytest.raises(IntegrityError):
            Code.objects.create(code_list=code_list, category=cat, code_value="1")

    def test_dataset_layer_and_cascade(self) -> None:
        """Test StudyUnit, InstanceVariable, StudyUnitVariable, and DDI Variable Cascade."""
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
        qi = QuestionItem.objects.create(
            urn="urn:ddi:fr.sciencespo:qi-cascade:1.0.0",
            question_text=[{"lang": "fr", "value": "Question"}],
        )
        rv = RepresentedVariable.objects.create(
            urn="urn:ddi:fr.sciencespo:rv-cascade:1.0.0",
            conceptual_variable=cv,
            question_item=qi,
        )

        iv = InstanceVariable.objects.create(
            study_unit=study_unit,
            represented_variable=rv,
            variable_name="q01a",
            universe=[{"lang": "fr", "value": "Ensemble des électeurs inscrits"}],
            notes=[{"lang": "fr", "value": "Variable filtrée"}],
            urn="urn:ddi:fr.sciencespo:iv-fr-bpf2007-q01a:1.0.0",
        )
        assert iv.pk == "urn:ddi:fr.sciencespo:iv-fr-bpf2007-q01a:1.0.0"
        assert iv.variable_name == "q01a"
        assert iv.represented_variable.conceptual_variable == cv

        # StudyUnitVariable mapping
        su_var = StudyUnitVariable.objects.create(
            study_unit=study_unit,
            instance_variable=iv,
            order=1,
        )
        assert study_unit.study_unit_variables.count() == 1
        assert su_var.instance_variable == iv

        # Test unique constraint (study_unit, variable_name)
        with pytest.raises(IntegrityError):
            InstanceVariable.objects.create(
                study_unit=study_unit,
                represented_variable=rv,
                variable_name="q01a",
                urn="urn:ddi:fr.sciencespo:iv-duplicate-test:1.0.0",
            )

    def test_auto_urn_generation_fallback(self) -> None:
        """Test that models inheriting DDIIdentifiable auto-generate canonical URN when omitted."""
        cat = Category.objects.create(
            label=[{"lang": "fr", "value": "Auto Generated Category"}],
        )
        assert cat.urn is not None
        assert cat.urn.startswith("urn:ddi:fr.sciencespo:Category-")
        assert cat.pk == cat.urn
        assert cat.agency == "fr.sciencespo"
        assert cat.version == "1.0.0"

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
