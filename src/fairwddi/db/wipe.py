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
        StagedImport,
        StagedResourceNode,
        StudyUnit,
        Subcollection,
        URNAlias,
        VariableGroup,
        VariableGroupMembership,
    )

    models_in_delete_order = [
        ("variable_group_memberships", VariableGroupMembership),
        ("variable_groups", VariableGroup),
        ("instance_variables", InstanceVariable),
        ("study_units", StudyUnit),
        ("represented_variables", RepresentedVariable),
        ("code_items", CodeItem),
        ("code_lists", CodeList),
        ("category_set_items", CategorySetItem),
        ("category_sets", CategorySet),
        ("categories", Category),
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
