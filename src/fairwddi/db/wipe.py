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

    models_in_delete_order = [
        ("study_unit_variables", StudyUnitVariable),
        ("instance_variables", InstanceVariable),
        ("study_units", StudyUnit),
        ("represented_variables", RepresentedVariable),
        ("codes", Code),
        ("code_lists", CodeList),
        ("category_scheme_items", CategorySchemeItem),
        ("category_schemes", CategoryScheme),
        ("categories", Category),
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
