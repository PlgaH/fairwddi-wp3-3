"""Unified Resource Set Resolver (`fairwddi.groups.resolver`).

Resolves structured set specifiers into typed URN sets for downstream comparison
and harmonization workflows:

- ``group:<slug_or_urn>`` — expands StudyUnits to full variable cascades & traverses nested groups
- ``batch:<id>`` — resources created by a specific ``IngestBatch``
- ``study:<urn>`` — single ``StudyUnit`` + full cascade (Datafile, InstanceVariable,
  RepresentedVariable, QuestionItem, CodeList, Category, ConceptualVariable, Concept)
- ``bank`` / ``bank:all`` / ``bank:imported`` / ``bank:harmonized`` — bank slices by origin
- ``urn:<u1,u2,...>`` — explicit list of resource URNs
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, Field

from fairwddi.groups.manager import _get_synced_member_refs, resolve_group


class ResourceSetSpec(BaseModel):
    """Parsed specifier describing a target resource set."""

    raw_spec: str
    kind: Literal["group", "batch", "study", "bank", "urns"]
    identifier: str | None = None


class ResolvedResourceSet(BaseModel):
    """Resolved resource set grouped by canonical DDI resource type."""

    spec: str
    kind: str
    label: str
    urns_by_type: dict[str, set[str]] = Field(default_factory=dict)
    study_urns: set[str] = Field(default_factory=set)
    group_urns: set[str] = Field(default_factory=set)

    @property
    def total_count(self) -> int:
        """Total count of resolved distinct resource URNs across all included types."""
        return len(self.all_urns)

    @property
    def all_urns(self) -> set[str]:
        """Union of all resolved URNs across all types."""
        union: set[str] = set()
        for urns in self.urns_by_type.values():
            union.update(urns)
        return union

    def urns_for(self, resource_type: str) -> set[str]:
        """Return resolved URNs for a specific DDI resource type."""
        return set(self.urns_by_type.get(resource_type, set()))


def parse_resource_set_spec(spec: str) -> ResourceSetSpec:
    """Parse a resource set specifier string into a typed :class:`ResourceSetSpec`."""
    raw = (spec or "").strip()
    if not raw:
        raise ValueError("Resource set specifier cannot be empty.")

    low = raw.lower()
    if low == "bank" or low.startswith("bank:"):
        scope = low.split(":", 1)[1] if ":" in low else "all"
        if scope not in ("all", "imported", "harmonized"):
            raise ValueError(
                f"Unsupported bank scope '{scope}' in '{raw}'. "
                "Expected 'bank', 'bank:all', 'bank:imported', or 'bank:harmonized'."
            )
        return ResourceSetSpec(raw_spec=raw, kind="bank", identifier=scope)

    if ":" not in raw:
        raise ValueError(
            f"Unrecognized set specifier '{raw}'. Expected one of: "
            "'group:<slug|urn>', 'batch:<id>', 'study:<urn>', "
            "'bank[:all|imported|harmonized]', or 'urn:<u1,u2,...>'."
        )

    prefix, ident = raw.split(":", 1)
    prefix_low = prefix.strip().lower()
    ident_clean = ident.strip()
    if not ident_clean:
        raise ValueError(f"Missing identifier after '{prefix_low}:' in set specifier '{raw}'.")

    if prefix_low == "group":
        return ResourceSetSpec(raw_spec=raw, kind="group", identifier=ident_clean)
    if prefix_low == "batch":
        return ResourceSetSpec(raw_spec=raw, kind="batch", identifier=ident_clean)
    if prefix_low == "study":
        return ResourceSetSpec(raw_spec=raw, kind="study", identifier=ident_clean)
    if prefix_low == "urn":
        return ResourceSetSpec(raw_spec=raw, kind="urns", identifier=ident_clean)

    raise ValueError(
        f"Unsupported set prefix '{prefix_low}' in '{raw}'. Expected 'group', 'batch', 'study', "
        "'bank', or 'urn'."
    )


def _expand_study_cascade(study_urns: set[str]) -> dict[str, set[str]]:
    """Expand StudyUnit URNs downward through Datafile -> IV -> RV -> QI/CodeList -> Cat/CV."""
    from fairwddi.models import (
        Category,
        Code,
        ConceptualVariable,
        Datafile,
        DatafileVariable,
        InstanceVariable,
        InstrumentQuestion,
        QuestionVariable,
        RepresentedVariable,
        StudyInstrument,
    )

    result: dict[str, set[str]] = {}
    if not study_urns:
        return result

    result["StudyUnit"] = set(study_urns)

    df_urns = set(
        Datafile.objects.filter(study_unit_id__in=study_urns).values_list("urn", flat=True)
    )
    if df_urns:
        result["Datafile"] = df_urns

    iv_urns = set(
        DatafileVariable.objects.filter(datafile_id__in=df_urns).values_list(
            "instance_variable_id", flat=True
        )
    )
    # Fallback scan for InstanceVariables linked to StudyUnit only via extended_attributes
    for iv_u, ext_attrs in InstanceVariable.objects.only("urn", "extended_attributes").values_list(
        "urn", "extended_attributes"
    ):
        if iv_u in iv_urns or not isinstance(ext_attrs, list):
            continue
        for item in ext_attrs:
            if (
                isinstance(item, dict)
                and item.get("type") == "study_unit_urn"
                and item.get("value") in study_urns
            ):
                iv_urns.add(iv_u)
                break
    if iv_urns:
        result["InstanceVariable"] = iv_urns

    rv_urns = set(
        InstanceVariable.objects.filter(
            urn__in=iv_urns, represented_variable__isnull=False
        ).values_list("represented_variable_id", flat=True)
    )
    if rv_urns:
        result["RepresentedVariable"] = rv_urns

    qi_urns = set(
        QuestionVariable.objects.filter(represented_variable_id__in=rv_urns).values_list(
            "question_item_id", flat=True
        )
    )
    inst_urns = set(
        StudyInstrument.objects.filter(study_unit_id__in=study_urns).values_list(
            "instrument_id", flat=True
        )
    )
    if inst_urns:
        result["Instrument"] = inst_urns
        qi_urns.update(
            InstrumentQuestion.objects.filter(instrument_id__in=inst_urns).values_list(
                "question_item_id", flat=True
            )
        )
    if qi_urns:
        result["QuestionItem"] = qi_urns

    cl_urns = set(
        RepresentedVariable.objects.filter(urn__in=rv_urns, code_list__isnull=False).values_list(
            "code_list_id", flat=True
        )
    )
    if cl_urns:
        result["CodeList"] = cl_urns

    cat_urns = set(
        Code.objects.filter(code_list_id__in=cl_urns).values_list("category_id", flat=True)
    )
    if cat_urns:
        result["Category"] = cat_urns

    cv_urns = set(
        RepresentedVariable.objects.filter(
            urn__in=rv_urns, conceptual_variable__isnull=False
        ).values_list("conceptual_variable_id", flat=True)
    )
    if cv_urns:
        result["ConceptualVariable"] = cv_urns

    concept_urns = set(
        ConceptualVariable.objects.filter(urn__in=cv_urns, concept__isnull=False).values_list(
            "concept_id", flat=True
        )
    )
    concept_urns.update(
        Category.objects.filter(urn__in=cat_urns, concept__isnull=False).values_list(
            "concept_id", flat=True
        )
    )
    if concept_urns:
        result["Concept"] = concept_urns

    return result


def _expand_group_recursive(
    group_urn: str,
    *,
    visited_groups: set[str],
    urns_by_type: dict[str, set[str]],
    study_urns: set[str],
) -> None:
    from fairwddi.models import Group

    if group_urn in visited_groups:
        return
    visited_groups.add(group_urn)

    group = Group.objects.filter(urn=group_urn).first()
    if group is None:
        return

    for ref in _get_synced_member_refs(group):
        r_type = ref["resource_type"]
        r_urn = ref["urn"]
        if r_type in ("Group", "VariableGroup"):
            _expand_group_recursive(
                r_urn,
                visited_groups=visited_groups,
                urns_by_type=urns_by_type,
                study_urns=study_urns,
            )
        elif r_type == "StudyUnit":
            study_urns.add(r_urn)
        else:
            urns_by_type.setdefault(r_type, set()).add(r_urn)


def _merge_type_maps(
    target: dict[str, set[str]], source: dict[str, set[str]]
) -> dict[str, set[str]]:
    for rt, urns in source.items():
        if urns:
            target.setdefault(rt, set()).update(urns)
    return target


def resolve_resource_set(
    spec: str,
    resource_types: Sequence[str] | None = None,
) -> ResolvedResourceSet:
    """Resolve a unified set specifier into typed resource URN sets (read-only)."""
    from fairwddi.models import IngestBatch, StudyUnit, UrnRegistry

    parsed = parse_resource_set_spec(spec)
    urns_by_type: dict[str, set[str]] = {}
    study_urns: set[str] = set()
    visited_groups: set[str] = set()
    label = parsed.raw_spec

    if parsed.kind == "group":
        assert parsed.identifier is not None
        group = resolve_group(parsed.identifier)
        label = group.slug or group.urn
        _expand_group_recursive(
            group.urn,
            visited_groups=visited_groups,
            urns_by_type=urns_by_type,
            study_urns=study_urns,
        )
        if study_urns:
            _merge_type_maps(urns_by_type, _expand_study_cascade(study_urns))

    elif parsed.kind == "study":
        assert parsed.identifier is not None
        su = StudyUnit.objects.filter(urn=parsed.identifier).only("urn").first()
        if su is None:
            raise ValueError(f"StudyUnit '{parsed.identifier}' not found.")
        study_urns.add(su.urn)
        label = su.urn
        _merge_type_maps(urns_by_type, _expand_study_cascade(study_urns))

    elif parsed.kind == "batch":
        assert parsed.identifier is not None
        try:
            batch_id = int(parsed.identifier)
        except ValueError as exc:
            raise ValueError(f"Batch identifier '{parsed.identifier}' must be an integer.") from exc
        batch = IngestBatch.objects.filter(id=batch_id).first()
        if batch is None:
            raise ValueError(f"IngestBatch #{batch_id} not found.")
        label = f"batch#{batch.id} ({batch.file_name})"
        raw_urns = list(batch.created_urns or [])
        if raw_urns:
            for row in UrnRegistry.objects.filter(urn__in=raw_urns).values("urn", "resource_type"):
                rt = row["resource_type"]
                u = row["urn"]
                urns_by_type.setdefault(rt, set()).add(u)
                if rt == "StudyUnit":
                    study_urns.add(u)

    elif parsed.kind == "bank":
        scope = parsed.identifier or "all"
        label = f"bank:{scope}"
        qs = UrnRegistry.objects.all()
        if scope == "imported":
            qs = qs.filter(origin="imported")
        elif scope == "harmonized":
            qs = qs.filter(origin__in=("generated", "instantiated"))
        for row in qs.values("urn", "resource_type"):
            rt = row["resource_type"]
            u = row["urn"]
            urns_by_type.setdefault(rt, set()).add(u)
            if rt == "StudyUnit":
                study_urns.add(u)

    elif parsed.kind == "urns":
        assert parsed.identifier is not None
        raw_list = [u.strip() for u in parsed.identifier.split(",") if u.strip()]
        label = f"urns({len(raw_list)})"
        if raw_list:
            rows = list(UrnRegistry.objects.filter(urn__in=raw_list).values("urn", "resource_type"))
            found = {r["urn"] for r in rows}
            missing = [u for u in raw_list if u not in found]
            if missing:
                raise ValueError(f"URN(s) not found in UrnRegistry: {', '.join(missing[:5])}")
            for row in rows:
                rt = row["resource_type"]
                u = row["urn"]
                if rt in ("Group", "VariableGroup"):
                    _expand_group_recursive(
                        u,
                        visited_groups=visited_groups,
                        urns_by_type=urns_by_type,
                        study_urns=study_urns,
                    )
                elif rt == "StudyUnit":
                    study_urns.add(u)
                else:
                    urns_by_type.setdefault(rt, set()).add(u)
            if study_urns:
                _merge_type_maps(urns_by_type, _expand_study_cascade(study_urns))

    if resource_types is not None:
        allowed = set(resource_types)
        urns_by_type = {rt: u_set for rt, u_set in urns_by_type.items() if rt in allowed and u_set}

    return ResolvedResourceSet(
        spec=parsed.raw_spec,
        kind=parsed.kind,
        label=label,
        urns_by_type=urns_by_type,
        study_urns=study_urns,
        group_urns=visited_groups,
    )
