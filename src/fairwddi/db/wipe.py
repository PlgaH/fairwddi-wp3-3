"""Database wipe utility for FAIRwDDI.

Deletes all records across all FAIRwDDI tables in safe reverse topological order.
"""

from __future__ import annotations


def wipe_database() -> dict[str, int]:
    """Wipe all records across all FAIRwDDI tables in reverse topological order.

    Returns a summary dictionary of deleted record counts by entity.
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

    models_in_delete_order = [
        ("event_logs", EventLog),
        ("semantic_relationships", SemanticRelationship),
        ("instrument_questions", InstrumentQuestion),
        ("instruments", Instrument),
        ("study_unit_variables", StudyUnitVariable),
        ("instance_variables", InstanceVariable),
        ("instance_variable_schemes", InstanceVariableScheme),
        ("study_units", StudyUnit),
        ("question_variables", QuestionVariable),
        ("represented_variables", RepresentedVariable),
        ("represented_variable_schemes", RepresentedVariableScheme),
        ("codes", Code),
        ("code_lists", CodeList),
        ("categories", Category),
        ("category_schemes", CategoryScheme),
        ("question_items", QuestionItem),
        ("question_schemes", QuestionScheme),
        ("conceptual_variables", ConceptualVariable),
        ("conceptual_variable_schemes", ConceptualVariableScheme),
        ("concepts", Concept),
        ("concept_schemes", ConceptScheme),
        ("groups", Group),
        ("organizations", Organization),
        ("urn_aliases", URNAlias),
        ("urn_registries", UrnRegistry),
        ("metadata_quarantine", MetadataQuarantine),
        ("staged_nodes", StagedResourceNode),
        ("staged_imports", StagedImport),
    ]

    deleted_counts: dict[str, int] = {}
    for name, model in models_in_delete_order:
        count = model.objects.count()
        if count > 0:
            model.objects.all().delete()
        deleted_counts[name] = count

    return deleted_counts
