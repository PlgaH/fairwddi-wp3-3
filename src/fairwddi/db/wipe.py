"""Database wipe utility for FAIRwDDI.

Deletes all records across all FAIRwDDI tables in strict leaf-to-root topological order
respecting ``on_delete=models.PROTECT`` foreign keys and lineage integrity guards.
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
        Datafile,
        DatafileVariable,
        DatafileVariableFrequency,
        EventLog,
        Group,
        IngestBatch,
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
        StudyInstrument,
        StudyUnit,
        URNAlias,
        UrnRegistry,
    )
    from fairwddi.utils.integrity import integrity_deletion_context

    models_in_delete_order = [
        ("event_logs", EventLog),
        ("semantic_relationships", SemanticRelationship),
        ("datafile_variable_frequencies", DatafileVariableFrequency),
        ("datafile_variables", DatafileVariable),
        ("study_instruments", StudyInstrument),
        ("instrument_questions", InstrumentQuestion),
        ("question_variables", QuestionVariable),
        ("instance_variables", InstanceVariable),
        ("instance_variable_schemes", InstanceVariableScheme),
        ("datafiles", Datafile),
        ("study_units", StudyUnit),
        ("codes", Code),
        ("question_items", QuestionItem),
        ("question_schemes", QuestionScheme),
        ("represented_variables", RepresentedVariable),
        ("represented_variable_schemes", RepresentedVariableScheme),
        ("code_lists", CodeList),
        ("categories", Category),
        ("category_schemes", CategoryScheme),
        ("conceptual_variables", ConceptualVariable),
        ("conceptual_variable_schemes", ConceptualVariableScheme),
        ("concepts", Concept),
        ("concept_schemes", ConceptScheme),
        ("instruments", Instrument),
        ("groups", Group),
        ("organizations", Organization),
        ("urn_aliases", URNAlias),
        ("metadata_quarantine", MetadataQuarantine),
        ("ingest_batches", IngestBatch),
        ("urn_registries", UrnRegistry),
    ]

    deleted_counts: dict[str, int] = {}
    with integrity_deletion_context(bypass=True):
        # Clear self-referential parent pointers before deleting protected hierarchies
        Code.objects.exclude(parent__isnull=True).update(parent=None)
        Category.objects.exclude(parent__isnull=True).update(parent=None)
        Concept.objects.exclude(parent__isnull=True).update(parent=None)

        for name, model in models_in_delete_order:
            count = model.objects.count()
            if count > 0:
                model.objects.all().delete()
            deleted_counts[name] = count

    return deleted_counts
