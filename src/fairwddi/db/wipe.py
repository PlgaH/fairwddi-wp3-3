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
        StagedImport,
        StagedResourceNode,
        StudyUnit,
        StudyUnitVariable,
        Subcollection,
        URNAlias,
    )

    models_in_delete_order = [
        ("event_logs", EventLog),
        ("instrument_questions", InstrumentQuestion),
        ("instruments", Instrument),
        ("study_unit_variables", StudyUnitVariable),
        ("instance_variables", InstanceVariable),
        ("study_units", StudyUnit),
        ("question_variables", QuestionVariable),
        ("represented_variables", RepresentedVariable),
        ("codes", Code),
        ("code_lists", CodeList),
        ("categories", Category),
        ("category_schemes", CategoryScheme),
        ("question_group_items", QuestionGroupItem),
        ("question_groups", QuestionGroup),
        ("question_items", QuestionItem),
        ("conceptual_variables", ConceptualVariable),
        ("concepts", Concept),
        ("subcollections", Subcollection),
        ("collections", Collection),
        ("distributors", Distributor),
        ("urn_aliases", URNAlias),
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
