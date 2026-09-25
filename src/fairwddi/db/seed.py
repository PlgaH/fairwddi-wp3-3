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

    if reset:
        from fairwddi.db.wipe import wipe_database

        wipe_database()

    agency = os.getenv("DDI_AGENCY", "fr.sciencespo")

    # -------------------------------------------------------------------------
    # 1. Organizational Hierarchy
    # -------------------------------------------------------------------------
    organization, _ = Organization.objects.get_or_create(
        urn=f"urn:ddi:{agency}:Organization.CDSP:1.0.0",
        defaults={
            "name": [
                {
                    "lang": "fr",
                    "value": "Centre de Données Socio-Politiques",
                },
                {
                    "lang": "en",
                    "value": "Center for Socio-Political Data",
                },
            ],
            "organization_type": "distributor",
            "extended_attributes": [
                {"type": "acronym", "value": "CDSP"},
                {"type": "uri", "value": "https://cdsp.sciences-po.fr/"},
                {"type": "email", "value": "cdsp@sciencespo.fr"},
            ],
        },
    )

    # Group (e.g. BPF Study Series Group)
    group_bpf, _ = Group.objects.get_or_create(
        urn=f"urn:ddi:{agency}:group-bpf-series:1.0.0",
        defaults={
            "name": [
                {
                    "lang": "fr",
                    "value": "Baromètre Politique Français (BPF)",
                },
                {
                    "lang": "en",
                    "value": "French Political Barometer (BPF)",
                },
            ],
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
            "group_type": "study_series",
            "references": [
                {
                    "resource_type": "StudyUnit",
                    "urn": f"urn:ddi:{agency}:bpf-2007-w01:1.0.0",
                },
                {
                    "resource_type": "StudyUnit",
                    "urn": f"urn:ddi:{agency}:bpf-2007-w02:1.0.0",
                },
            ],
            "hashes": {"sha256": "group_hash_bpf_001"},
        },
    )

    # -------------------------------------------------------------------------
    # 2. Concept Layer (Controlled Vocabularies & Thesauri)
    # -------------------------------------------------------------------------
    concept_scheme, _ = ConceptScheme.objects.get_or_create(
        urn=f"urn:ddi:{agency}:cs-politics-thesaurus:1.0.0",
        defaults={
            "name": [
                {"lang": "fr", "value": "Schéma de concepts politiques"},
                {"lang": "en", "value": "Political Concepts Scheme"},
            ],
            "description": [
                {
                    "lang": "fr",
                    "value": "Concepts et thématiques de science politique basés sur ELSST.",
                }
            ],
        },
    )

    root_concept, _ = Concept.objects.get_or_create(
        urn=f"urn:ddi:{agency}:concept-elsst-pol:1.0.0",
        defaults={
            "scheme": concept_scheme,
            "uri": "https://elsst.cessda.eu/id/4/Politics",
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
            "hashes": {"sha256": "concept_hash_pol"},
            "extended_attributes": [{"type": "scope_note", "value": "CESSDA Core Concept"}],
        },
    )

    sub_concept, _ = Concept.objects.get_or_create(
        urn=f"urn:ddi:{agency}:concept-elsst-pol-att:1.0.0",
        defaults={
            "scheme": concept_scheme,
            "uri": "https://elsst.cessda.eu/id/4/PoliticalAttitudes",
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
            "hashes": {"sha256": "concept_hash_pol_att"},
        },
    )

    cv_scheme, _ = ConceptualVariableScheme.objects.get_or_create(
        urn=f"urn:ddi:{agency}:cvs-attitudes-core:1.0.0",
        defaults={
            "name": [
                {"lang": "fr", "value": "Schéma de variables conceptuelles politiques"},
                {"lang": "en", "value": "Political Conceptual Variables Scheme"},
            ],
            "description": [
                {
                    "lang": "fr",
                    "value": "Variables conceptuelles mesurant les attitudes politiques.",
                }
            ],
        },
    )

    cv_interest, _ = ConceptualVariable.objects.get_or_create(
        urn=f"urn:ddi:{agency}:cv-political-interest:1.0.0",
        defaults={
            "scheme": cv_scheme,
            "concept": sub_concept,
            "name": [
                {"lang": "fr", "value": "INTERET_POLITIQUE"},
                {"lang": "en", "value": "POLITICAL_INTEREST"},
            ],
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
    # QuestionScheme
    qs_politics, _ = QuestionScheme.objects.get_or_create(
        urn=f"urn:ddi:{agency}:qs-politics-core:1.0.0",
        defaults={
            "name": [
                {"lang": "fr", "value": "Schéma de questions politiques"},
                {"lang": "en", "value": "Political Questions Scheme"},
            ],
            "description": [
                {"lang": "fr", "value": "Questions relatives à l'attention et l'intérêt politique"}
            ],
        },
    )

    qi_interest, _ = QuestionItem.objects.get_or_create(
        urn=f"urn:ddi:{agency}:qi-fr-interest-pol:1.0.0",
        defaults={
            "name": [
                {"lang": "fr", "value": "QI_INTERET_POL"},
                {"lang": "en", "value": "QI_POL_INTEREST"},
            ],
            "scheme": qs_politics,
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

    # CategoryScheme
    cat_scheme, _ = CategoryScheme.objects.get_or_create(
        urn=f"urn:ddi:{agency}:cs-interest-4pt:1.0.0",
        defaults={
            "name": [{"lang": "fr", "value": "Échelle d'intérêt à 4 niveaux"}],
            "description": [{"lang": "fr", "value": "Beaucoup, assez, un peu, pas du tout"}],
        },
    )

    # Categories belonging directly to CategoryScheme
    cat_defs: list[dict[str, Any]] = [
        {
            "id_str": "cat-pol-beaucoup",
            "fr": "Beaucoup",
            "en": "A lot",
            "order": 1,
            "is_missing": False,
        },
        {
            "id_str": "cat-pol-assez",
            "fr": "Assez",
            "en": "Somewhat",
            "order": 2,
            "is_missing": False,
        },
        {
            "id_str": "cat-pol-un-peu",
            "fr": "Un peu",
            "en": "A little",
            "order": 3,
            "is_missing": False,
        },
        {
            "id_str": "cat-pol-pas-du-tout",
            "fr": "Pas du tout",
            "en": "Not at all",
            "order": 4,
            "is_missing": False,
        },
        {
            "id_str": "cat-nsp",
            "fr": "Ne sait pas (NSP)",
            "en": "Don't know",
            "order": 5,
            "is_missing": True,
        },
        {
            "id_str": "cat-refus",
            "fr": "Refus de répondre",
            "en": "Refused",
            "order": 6,
            "is_missing": True,
        },
    ]

    categories: dict[str, Category] = {}
    for cat_def in cat_defs:
        cat, _ = Category.objects.get_or_create(
            urn=f"urn:ddi:{agency}:{cat_def['id_str']}:1.0.0",
            defaults={
                "name": [
                    {"lang": "fr", "value": cat_def["fr"]},
                    {"lang": "en", "value": cat_def["en"]},
                ],
                "scheme": cat_scheme,
                "order": cat_def["order"],
                "is_missing": cat_def["is_missing"],
                "label": [
                    {"lang": "fr", "value": cat_def["fr"]},
                    {"lang": "en", "value": cat_def["en"]},
                ],
                "hashes": {"sha256": f"hash_{cat_def['id_str']}"},
            },
        )
        categories[cat_def["id_str"]] = cat

    # CodeList & Codes
    code_list, _ = CodeList.objects.get_or_create(
        urn=f"urn:ddi:{agency}:cl-interest-4pt:1.0.0",
        defaults={
            "name": [{"lang": "fr", "value": "Codes échelle intérêt politique (1-4, 88, 99)"}],
            "scheme": cat_scheme,
            "hashes": {"sha256": "cl_hash_interest_4pt"},
        },
    )

    code_mappings = [
        ("1", "cat-pol-beaucoup", 1, False),
        ("2", "cat-pol-assez", 2, False),
        ("3", "cat-pol-un-peu", 3, False),
        ("4", "cat-pol-pas-du-tout", 4, False),
        ("88", "cat-nsp", 5, True),
        ("99", "cat-refus", 6, True),
    ]
    for val, cat_key, ord_val, is_miss in code_mappings:
        Code.objects.get_or_create(
            code_list=code_list,
            code_value=val,
            defaults={
                "category": categories[cat_key],
                "order": ord_val,
                "is_missing": is_miss,
            },
        )

    # RepresentedVariableScheme
    rv_scheme, _ = RepresentedVariableScheme.objects.get_or_create(
        urn=f"urn:ddi:{agency}:rvs-bpf-core:1.0.0",
        defaults={
            "name": [
                {"lang": "fr", "value": "Schéma de variables représentées"},
                {"lang": "en", "value": "Represented Variables Scheme"},
            ],
            "description": [
                {"lang": "fr", "value": "Variables représentées avec modalités de réponse."}
            ],
        },
    )

    # RepresentedVariable
    rv_interest, _ = RepresentedVariable.objects.get_or_create(
        urn=f"urn:ddi:{agency}:rv-fr-political-interest:1.0.0",
        defaults={
            "scheme": rv_scheme,
            "conceptual_variable": cv_interest,
            "code_list": code_list,
            "value_representation": {
                "type": "code",
                "code_list_urn": code_list.urn,
            },
            "name": [{"lang": "fr", "value": "RV_INTERET_POL_4PT"}],
            "label": [{"lang": "fr", "value": "Intérêt politique (échelle 4 pts)"}],
            "description": [{"lang": "fr", "value": "Mesure de l'intérêt politique (4 pts)."}],
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
            "name": [{"value": "BPF_2007_W1"}],
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
            "name": [{"value": "BPF_2007_W2"}],
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

    # InstanceVariableScheme
    iv_scheme, _ = InstanceVariableScheme.objects.get_or_create(
        urn=f"urn:ddi:{agency}:ivs-bpf-2007:1.0.0",
        defaults={
            "name": [
                {"lang": "fr", "value": "Schéma de variables d'instance BPF 2007"},
                {"lang": "en", "value": "BPF 2007 Instance Variables Scheme"},
            ],
            "description": [
                {"lang": "fr", "value": "Variables physiques des fichiers de données BPF 2007."}
            ],
        },
    )

    # Harmonized InstanceVariables instantiated across study waves
    iv_w1_q01, _ = InstanceVariable.objects.get_or_create(
        urn=f"urn:ddi:{agency}:bpf-2007-w01-q01:1.0.0",
        defaults={
            "scheme": iv_scheme,
            "represented_variable": rv_interest,
            "name": [{"value": "q01_pol_interest"}],
            "label": [{"lang": "fr", "value": "Intérêt pour la politique (Vague 1)"}],
            "description": [
                {"lang": "fr", "value": "Colonne q01_pol_interest dans le fichier SPSS vague 1."}
            ],
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
            "scheme": iv_scheme,
            "represented_variable": rv_interest,
            "name": [{"value": "q01_pol_interest"}],
            "label": [{"lang": "fr", "value": "Intérêt pour la politique (Vague 2)"}],
            "description": [
                {"lang": "fr", "value": "Colonne q01_pol_interest dans le fichier SPSS vague 2."}
            ],
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
    UrnRegistry.objects.get_or_create(
        urn=rv_interest.urn,
        defaults={
            "resource_type": "RepresentedVariable",
            "extended_attributes": [{"type": "source", "value": "seed"}],
        },
    )
    UrnRegistry.objects.get_or_create(
        urn="https://elsst.cessda.eu/id/4/PoliticalAttitudes",
        defaults={
            "resource_type": "Concept",
            "extended_attributes": [{"type": "vocabulary", "value": "ELSST"}],
        },
    )

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

    # -------------------------------------------------------------------------
    # 6. Semantic Graph (RDF Triple-like Relationships)
    # -------------------------------------------------------------------------
    SemanticRelationship.objects.get_or_create(
        subject_urn=sub_concept.uri,
        predicate="skos:exactMatch",
        object_urn="https://elsst.cessda.eu/id/4/PoliticalAttitudes",
        defaults={
            "subject_type": "Concept",
            "object_type": "Concept",
            "extended_attributes": [
                {"type": "thesaurus", "value": "ELSST"},
                {"type": "mapping_source", "value": "CESSDA ELSST v4"},
            ],
        },
    )

    SemanticRelationship.objects.get_or_create(
        subject_urn=cv_interest.urn,
        predicate="skos:relatedMatch",
        object_urn=sub_concept.uri,
        defaults={
            "subject_type": "ConceptualVariable",
            "object_type": "Concept",
            "extended_attributes": [
                {"type": "alignment_method", "value": "curated"},
                {"type": "confidence", "value": 0.98},
            ],
        },
    )

    SemanticRelationship.objects.get_or_create(
        subject_urn=qi_interest.urn,
        predicate="skos:narrowMatch",
        object_urn=cv_interest.urn,
        defaults={
            "subject_type": "QuestionItem",
            "object_type": "ConceptualVariable",
            "extended_attributes": [
                {"type": "alignment_type", "value": "indicator_measure"},
            ],
        },
    )

    return {
        "organizations": Organization.objects.count(),
        "groups": Group.objects.count(),
        "concept_schemes": ConceptScheme.objects.count(),
        "concepts": Concept.objects.count(),
        "conceptual_variable_schemes": ConceptualVariableScheme.objects.count(),
        "conceptual_variables": ConceptualVariable.objects.count(),
        "question_schemes": QuestionScheme.objects.count(),
        "question_items": QuestionItem.objects.count(),
        "question_variables": QuestionVariable.objects.count(),
        "instruments": Instrument.objects.count(),
        "instrument_questions": InstrumentQuestion.objects.count(),
        "category_schemes": CategoryScheme.objects.count(),
        "categories": Category.objects.count(),
        "code_lists": CodeList.objects.count(),
        "codes": Code.objects.count(),
        "represented_variable_schemes": RepresentedVariableScheme.objects.count(),
        "represented_variables": RepresentedVariable.objects.count(),
        "study_units": StudyUnit.objects.count(),
        "instance_variable_schemes": InstanceVariableScheme.objects.count(),
        "instance_variables": InstanceVariable.objects.count(),
        "study_unit_variables": StudyUnitVariable.objects.count(),
        "urn_registries": UrnRegistry.objects.count(),
        "urn_aliases": URNAlias.objects.count(),
        "staged_nodes": StagedResourceNode.objects.count(),
        "event_logs": EventLog.objects.count(),
        "semantic_relationships": SemanticRelationship.objects.count(),
    }
