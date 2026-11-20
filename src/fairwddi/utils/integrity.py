"""Referential integrity and deletion-protection utilities for FAIRwDDI resources.

Ensures that any resource referenced by another resource—whether through relational
foreign keys, junction tables, Group memberships, or semantic/lineage triples
(such as ``prov:wasDerivedFrom``)—cannot be deleted while references exist.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from django.db.models.deletion import ProtectedError

_BYPASS_INTEGRITY: ContextVar[bool] = ContextVar("fairwddi_bypass_integrity", default=False)
_IGNORE_URNS: ContextVar[frozenset[str]] = ContextVar("fairwddi_ignore_urns", default=frozenset())


class ResourceReferencedError(ProtectedError):
    """Raised when attempting to delete a resource that is still referenced by other resources."""


@contextmanager
def integrity_deletion_context(
    *,
    ignore_urns: set[str] | frozenset[str] | None = None,
    bypass: bool = False,
) -> Iterator[None]:
    """Temporarily scope deletion-integrity checks (e.g., for batch rollback or full wipe)."""
    tok_bypass = _BYPASS_INTEGRITY.set(bypass)
    tok_ignore = _IGNORE_URNS.set(frozenset(ignore_urns or ()))
    try:
        yield
    finally:
        _IGNORE_URNS.reset(tok_ignore)
        _BYPASS_INTEGRITY.reset(tok_bypass)


def is_integrity_bypassed() -> bool:
    """Return True if integrity checks are currently bypassed via context."""
    return _BYPASS_INTEGRITY.get()


def get_ignored_urns() -> frozenset[str]:
    """Return the set of URNs ignored during the active batch deletion context."""
    return _IGNORE_URNS.get()


def get_resource_references(
    urn: str,
    ignore_urns: set[str] | frozenset[str] | None = None,
) -> list[dict[str, Any]]:
    """Collect all active references pointing to ``urn`` from outside ``ignore_urns``.

    Inspects:
    1. Relational foreign keys and junction tables across all DDI layers.
    2. ``Group.references`` JSONB membership lists.
    3. ``SemanticRelationship`` triples where ``object_urn == urn`` (e.g., ``prov:wasDerivedFrom``,
       ``skos:exactMatch``, ``dcterms:isPartOf``).
    """
    from fairwddi.models import (
        Category,
        Code,
        CodeList,
        Concept,
        ConceptualVariable,
        Datafile,
        DatafileVariable,
        DatafileVariableFrequency,
        Group,
        InstanceVariable,
        InstrumentQuestion,
        QuestionItem,
        QuestionVariable,
        RepresentedVariable,
        SemanticRelationship,
        StudyInstrument,
    )

    ignore = set(ignore_urns or ()) | set(_IGNORE_URNS.get())
    ignore.add(urn)
    refs: list[dict[str, Any]] = []

    def _add(table: str, referencing_urn: str | None, field: str) -> None:
        if referencing_urn and referencing_urn not in ignore:
            refs.append({"table": table, "urn": referencing_urn, "field": field})

    # 1. Representation & Concept Layer FKs
    for c in Code.objects.filter(category_id=urn).only("urn", "code_list_id"):
        if c.urn not in ignore and (not c.code_list_id or c.code_list_id not in ignore):
            _add("Code", c.urn, "category")

    for c in Code.objects.filter(code_list_id=urn).only("urn"):
        _add("Code", c.urn, "code_list")

    for c in Code.objects.filter(parent_id=urn).only("urn"):
        _add("Code", c.urn, "parent")

    for qi in QuestionItem.objects.filter(code_list_id=urn).only("urn"):
        _add("QuestionItem", qi.urn, "code_list")

    for qi in QuestionItem.objects.filter(scheme_id=urn).only("urn"):
        _add("QuestionItem", qi.urn, "scheme")

    for rv in RepresentedVariable.objects.filter(code_list_id=urn).only("urn"):
        _add("RepresentedVariable", rv.urn, "code_list")

    for rv in RepresentedVariable.objects.filter(conceptual_variable_id=urn).only("urn"):
        _add("RepresentedVariable", rv.urn, "conceptual_variable")

    for rv in RepresentedVariable.objects.filter(scheme_id=urn).only("urn"):
        _add("RepresentedVariable", rv.urn, "scheme")

    for cat in Category.objects.filter(concept_id=urn).only("urn"):
        _add("Category", cat.urn, "concept")

    for cat in Category.objects.filter(parent_id=urn).only("urn"):
        _add("Category", cat.urn, "parent")

    for cat in Category.objects.filter(scheme_id=urn).only("urn"):
        _add("Category", cat.urn, "scheme")

    for cl in CodeList.objects.filter(scheme_id=urn).only("urn"):
        _add("CodeList", cl.urn, "scheme")

    for cv in ConceptualVariable.objects.filter(concept_id=urn).only("urn"):
        _add("ConceptualVariable", cv.urn, "concept")

    for cv in ConceptualVariable.objects.filter(scheme_id=urn).only("urn"):
        _add("ConceptualVariable", cv.urn, "scheme")

    for con in Concept.objects.filter(parent_id=urn).only("urn"):
        _add("Concept", con.urn, "parent")

    for con in Concept.objects.filter(scheme_id=urn).only("urn"):
        _add("Concept", con.urn, "scheme")

    # 2. Dataset & Instrument Layer FKs
    for iv in InstanceVariable.objects.filter(represented_variable_id=urn).only("urn"):
        _add("InstanceVariable", iv.urn, "represented_variable")

    for iv in InstanceVariable.objects.filter(scheme_id=urn).only("urn"):
        _add("InstanceVariable", iv.urn, "scheme")

    for df in Datafile.objects.filter(study_unit_id=urn).only("urn"):
        _add("Datafile", df.urn, "study_unit")

    # 3. Junction tables
    for qv in QuestionVariable.objects.filter(question_item_id=urn).only("represented_variable_id"):
        _add("QuestionVariable", qv.represented_variable_id, "question_item")

    for qv in QuestionVariable.objects.filter(represented_variable_id=urn).only("question_item_id"):
        _add("QuestionVariable", qv.question_item_id, "represented_variable")

    for iq in InstrumentQuestion.objects.filter(question_item_id=urn).only("instrument_id"):
        _add("InstrumentQuestion", iq.instrument_id, "question_item")

    for iq in InstrumentQuestion.objects.filter(instrument_id=urn).only("question_item_id"):
        _add("InstrumentQuestion", iq.question_item_id, "instrument")

    for si in StudyInstrument.objects.filter(instrument_id=urn).only("study_unit_id"):
        _add("StudyInstrument", si.study_unit_id, "instrument")

    for si in StudyInstrument.objects.filter(study_unit_id=urn).only("instrument_id"):
        _add("StudyInstrument", si.instrument_id, "study_unit")

    for dfv in DatafileVariable.objects.filter(datafile_id=urn).only("instance_variable_id"):
        _add("DatafileVariable", dfv.instance_variable_id, "datafile")

    for dfv in DatafileVariable.objects.filter(instance_variable_id=urn).only("datafile_id"):
        _add("DatafileVariable", dfv.datafile_id, "instance_variable")

    for freq in DatafileVariableFrequency.objects.filter(datafile_id=urn).only(
        "instance_variable_id"
    ):
        _add("DatafileVariableFrequency", freq.instance_variable_id, "datafile")

    for freq in DatafileVariableFrequency.objects.filter(instance_variable_id=urn).only(
        "datafile_id"
    ):
        _add("DatafileVariableFrequency", freq.datafile_id, "instance_variable")

    # 4. Group.references JSONB
    for grp in Group.objects.only("urn", "references"):
        if grp.urn in ignore or not isinstance(grp.references, list):
            continue
        if any(isinstance(r, dict) and r.get("urn") == urn for r in grp.references):
            _add("Group", grp.urn, "references")

    # 5. SemanticRelationship / Lineage references where urn is the referenced object
    for rel in SemanticRelationship.objects.filter(object_urn=urn).only("subject_urn", "predicate"):
        _add("SemanticRelationship", rel.subject_urn, rel.predicate)

    return refs


def assert_can_delete(
    urn: str,
    ignore_urns: set[str] | frozenset[str] | None = None,
) -> None:
    """Raise ``ResourceReferencedError`` if ``urn`` is referenced by any active resource."""
    if _BYPASS_INTEGRITY.get():
        return
    refs = get_resource_references(urn, ignore_urns=ignore_urns)
    if refs:
        sample = ", ".join(f"{r['table']}({r['urn']} via {r['field']})" for r in refs[:5])
        extra = f" ... (+{len(refs) - 5} more)" if len(refs) > 5 else ""
        raise ResourceReferencedError(
            f"Cannot delete resource '{urn}': it is referenced by {len(refs)} "
            f"resource(s) [{sample}{extra}].",
            protected_objects=set(),
        )
