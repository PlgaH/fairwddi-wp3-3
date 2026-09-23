"""Database seeder for FAIRwDDI.

Populates the database with multilingual DDI model sample data (DDI 4 / DDI-CDI / DDI-L 3.3)
across all architectural layers using standard canonical DDI 3.3 / 4.0 URNs.
"""

from __future__ import annotations

import os
from typing import Any


def seed_sample_data(reset: bool = False) -> dict[str, int]:
    """Seed the database with standard DDI model demonstration entities.

    If reset is True, clears existing records first.
    Returns a summary dictionary of created entity counts.
    """
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
        EventLog,
        InstanceVariable,
        Instrument,
        InstrumentQuestion,
        QuestionGroup,
        QuestionGroupItem,
        QuestionItem,
        QuestionVariable,
        RepresentedVariable,
        StagedImport,
        StagedResourceNode,
        StudyUnit,
        StudyUnitVariable,
        Subcollection,
        URNAlias,
    )

    if reset:
        from fairwddi.db.wipe import wipe_database

        wipe_database()

    agency = os.getenv("DDI_AGENCY", "fr.sciencespo")

    # -------------------------------------------------------------------------
    # 1. Organizational Hierarchy
    # -------------------------------------------------------------------------
    distributor, _ = Distributor.objects.get_or_create(
        name="Centre de Données Socio-Politiques (CDSP)",
    )

    collection, _ = Collection.objects.get_or_create(
        urn=f"urn:ddi:{agency}:BPF:1.0.0",
        defaults={
            "distributor": distributor,
            "name": "Baromètre Politique Français (BPF)",
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
            "hashes": {"sha256": "hash_coll_bpf_001"},
        },
    )

    subcollection, _ = Subcollection.objects.get_or_create(
        urn=f"urn:ddi:{agency}:BPF_2007:1.0.0",
        defaults={
            "collection": collection,
            "name": "BPF 2007 (Vagues Électorales)",
            "hashes": {"sha256": "hash_subcoll_bpf_2007"},
        },
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
            "extended_attributes": [{"type": "scope_note", "value": "CESSDA Core Concept"}],
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

    cv_interest, _ = ConceptualVariable.objects.get_or_create(
        urn=f"urn:ddi:{agency}:cv-political-interest:1.0.0",
        defaults={
            "concept": sub_concept,
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
            "hashes": {"sha256": "hash_cv_interest_001"},
            "extended_attributes": [{"type": "variable_type", "value": "attitudinal"}],
        },
    )

    # -------------------------------------------------------------------------
    # 3. Representation Layer & Instruments
    # -------------------------------------------------------------------------
    qi_interest, _ = QuestionItem.objects.get_or_create(
        urn=f"urn:ddi:{agency}:qi-fr-interest-pol:1.0.0",
        defaults={
            "question_text": [
                {
                    "lang": "fr",
                    "value": (
                        "De façon générale, diriez-vous que vous vous intéressez à la politique ?"
                    ),
                },
                {
                    "lang": "en",
                    "value": "Generally speaking, would you say you are interested in politics?",
                },
            ],
            "hashes": {"sha256": "qi_hash_pol_interest_001"},
            "extended_attributes": [
                {
                    "type": "pre_question_text",
                    "value": [
                        {
                            "lang": "fr",
                            "value": (
                                "Passons maintenant à quelques questions sur votre "
                                "perception de la politique."
                            ),
                        }
                    ],
                },
                {
                    "type": "interviewer_instructions",
                    "value": [
                        {"lang": "fr", "value": "Lire les modalités de réponse si nécessaire."}
                    ],
                },
            ],
        },
    )

    # Question Group
    qg_politics, _ = QuestionGroup.objects.get_or_create(
        urn=f"urn:ddi:{agency}:qg-politics-core:1.0.0",
        defaults={
            "label": [
                {"lang": "fr", "value": "Module d'intérêt politique"},
                {"lang": "en", "value": "Political Interest Core Module"},
            ],
            "description": [{"lang": "fr", "value": "Questions relatives à l'attention politique"}],
            "hashes": {"sha256": "qg_hash_politics_001"},
        },
    )
    QuestionGroupItem.objects.get_or_create(
        question_group=qg_politics,
        question_item=qi_interest,
        defaults={"order": 1},
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
            urn=f"urn:ddi:{agency}:{cat_def['id_str']}:1.0.0",
            defaults={
                "label": [
                    {"lang": "fr", "value": cat_def["fr"]},
                    {"lang": "en", "value": cat_def["en"]},
                ],
                "hashes": {"sha256": f"hash_{cat_def['id_str']}"},
            },
        )
        categories[cat_def["id_str"]] = cat

    # CategoryScheme
    cat_scheme, _ = CategoryScheme.objects.get_or_create(
        urn=f"urn:ddi:{agency}:cs-interest-4pt:1.0.0",
        defaults={
            "name": [{"lang": "fr", "value": "Échelle d'intérêt à 4 niveaux"}],
            "description": [{"lang": "fr", "value": "Beaucoup, assez, un peu, pas du tout"}],
            "hashes": {"sha256": "cs_hash_interest_4pt"},
        },
    )
    for idx, key in enumerate(
        ["cat-pol-beaucoup", "cat-pol-assez", "cat-pol-un-peu", "cat-pol-pas-du-tout"], start=1
    ):
        CategorySchemeItem.objects.get_or_create(
            category_scheme=cat_scheme,
            category=categories[key],
            defaults={"order": idx},
        )

    # CodeList & Codes
    code_list, _ = CodeList.objects.get_or_create(
        urn=f"urn:ddi:{agency}:cl-interest-4pt:1.0.0",
        defaults={
            "name": [{"lang": "fr", "value": "Codes échelle intérêt politique (1-4, 88, 99)"}],
            "category_scheme": cat_scheme,
            "hashes": {"sha256": "cl_hash_interest_4pt"},
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
        Code.objects.get_or_create(
            code_list=code_list,
            code_value=val,
            defaults={"category": categories[cat_key], "order": ord_val},
        )

    # RepresentedVariable
    rv_interest, _ = RepresentedVariable.objects.get_or_create(
        urn=f"urn:ddi:{agency}:rv-fr-political-interest:1.0.0",
        defaults={
            "conceptual_variable": cv_interest,
            "code_list": code_list,
            "label": [{"lang": "fr", "value": "Intérêt politique (échelle 4 pts)"}],
            "hashes": {"sha256": "rv_hash_pol_interest_001"},
        },
    )

    # QuestionVariable junction
    QuestionVariable.objects.get_or_create(
        question_item=qi_interest,
        represented_variable=rv_interest,
        defaults={"path": "/RepresentedVariable/QuestionItem", "order": 1},
    )

    # Instrument & InstrumentQuestion
    instrument, _ = Instrument.objects.get_or_create(
        urn=f"urn:ddi:{agency}:inst-bpf-2007:1.0.0",
        defaults={
            "name": [{"lang": "fr", "value": "Questionnaire BPF 2007 Vague 1"}],
            "label": [{"lang": "fr", "value": "Questionnaire Principal BPF 2007"}],
            "description": [{"lang": "fr", "value": "Questionnaire administré en face-à-face."}],
            "hashes": {"sha256": "inst_hash_bpf_2007"},
        },
    )
    InstrumentQuestion.objects.get_or_create(
        instrument=instrument,
        question_item=qi_interest,
        path="/Instrument/Sequence/POL_MODULE/Q01",
        defaults={"order": 1},
    )

    # -------------------------------------------------------------------------
    # 4. Dataset Layer (StudyUnit & InstanceVariables)
    # -------------------------------------------------------------------------
    study_wave1, _ = StudyUnit.objects.get_or_create(
        urn=f"urn:ddi:{agency}:bpf-2007-w01:1.0.0",
        defaults={
            "subcollection": subcollection,
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
            "hashes": {"sha256": "su_hash_bpf_w01"},
        },
    )

    study_wave2, _ = StudyUnit.objects.get_or_create(
        urn=f"urn:ddi:{agency}:bpf-2007-w02:1.0.0",
        defaults={
            "subcollection": subcollection,
            "title": [
                {"lang": "fr", "value": "Baromètre Politique Français - Vague 2 (Avril 2007)"},
                {"lang": "en", "value": "French Political Barometer - Wave 2 (April 2007)"},
            ],
            "external_ref": "10.7303/cdsp-bpf2007-w02",
            "year": 2007,
            "description": [
                {"lang": "fr", "value": "Enquête post-premier tour présidentielle 2007."}
            ],
            "hashes": {"sha256": "su_hash_bpf_w02"},
        },
    )

    # Harmonized InstanceVariables instantiated across study waves
    iv_w1_q01, _ = InstanceVariable.objects.get_or_create(
        urn=f"urn:ddi:{agency}:bpf-2007-w01-q01:1.0.0",
        defaults={
            "represented_variable": rv_interest,
            "name": "q01_pol_interest",
            "label": [{"lang": "fr", "value": "Intérêt pour la politique (Vague 1)"}],
            "extended_attributes": [
                {"type": "universe", "value": "Ensemble des électeurs inscrits"},
                {"type": "notes", "value": "Variable administrée en début de questionnaire"},
            ],
            "hashes": {"sha256": "iv_hash_w1_q01"},
        },
    )

    iv_w2_q01, _ = InstanceVariable.objects.get_or_create(
        urn=f"urn:ddi:{agency}:bpf-2007-w02-q01:1.0.0",
        defaults={
            "represented_variable": rv_interest,
            "name": "q01_pol_interest",
            "label": [{"lang": "fr", "value": "Intérêt pour la politique (Vague 2)"}],
            "extended_attributes": [
                {"type": "universe", "value": "Ensemble des électeurs inscrits"},
                {"type": "notes", "value": "Variable répétée à l'identique de la Vague 1"},
            ],
            "hashes": {"sha256": "iv_hash_w2_q01"},
        },
    )

    # StudyUnit to Variable relationship mapping with path
    StudyUnitVariable.objects.get_or_create(
        study_unit=study_wave1,
        instance_variable=iv_w1_q01,
        defaults={"path": "/StudyUnit/DataPipeline/q01_pol_interest", "order": 1},
    )
    StudyUnitVariable.objects.get_or_create(
        study_unit=study_wave2,
        instance_variable=iv_w2_q01,
        defaults={"path": "/StudyUnit/DataPipeline/q01_pol_interest", "order": 1},
    )

    # -------------------------------------------------------------------------
    # 5. Infrastructure, Provenance, Staging & Event Logging
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

    staged_import, _ = StagedImport.objects.get_or_create(
        file_name="ddi_l_4_closer_sample.json",
        defaults={
            "source_format": "ddi-l:4.0:json",
            "status": "staged",
            "import_options": {
                "source_system": "CLOSER",
                "target_agency": agency,
            },
            "total_resources": 1,
            "processed_resources": 0,
        },
    )

    StagedResourceNode.objects.get_or_create(
        staged_import=staged_import,
        raw_urn="urn:closer:raw:item-001",
        defaults={
            "resource_type": "QuestionItem",
            "raw_value": {
                "question_text": [{"lang": "en", "value": "Are you interested in politics?"}]
            },
            "status": "staged",
        },
    )

    EventLog.objects.get_or_create(
        urn=rv_interest.urn,
        event_type="seeded",
        defaults={
            "event_data": {
                "action": "initial_seed",
                "agency": agency,
                "author": "system",
            }
        },
    )

    return {
        "distributors": Distributor.objects.count(),
        "collections": Collection.objects.count(),
        "subcollections": Subcollection.objects.count(),
        "concepts": Concept.objects.count(),
        "conceptual_variables": ConceptualVariable.objects.count(),
        "question_items": QuestionItem.objects.count(),
        "question_groups": QuestionGroup.objects.count(),
        "question_group_items": QuestionGroupItem.objects.count(),
        "question_variables": QuestionVariable.objects.count(),
        "instruments": Instrument.objects.count(),
        "instrument_questions": InstrumentQuestion.objects.count(),
        "categories": Category.objects.count(),
        "category_schemes": CategoryScheme.objects.count(),
        "category_scheme_items": CategorySchemeItem.objects.count(),
        "code_lists": CodeList.objects.count(),
        "codes": Code.objects.count(),
        "represented_variables": RepresentedVariable.objects.count(),
        "study_units": StudyUnit.objects.count(),
        "instance_variables": InstanceVariable.objects.count(),
        "study_unit_variables": StudyUnitVariable.objects.count(),
        "urn_aliases": URNAlias.objects.count(),
        "staged_nodes": StagedResourceNode.objects.count(),
        "event_logs": EventLog.objects.count(),
    }
