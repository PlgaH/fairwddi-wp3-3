"""Database seeder for FAIRwDDI.

Populates the database with realistic multilingual DDI model sample data (DDI 4 / DDI-CDI / DDI-L)
across all 6 architectural layers.
"""

from __future__ import annotations

from typing import Any


def seed_sample_data(reset: bool = False) -> dict[str, int]:
    """Seed the database with standard DDI model demonstration entities.

    If reset is True, clears existing records first.
    Returns a summary dictionary of created entity counts.
    """
    from fairwddi.models import (
        Category,
        CategorySet,
        CategorySetItem,
        CodeItem,
        CodeList,
        Collection,
        Concept,
        ConceptRelationship,
        ConceptualVariable,
        Distributor,
        InstanceVariable,
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

    if reset:
        from fairwddi.db.wipe import wipe_database

        wipe_database()

    # -------------------------------------------------------------------------
    # 1. Organizational Hierarchy
    # -------------------------------------------------------------------------
    distributor, _ = Distributor.objects.get_or_create(
        name="Centre de Données Socio-Politiques (CDSP)",
    )

    collection, _ = Collection.objects.get_or_create(
        distributor=distributor,
        name="Baromètre Politique Français (BPF)",
        defaults={
            "description": [
                {
                    "lang": "fr",
                    "value": (
                        "Série d'enquêtes électorales et politiques françaises menées par le CDSP."
                    ),
                },
                {
                    "lang": "en",
                    "value": "French political barometer survey series conducted by CDSP.",
                },
            ],
            "urn": "urn:ddi:fr.cdsp:Group:BPF:1.0",
        },
    )

    subcollection, _ = Subcollection.objects.get_or_create(
        collection=collection,
        name="BPF 2007 (Vagues Électorales)",
        defaults={"urn": "urn:ddi:fr.cdsp:SubGroup:BPF_2007:1.0"},
    )

    # -------------------------------------------------------------------------
    # 2. Concept Layer (Controlled Vocabularies & Thesauri)
    # -------------------------------------------------------------------------
    root_concept, _ = Concept.objects.get_or_create(
        uri="https://elsst.cessda.eu/id/4/Politics",
        defaults={
            "vocabulary": "ELSST",
            "notation": "POL",
            "concept_type": "domain",
            "label": [
                {"lang": "fr", "value": "Politique"},
                {"lang": "en", "value": "Politics"},
            ],
            "description": [
                {
                    "lang": "fr",
                    "value": "Affaires politiques, gouvernement et institutions.",
                }
            ],
        },
    )

    sub_concept, _ = Concept.objects.get_or_create(
        uri="https://elsst.cessda.eu/id/4/PoliticalAttitudes",
        defaults={
            "vocabulary": "ELSST",
            "notation": "POL.ATT",
            "concept_type": "concept",
            "parent": root_concept,
            "label": [
                {"lang": "fr", "value": "Attitudes et comportements politiques"},
                {"lang": "en", "value": "Political attitudes and behavior"},
            ],
            "definition": [
                {
                    "lang": "fr",
                    "value": (
                        "Dispositions, orientations et opinions citoyennes "
                        "envers le système politique."
                    ),
                }
            ],
        },
    )

    ConceptRelationship.objects.get_or_create(
        source_concept=sub_concept,
        target_concept=root_concept,
        relationship_type="broader",
    )

    hash_example = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    cv_interest, _ = ConceptualVariable.objects.get_or_create(
        urn="urn:ddi:fr.cdsp:ConceptualVariable:cv-political-interest:1.0.0",
        defaults={
            "concept": sub_concept,
            "agency": "fr.cdsp",
            "ddi_identifier": "cv-political-interest",
            "version": "1.0.0",
            "label": [
                {"lang": "fr", "value": "Intérêt pour la politique"},
                {"lang": "en", "value": "Interest in politics"},
            ],
            "description": [
                {
                    "lang": "fr",
                    "value": "Mesure du niveau d'intérêt subjectif pour les questions politiques.",
                }
            ],
            "content_hash": hash_example,
            "content_hashes": {"v1_strict_sha256": hash_example},
        },
    )

    ConceptualVariable.objects.get_or_create(
        urn="urn:ddi:fr.cdsp:ConceptualVariable:cv-left-right-placement:1.0.0",
        defaults={
            "concept": sub_concept,
            "agency": "fr.cdsp",
            "ddi_identifier": "cv-left-right-placement",
            "version": "1.0.0",
            "label": [
                {"lang": "fr", "value": "Auto-positionnement gauche-droite"},
                {"lang": "en", "value": "Left-right political self-placement"},
            ],
            "description": [
                {"lang": "fr", "value": "Positionnement idéologique sur une échelle gauche-droite."}
            ],
            "content_hash": "a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef0",
        },
    )

    # -------------------------------------------------------------------------
    # 3. Representation Layer
    # -------------------------------------------------------------------------
    # Question Items
    qi_interest, _ = QuestionItem.objects.get_or_create(
        urn="urn:ddi:fr.cdsp:QuestionItem:qi-fr-interest-pol:1.0.0",
        defaults={
            "agency": "fr.cdsp",
            "ddi_identifier": "qi-fr-interest-pol",
            "version": "1.0.0",
            "question_text": [
                {
                    "lang": "fr",
                    "value": "Diriez-vous que vous vous intéressez à la politique ?",
                    "type": "literal",
                },
                {
                    "lang": "en",
                    "value": "Personally, would you say you are interested in politics?",
                    "type": "literal",
                    "translated": True,
                },
            ],
            "pre_question_text": [
                {
                    "lang": "fr",
                    "value": "Passons à quelques questions sur votre regard sur la vie publique.",
                }
            ],
            "interviewer_instructions": [
                {
                    "lang": "fr",
                    "value": "Lire les modalités si nécessaire. Une seule réponse possible.",
                }
            ],
            "content_hash": "1111111122222222333333334444444455555555666666667777777788888888",
        },
    )

    # Categories
    cat_defs: list[dict[str, Any]] = [
        {"id_str": "cat-pol-beaucoup", "fr": "Beaucoup", "en": "A lot"},
        {"id_str": "cat-pol-assez", "fr": "Assez", "en": "Somewhat"},
        {"id_str": "cat-pol-un-peu", "fr": "Un peu", "en": "A little"},
        {"id_str": "cat-pol-pas-du-tout", "fr": "Pas du tout", "en": "Not at all"},
        {"id_str": "cat-nsp", "fr": "Ne sait pas (NSP)", "en": "Don't know"},
        {"id_str": "cat-refus", "fr": "Refus de répondre", "en": "Refused"},
    ]

    categories: dict[str, Category] = {}
    for cat_def in cat_defs:
        cat, _ = Category.objects.get_or_create(
            urn=f"urn:ddi:fr.cdsp:Category:{cat_def['id_str']}:1.0.0",
            defaults={
                "agency": "fr.cdsp",
                "ddi_identifier": cat_def["id_str"],
                "version": "1.0.0",
                "label": [
                    {"lang": "fr", "value": cat_def["fr"]},
                    {"lang": "en", "value": cat_def["en"]},
                ],
                "content_hash": f"hash_{cat_def['id_str']}",
            },
        )
        categories[cat_def["id_str"]] = cat

    # CategorySet (4-point scale + missing)
    cat_set, _ = CategorySet.objects.get_or_create(
        urn="urn:ddi:fr.cdsp:CategorySet:cs-interest-4pt:1.0.0",
        defaults={
            "agency": "fr.cdsp",
            "ddi_identifier": "cs-interest-4pt",
            "name": [{"lang": "fr", "value": "Échelle d'intérêt à 4 niveaux"}],
            "description": [{"lang": "fr", "value": "Beaucoup, assez, un peu, pas du tout"}],
            "content_hash": "cs_hash_interest_4pt",
        },
    )
    for idx, key in enumerate(
        ["cat-pol-beaucoup", "cat-pol-assez", "cat-pol-un-peu", "cat-pol-pas-du-tout"], start=1
    ):
        CategorySetItem.objects.get_or_create(
            category_set=cat_set,
            category=categories[key],
            defaults={"order": idx},
        )

    # CodeList & CodeItems
    code_list, _ = CodeList.objects.get_or_create(
        urn="urn:ddi:fr.cdsp:CodeList:cl-interest-4pt:1.0.0",
        defaults={
            "agency": "fr.cdsp",
            "ddi_identifier": "cl-interest-4pt",
            "name": [{"lang": "fr", "value": "Codes échelle intérêt politique (1-4, 88, 99)"}],
            "category_set": cat_set,
            "content_hash": "cl_hash_interest_4pt",
        },
    )

    code_mappings = [
        ("1", "cat-pol-beaucoup", 1),
        ("2", "cat-pol-assez", 2),
        ("3", "cat-pol-un-peu", 3),
        ("4", "cat-pol-pas-du-tout", 4),
        ("88", "cat-nsp", 5),
        ("99", "cat-refus", 6),
    ]
    for val, cat_key, ord_val in code_mappings:
        CodeItem.objects.get_or_create(
            code_list=code_list,
            code_value=val,
            defaults={"category": categories[cat_key], "order": ord_val},
        )

    # RepresentedVariable
    rv_interest, _ = RepresentedVariable.objects.get_or_create(
        urn="urn:ddi:fr.cdsp:RepresentedVariable:rv-fr-political-interest:1.0.0",
        defaults={
            "agency": "fr.cdsp",
            "ddi_identifier": "rv-fr-political-interest",
            "conceptual_variable": cv_interest,
            "question_item": qi_interest,
            "code_list": code_list,
            "label": [{"lang": "fr", "value": "Intérêt politique (échelle 4 pts)"}],
            "content_hash": "rv_hash_pol_interest_001",
        },
    )

    # -------------------------------------------------------------------------
    # 4. Dataset Layer (StudyUnit & InstanceVariables)
    # -------------------------------------------------------------------------
    study_wave1, _ = StudyUnit.objects.get_or_create(
        urn="urn:ddi:fr.cdsp:StudyUnit:bpf-2007-w01:1.0.0",
        defaults={
            "subcollection": subcollection,
            "agency": "fr.cdsp",
            "ddi_identifier": "bpf-2007-w01",
            "title": [
                {"lang": "fr", "value": "Baromètre Politique Français - Vague 1 (Mars 2007)"},
                {"lang": "en", "value": "French Political Barometer - Wave 1 (March 2007)"},
            ],
            "external_ref": "10.7303/cdsp-bpf2007-w01",
            "year": 2007,
            "description": [
                {
                    "lang": "fr",
                    "value": "Enquête pré-électorale présidentielle (échantillon 4000 électeurs).",
                }
            ],
        },
    )

    study_wave2, _ = StudyUnit.objects.get_or_create(
        urn="urn:ddi:fr.cdsp:StudyUnit:bpf-2007-w02:1.0.0",
        defaults={
            "subcollection": subcollection,
            "agency": "fr.cdsp",
            "ddi_identifier": "bpf-2007-w02",
            "title": [
                {"lang": "fr", "value": "Baromètre Politique Français - Vague 2 (Avril 2007)"},
                {"lang": "en", "value": "French Political Barometer - Wave 2 (April 2007)"},
            ],
            "external_ref": "10.7303/cdsp-bpf2007-w02",
            "year": 2007,
            "description": [
                {"lang": "fr", "value": "Enquête post-premier tour présidentielle 2007."}
            ],
        },
    )

    # Harmonized InstanceVariables instantiated across both study waves
    iv_w1_q01, _ = InstanceVariable.objects.get_or_create(
        study_unit=study_wave1,
        variable_name="q01_pol_interest",
        defaults={
            "urn": "urn:ddi:fr.cdsp:InstanceVariable:bpf-2007-w01-q01:1.0.0",
            "agency": "fr.cdsp",
            "ddi_identifier": "bpf-2007-w01-q01",
            "represented_variable": rv_interest,
            "universe": [{"lang": "fr", "value": "Ensemble des électeurs inscrits"}],
            "notes": [{"lang": "fr", "value": "Variable administrée en début de questionnaire"}],
            "is_indexed": True,
        },
    )

    InstanceVariable.objects.get_or_create(
        study_unit=study_wave2,
        variable_name="q01_pol_interest",
        defaults={
            "urn": "urn:ddi:fr.cdsp:InstanceVariable:bpf-2007-w02-q01:1.0.0",
            "agency": "fr.cdsp",
            "ddi_identifier": "bpf-2007-w02-q01",
            "represented_variable": rv_interest,
            "universe": [{"lang": "fr", "value": "Ensemble des électeurs inscrits"}],
            "notes": [{"lang": "fr", "value": "Variable répétée à l'identique de la Vague 1"}],
            "is_indexed": True,
        },
    )

    # -------------------------------------------------------------------------
    # 5. Grouping Layer
    # -------------------------------------------------------------------------
    var_group, _ = VariableGroup.objects.get_or_create(
        study_unit=study_wave1,
        urn="urn:ddi:fr.cdsp:VariableGroup:vg-pol-attitudes:1.0.0",
        defaults={
            "agency": "fr.cdsp",
            "ddi_identifier": "vg-pol-attitudes",
            "label": [
                {"lang": "fr", "value": "Attitudes et engagement politique"},
                {"lang": "en", "value": "Political Attitudes and Engagement"},
            ],
            "type_of_group": "Thematic",
            "concept": sub_concept,
        },
    )
    VariableGroupMembership.objects.get_or_create(
        variable_group=var_group,
        instance_variable=iv_w1_q01,
        defaults={"order": 1},
    )

    # -------------------------------------------------------------------------
    # 6. Infrastructure, Provenance, and Staging Layer
    # -------------------------------------------------------------------------
    URNAlias.objects.get_or_create(
        alias_urn="raw:colectica:098f6bcd-4621-3373-8ade-4e832627b4f6:1",
        defaults={
            "canonical_urn": rv_interest.urn,
            "entity_type": "RepresentedVariable",
            "hash_strategy": "v1_strict_sha256",
            "source_file": "bpf_2007_w01_source.xml",
        },
    )

    payload, _ = StagedImportPayload.objects.get_or_create(
        file_name="ddi_l_4_closer_sample.json",
        defaults={
            "source_format": "ddi_l_4_json",
            "status": "staged",
            "raw_payload": {
                "ResourceType": "QuestionItem",
                "Text": "Sample DDI 4 staged question bundle",
            },
        },
    )

    StagedResourceNode.objects.get_or_create(
        import_payload=payload,
        raw_urn="urn:closer:raw:item-001",
        defaults={
            "resource_type": "QuestionItem",
            "raw_value": {
                "question_text": [{"lang": "en", "value": "Are you interested in politics?"}]
            },
            "status": "staged",
        },
    )

    return {
        "distributors": Distributor.objects.count(),
        "collections": Collection.objects.count(),
        "subcollections": Subcollection.objects.count(),
        "concepts": Concept.objects.count(),
        "concept_relationships": ConceptRelationship.objects.count(),
        "conceptual_variables": ConceptualVariable.objects.count(),
        "question_items": QuestionItem.objects.count(),
        "categories": Category.objects.count(),
        "category_sets": CategorySet.objects.count(),
        "code_lists": CodeList.objects.count(),
        "code_items": CodeItem.objects.count(),
        "represented_variables": RepresentedVariable.objects.count(),
        "study_units": StudyUnit.objects.count(),
        "instance_variables": InstanceVariable.objects.count(),
        "variable_groups": VariableGroup.objects.count(),
        "urn_aliases": URNAlias.objects.count(),
        "staged_nodes": StagedResourceNode.objects.count(),
    }
