"""Tests for FAIRwDDI Django ORM models, relationships, and constraints."""

import pytest
from django.db import IntegrityError
from django.test import TestCase

from fairwddi.models import (
    Category,
    CategorySet,
    CategorySetItem,
    CodeItem,
    CodeList,
    Collection,
    Concept,
    ConceptualVariable,
    Distributor,
    InstanceVariable,
    MetadataQuarantine,
    QuestionItem,
    RepresentedVariable,
    StagedImportPayload,
    StagedResourceNode,
    StudyUnit,
    Subcollection,
    URNAlias,
    VariableGroup,
    VariableGroupMembership,
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
            urn="urn:ddi:fr.cdsp:Group:BPF:1.0",
        )
        self.subcollection = Subcollection.objects.create(
            collection=self.collection,
            name="Vagues 2007",
            urn="urn:ddi:fr.cdsp:SubGroup:BPF_2007:1.0",
        )

    def test_organization_hierarchy(self) -> None:
        """Test Distributor -> Collection -> Subcollection hierarchy."""
        assert self.distributor.collections.count() == 1
        assert self.collection.subcollections.count() == 1
        assert str(self.subcollection) == "Baromètre Politique Français - Vagues 2007"

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

        # ConceptualVariable
        cv = ConceptualVariable.objects.create(
            concept=child_concept,
            urn="urn:ddi:fr.cdsp:ConceptualVariable:cv-fr-001:1.0.0",
            label=[{"lang": "fr", "value": "Intérêt pour la politique"}],
            description=[{"lang": "fr", "value": "Mesure du niveau d'intérêt politique"}],
            content_hash="abc111",
            content_hashes={"v1_strict_sha256": "abc111"},
        )
        assert cv.concept == child_concept
        assert cv.content_hashes["v1_strict_sha256"] == "abc111"

    def test_representation_layer(self) -> None:
        """Test QuestionItem, Category, CategorySet, CodeList, CodeItem, and RepresentedVariable."""
        # QuestionItem
        qi = QuestionItem.objects.create(
            urn="urn:ddi:fr.cdsp:QuestionItem:qi-fr-001:1.0.0",
            question_text=[
                {"lang": "fr", "value": "Diriez-vous que vous vous intéressez à la politique ?"},
                {"lang": "en", "value": "Would you say you are interested in politics?"},
            ],
            interviewer_instructions=[{"lang": "fr", "value": "Lire les options de réponse."}],
            content_hash="qi_hash_001",
        )
        assert qi.question_text[0]["lang"] == "fr"

        # Categories
        cat_yes = Category.objects.create(
            urn="urn:ddi:fr.cdsp:Category:cat-fr-yes:1.0.0",
            label=[{"lang": "fr", "value": "Oui, beaucoup"}, {"lang": "en", "value": "Yes, a lot"}],
            content_hash="cat_yes_hash",
        )
        cat_no = Category.objects.create(
            urn="urn:ddi:fr.cdsp:Category:cat-fr-no:1.0.0",
            label=[
                {"lang": "fr", "value": "Non, pas du tout"},
                {"lang": "en", "value": "No, not at all"},
            ],
            content_hash="cat_no_hash",
        )

        # CategorySet & Items
        cat_set = CategorySet.objects.create(
            urn="urn:ddi:fr.cdsp:CategorySet:cs-fr-interest:1.0.0",
            name=[{"lang": "fr", "value": "Échelle d'intérêt politique"}],
            content_hash="cs_hash_001",
        )
        CategorySetItem.objects.create(category_set=cat_set, category=cat_yes, order=1)
        CategorySetItem.objects.create(category_set=cat_set, category=cat_no, order=2)
        assert cat_set.items.count() == 2

        # CodeList & CodeItems
        code_list = CodeList.objects.create(
            urn="urn:ddi:fr.cdsp:CodeList:cl-fr-001:1.0.0",
            name=[{"lang": "fr", "value": "Codes intérêt"}],
            category_set=cat_set,
            content_hash="cl_hash_001",
        )
        CodeItem.objects.create(code_list=code_list, category=cat_yes, code_value="1", order=1)
        CodeItem.objects.create(code_list=code_list, category=cat_no, code_value="2", order=2)
        assert code_list.items.count() == 2

        # ConceptualVariable for link
        cv = ConceptualVariable.objects.create(
            urn="urn:ddi:fr.cdsp:ConceptualVariable:cv-002:1.0.0",
            label=[{"lang": "fr", "value": "Intérêt politique"}],
        )

        # RepresentedVariable
        rv = RepresentedVariable.objects.create(
            conceptual_variable=cv,
            question_item=qi,
            code_list=code_list,
            urn="urn:ddi:fr.cdsp:RepresentedVariable:rv-fr-001:1.0.0",
            label=[{"lang": "fr", "value": "Intérêt politique RV"}],
            content_hash="rv_hash_001",
        )
        assert rv.question_item == qi
        assert rv.code_list == code_list

    def test_codeitem_unique_constraint(self) -> None:
        """Test unique constraint on CodeItem (code_list, code_value)."""
        cat = Category.objects.create(
            label=[{"lang": "fr", "value": "Test"}],
        )
        code_list = CodeList.objects.create(
            name=[{"lang": "fr", "value": "Test List"}],
        )
        CodeItem.objects.create(code_list=code_list, category=cat, code_value="1")
        with pytest.raises(IntegrityError):
            CodeItem.objects.create(code_list=code_list, category=cat, code_value="1")

    def test_dataset_layer_and_cascade(self) -> None:
        """Test StudyUnit, InstanceVariable, and DDI Variable Cascade."""
        study_unit = StudyUnit.objects.create(
            subcollection=self.subcollection,
            title=[{"lang": "fr", "value": "BPF Vague 1 (2007)"}],
            external_ref="10.7303/cdsp-bpf2007-1",
            year=2007,
            urn="urn:ddi:fr.cdsp:StudyUnit:su-bpf2007-1:1.0.0",
        )

        cv = ConceptualVariable.objects.create(label=[{"lang": "fr", "value": "Concept"}])
        qi = QuestionItem.objects.create(question_text=[{"lang": "fr", "value": "Question"}])
        rv = RepresentedVariable.objects.create(conceptual_variable=cv, question_item=qi)

        iv = InstanceVariable.objects.create(
            study_unit=study_unit,
            represented_variable=rv,
            variable_name="q01a",
            universe=[{"lang": "fr", "value": "Ensemble des électeurs inscrits"}],
            notes=[{"lang": "fr", "value": "Variable filtrée"}],
            urn="urn:ddi:fr.cdsp:InstanceVariable:iv-fr-bpf2007-q01a:1.0.0",
        )
        assert iv.variable_name == "q01a"
        assert iv.represented_variable.conceptual_variable == cv

        # Test unique constraint (study_unit, variable_name)
        with pytest.raises(IntegrityError):
            InstanceVariable.objects.create(
                study_unit=study_unit,
                represented_variable=rv,
                variable_name="q01a",
            )

    def test_variable_group_and_membership(self) -> None:
        """Test DDI-L VariableGroup with study/series scoping and membership."""
        study_unit = StudyUnit.objects.create(
            subcollection=self.subcollection,
            title=[{"lang": "fr", "value": "Study 2007"}],
        )
        cv = ConceptualVariable.objects.create(label=[{"lang": "fr", "value": "Concept"}])
        qi = QuestionItem.objects.create(question_text=[{"lang": "fr", "value": "Question"}])
        rv = RepresentedVariable.objects.create(conceptual_variable=cv, question_item=qi)
        iv = InstanceVariable.objects.create(
            study_unit=study_unit, represented_variable=rv, variable_name="demo_age"
        )

        vg = VariableGroup.objects.create(
            study_unit=study_unit,
            label=[{"lang": "fr", "value": "Variables socio-démographiques"}],
            type_of_group="Thematic",
            urn="urn:ddi:fr.cdsp:VariableGroup:vg-fr-demo:1.0.0",
        )
        vgm = VariableGroupMembership.objects.create(
            variable_group=vg, instance_variable=iv, order=1
        )
        assert vg.memberships.count() == 1
        assert vgm.instance_variable == iv

    def test_infrastructure_and_staging_layer(self) -> None:
        """Test URNAlias, MetadataQuarantine, StagedImportPayload, and StagedResourceNode."""
        # URNAlias
        alias = URNAlias.objects.create(
            alias_urn="raw:colectica:random-uuid-1234",
            canonical_urn="urn:ddi:fr.cdsp:QuestionItem:qi-fr-001:1.0.0",
            entity_type="QuestionItem",
            hash_strategy="v1_strict_sha256",
            source_file="survey2007.xml",
        )
        assert alias.canonical_urn == "urn:ddi:fr.cdsp:QuestionItem:qi-fr-001:1.0.0"

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

        # StagedImportPayload & StagedResourceNode
        payload = StagedImportPayload.objects.create(
            source_format="ddi_l_4_json",
            file_name="closer_sample.json",
            raw_payload={"type": "bundle", "count": 10},
        )
        node = StagedResourceNode.objects.create(
            import_payload=payload,
            resource_type="QuestionItem",
            raw_urn="urn:closer:qi:999",
            raw_value={"question_text": [{"lang": "en", "value": "Are you employed?"}]},
        )
        assert payload.nodes.count() == 1
        assert node.import_payload == payload
