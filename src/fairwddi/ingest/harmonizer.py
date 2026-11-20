"""Stage 3b (Harmonization & Lineage): Non-destructive, origin-aware harmonization & undo.

Supports:
- Linking ``imported`` resources into existing ``generated`` or ``instantiated`` resources
  (``link_to_harmonized_resource``) while enriching metadata (alternate spellings, languages).
- Creating new ``generated`` or ``instantiated`` harmonized resources from ``imported``
  resources (``create_harmonized_resource``).
- Declarative shared-stem grouping (``Group`` with ``dcterms:isPartOf``).
- Explicit W3C PROV-O / SKOS lineage (``prov:wasDerivedFrom``, ``skos:closeMatch``).
- Transactional rollback (``undo_harmonization``) via EventLog snapshots.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any

from django.db import transaction

from fairwddi.ingest.comparator import discover_candidates
from fairwddi.ingest.plan import IngestPlan, PlanActionItem, ReviewGate
from fairwddi.utils.integrity import get_resource_references, integrity_deletion_context
from fairwddi.utils.normalize_string import normalize_string
from fairwddi.utils.urn import generate_generic_urn, slugify, validate_ddi_urn

logger = logging.getLogger(__name__)


def _compute_hashes(resource_type: str, normalized_fields: dict[str, Any]) -> dict[str, str]:
    """Compute deterministic SHA-256 content and facet hashes."""
    canonical_json = json.dumps(
        {"type": resource_type, **normalized_fields},
        sort_keys=True,
        ensure_ascii=False,
    )
    content_digest = hashlib.sha256(canonical_json.encode()).hexdigest()
    hashes: dict[str, str] = {"content": f"sha256:{content_digest}"}

    if normalized_fields.get("label"):
        lbl_json = json.dumps(normalized_fields["label"], sort_keys=True, ensure_ascii=False)
        hashes["label"] = f"sha256:{hashlib.sha256(lbl_json.encode()).hexdigest()}"

    if normalized_fields.get("question_text"):
        qt_json = json.dumps(normalized_fields["question_text"], sort_keys=True, ensure_ascii=False)
        hashes["question_text"] = f"sha256:{hashlib.sha256(qt_json.encode()).hexdigest()}"

    if normalized_fields.get("codes"):
        codes_json = json.dumps(normalized_fields["codes"], sort_keys=True, ensure_ascii=False)
        hashes["codes"] = f"sha256:{hashlib.sha256(codes_json.encode()).hexdigest()}"

    return hashes


def _get_model_for_type(resource_type: str) -> Any:
    from fairwddi.models import (
        Category,
        CategoryScheme,
        CodeList,
        Concept,
        ConceptScheme,
        ConceptualVariable,
        ConceptualVariableScheme,
        Group,
        Instrument,
        QuestionItem,
        QuestionScheme,
        RepresentedVariable,
        RepresentedVariableScheme,
        StudyUnit,
        VariableGroup,
    )

    return {
        "Category": Category,
        "CodeList": CodeList,
        "QuestionItem": QuestionItem,
        "RepresentedVariable": RepresentedVariable,
        "Concept": Concept,
        "ConceptualVariable": ConceptualVariable,
        "StudyUnit": StudyUnit,
        "Instrument": Instrument,
        "Group": Group,
        "VariableGroup": VariableGroup,
        "CategoryScheme": CategoryScheme,
        "ConceptScheme": ConceptScheme,
        "ConceptualVariableScheme": ConceptualVariableScheme,
        "QuestionScheme": QuestionScheme,
        "RepresentedVariableScheme": RepresentedVariableScheme,
    }.get(resource_type)


def _to_dict_form(val: Any) -> dict[str, str]:
    if not val:
        return {}
    if isinstance(val, list):
        res: dict[str, str] = {}
        for item in val:
            if isinstance(item, dict):
                lang = (
                    item.get("lang")
                    or item.get("@lang")
                    or item.get("language")
                    or item.get("@language")
                    or "en"
                )
                text_val = item.get("value") or item.get("@value") or item.get("text") or ""
                if text_val:
                    res[str(lang)] = str(text_val)
        return res
    if isinstance(val, dict):
        return {str(k): str(v) for k, v in val.items() if v}
    return {}


def _merge_jsonb_dicts(
    target_val: Any,
    source_val: Any,
) -> Any:
    tgt_dict = _to_dict_form(target_val)
    src_dict = _to_dict_form(source_val)
    if not tgt_dict and not src_dict:
        return target_val
    merged = dict(tgt_dict)
    for lang, val in src_dict.items():
        if lang not in merged and val:
            merged[lang] = val
    if isinstance(target_val, list) or isinstance(source_val, list):
        return [{"lang": k, "value": v} for k, v in sorted(merged.items())]
    return dict(sorted(merged.items()))


def _extract_variant_strings(variants: Any) -> set[str]:
    """Extract normalized string set from a list/dict of variant specifications."""
    res: set[str] = set()
    if not variants:
        return res
    if isinstance(variants, str):
        cleaned = normalize_string(variants)
        if cleaned:
            res.add(cleaned)
    elif isinstance(variants, dict):
        for v in variants.values():
            if isinstance(v, str) and normalize_string(v):
                res.add(normalize_string(v))
    elif isinstance(variants, list):
        for item in variants:
            if isinstance(item, str) and normalize_string(item):
                res.add(normalize_string(item))
            elif isinstance(item, dict):
                for v in item.values():
                    if isinstance(v, str) and normalize_string(v):
                        res.add(normalize_string(v))
    return res


def _curate_multilingual_text(
    items: list[tuple[str, Any]],
    canonical_text: Any = None,
    preserved_variants: list[Any] | None = None,
    discarded_variants: list[Any] | None = None,
    variant_type: str | None = None,
    prefer_list_format: bool = False,
) -> tuple[Any, list[dict[str, Any]]]:
    """Merge multilingual texts across items, apply canonical_text, and collect wording_variants."""
    merged: dict[str, str] = {}
    any_list_input = prefer_list_format
    collected: list[tuple[str, str, str]] = []

    for src_urn, raw_val in items:
        if isinstance(raw_val, list):
            any_list_input = True
        d = _to_dict_form(raw_val)
        for lang, text_val in d.items():
            cleaned = normalize_string(text_val)
            if not cleaned:
                continue
            if lang not in merged:
                merged[lang] = cleaned
            collected.append((src_urn, lang, cleaned))

    if canonical_text:
        if isinstance(canonical_text, str):
            cleaned_can = normalize_string(canonical_text)
            if cleaned_can:
                target_lang = next(iter(merged.keys()), "fr")
                merged[target_lang] = cleaned_can
        else:
            can_dict = _to_dict_form(canonical_text)
            for lang, val in can_dict.items():
                cleaned_can = normalize_string(val)
                if cleaned_can:
                    merged[lang] = cleaned_can

    discarded_set = _extract_variant_strings(discarded_variants)
    discarded_lower = {s.lower() for s in discarded_set}
    preserved_set = (
        _extract_variant_strings(preserved_variants) if preserved_variants is not None else None
    )
    preserved_lower = {s.lower() for s in preserved_set} if preserved_set is not None else None

    variant_entries: list[dict[str, Any]] = []
    seen_variants: set[tuple[str, str]] = set()

    for src_urn, lang, text_val in collected:
        primary = merged.get(lang)
        if not primary or text_val == primary:
            continue
        if text_val in discarded_set or text_val.lower() in discarded_lower:
            continue
        if preserved_lower is not None and text_val.lower() not in preserved_lower:
            continue

        key = (lang, text_val)
        if key not in seen_variants:
            seen_variants.add(key)
            variant_entries.append(
                {
                    "type": "wording_variant",
                    "lang": lang,
                    "value": text_val,
                    "variant_type": variant_type or "alternate_spelling",
                    "is_default": False,
                    "source_urn": src_urn,
                }
            )

    if preserved_set:
        default_lang = next(iter(merged.keys()), "fr")
        default_src = items[-1][0] if items else ""
        for p_val in sorted(preserved_set):
            if p_val in discarded_set or p_val.lower() in discarded_lower:
                continue
            if p_val == merged.get(default_lang):
                continue
            key = (default_lang, p_val)
            if key not in seen_variants:
                seen_variants.add(key)
                variant_entries.append(
                    {
                        "type": "wording_variant",
                        "lang": default_lang,
                        "value": p_val,
                        "variant_type": variant_type or "alternate_spelling",
                        "is_default": False,
                        "source_urn": default_src,
                    }
                )

    if not merged:
        return ([] if any_list_input else {}), variant_entries

    final_val: Any = (
        [{"lang": k, "value": v} for k, v in sorted(merged.items())]
        if any_list_input
        else dict(sorted(merged.items()))
    )
    return final_val, variant_entries


def _append_unique_ext_attrs(
    existing: list[Any] | None,
    new_items: list[dict[str, Any]],
) -> list[Any]:
    res = list(existing or [])
    for item in new_items:
        if item.get("type") == "wording_variant":
            already = any(
                isinstance(e, dict)
                and e.get("type") == "wording_variant"
                and e.get("lang") == item.get("lang")
                and e.get("value") == item.get("value")
                for e in res
            )
            if not already:
                res.append(item)
        elif item not in res:
            res.append(item)
    return res


def _snapshot_target(obj: Any, resource_type: str) -> dict[str, Any]:
    """Capture pre-enrichment field values for rollback."""
    snap: dict[str, Any] = {
        "resource_type": resource_type,
        "urn": obj.urn,
        "name": getattr(obj, "name", None),
        "label": dict(obj.label)
        if isinstance(getattr(obj, "label", None), dict)
        else (
            list(obj.label)
            if isinstance(getattr(obj, "label", None), list)
            else getattr(obj, "label", None)
        ),
        "description": (
            dict(obj.description)
            if isinstance(getattr(obj, "description", None), dict)
            else (
                list(obj.description)
                if isinstance(getattr(obj, "description", None), list)
                else getattr(obj, "description", None)
            )
        ),
        "hashes": dict(obj.hashes) if isinstance(getattr(obj, "hashes", None), dict) else None,
        "extended_attributes": (
            list(obj.extended_attributes)
            if isinstance(getattr(obj, "extended_attributes", None), list)
            else getattr(obj, "extended_attributes", None)
        ),
    }
    if resource_type == "QuestionItem":
        qt = getattr(obj, "question_text", None)
        ii = getattr(obj, "interviewer_instructions", None)
        snap["question_text"] = (
            dict(qt) if isinstance(qt, dict) else (list(qt) if isinstance(qt, list) else qt)
        )
        snap["interviewer_instructions"] = (
            dict(ii) if isinstance(ii, dict) else (list(ii) if isinstance(ii, list) else ii)
        )
    elif resource_type == "Concept":
        df = getattr(obj, "definition", None)
        snap["definition"] = (
            dict(df) if isinstance(df, dict) else (list(df) if isinstance(df, list) else df)
        )
    return snap


def _restore_target_snapshot(snap: dict[str, Any]) -> None:
    """Restore a resource from a snapshot dict."""
    model_cls = _get_model_for_type(snap["resource_type"])
    if model_cls is None:
        return
    obj = model_cls.objects.filter(urn=snap["urn"]).first()
    if obj is None:
        return
    for fld in ("name", "label", "description", "hashes", "extended_attributes"):
        if fld in snap and hasattr(obj, fld):
            try:
                setattr(obj, fld, snap[fld])
            except AttributeError:
                pass
    if snap["resource_type"] == "QuestionItem":
        if "question_text" in snap:
            obj.question_text = snap["question_text"]
        if "interviewer_instructions" in snap:
            obj.interviewer_instructions = snap["interviewer_instructions"]
    elif snap["resource_type"] == "Concept" and "definition" in snap:
        obj.definition = snap["definition"]
    obj.save()


def _enrich_target_from_sources(
    target_obj: Any,
    sources: list[Any],
    resource_type: str,
    *,
    canonical_text: Any = None,
    preserved_variants: list[Any] | None = None,
    discarded_variants: list[Any] | None = None,
    variant_type: str | None = None,
) -> None:
    """Enrich an existing target resource with translations and alternate spellings from sources."""
    pre_label = getattr(target_obj, "label", None)
    pre_qt = getattr(target_obj, "question_text", None)

    for s in sources:
        if hasattr(s, "description") and s.description and hasattr(target_obj, "description"):
            target_obj.description = _merge_jsonb_dicts(target_obj.description, s.description)
        if (
            hasattr(s, "interviewer_instructions")
            and s.interviewer_instructions
            and hasattr(target_obj, "interviewer_instructions")
        ):
            target_obj.interviewer_instructions = _merge_jsonb_dicts(
                target_obj.interviewer_instructions, s.interviewer_instructions
            )
        if hasattr(s, "definition") and s.definition and hasattr(target_obj, "definition"):
            target_obj.definition = _merge_jsonb_dicts(target_obj.definition, s.definition)

    if resource_type == "QuestionItem" and hasattr(target_obj, "question_text"):
        qt_items = [
            (target_obj.urn, pre_qt),
            *((s.urn, getattr(s, "question_text", None)) for s in sources),
        ]
        curated_qt, qt_vars = _curate_multilingual_text(
            qt_items,
            canonical_text=canonical_text,
            preserved_variants=preserved_variants,
            discarded_variants=discarded_variants,
            variant_type=variant_type,
            prefer_list_format=isinstance(pre_qt, list),
        )
        if curated_qt:
            target_obj.question_text = curated_qt
        if qt_vars:
            target_obj.extended_attributes = _append_unique_ext_attrs(
                target_obj.extended_attributes, qt_vars
            )
        # Also merge optional label if present
        for s in sources:
            if getattr(s, "label", None) and target_obj.label != s.label:
                target_obj.label = _merge_jsonb_dicts(target_obj.label, s.label)
    elif hasattr(target_obj, "label"):
        lbl_items = [
            (target_obj.urn, pre_label),
            *((s.urn, getattr(s, "label", None)) for s in sources),
        ]
        curated_lbl, lbl_vars = _curate_multilingual_text(
            lbl_items,
            canonical_text=canonical_text,
            preserved_variants=preserved_variants,
            discarded_variants=discarded_variants,
            variant_type=variant_type,
            prefer_list_format=isinstance(pre_label, list),
        )
        if curated_lbl:
            target_obj.label = curated_lbl
        if lbl_vars:
            target_obj.extended_attributes = _append_unique_ext_attrs(
                target_obj.extended_attributes, lbl_vars
            )

    hash_payload: dict[str, Any] = {
        "name": getattr(target_obj, "name", None),
        "label": getattr(target_obj, "label", None),
        "description": getattr(target_obj, "description", None),
    }
    if resource_type == "QuestionItem" and hasattr(target_obj, "question_text"):
        hash_payload["question_text"] = target_obj.question_text
    elif resource_type == "Concept" and hasattr(target_obj, "definition"):
        hash_payload["definition"] = target_obj.definition

    target_obj.hashes = _compute_hashes(resource_type, hash_payload)


def _copy_codelist_structure(
    gen_cl: Any,
    source_cl: Any,
    origin: str = "generated",
) -> list[str]:
    """Copy Code items from source_cl onto gen_cl, resolving harmonized Categories."""
    from fairwddi.models import Category, CodeItem, SemanticRelationship

    created_code_urns: list[str] = []
    for ci in CodeItem.objects.filter(code_list=source_cl).select_related("category").order_by(
        "order", "code_value"
    ):
        target_cat = ci.category
        if target_cat is not None:
            parent_cat_urn = (
                SemanticRelationship.objects.filter(
                    predicate="prov:wasDerivedFrom",
                    object_urn=target_cat.urn,
                    subject_type="Category",
                )
                .values_list("subject_urn", flat=True)
                .first()
            )
            if parent_cat_urn:
                harm_cat = Category.objects.filter(urn=parent_cat_urn).first()
                if harm_cat is not None:
                    target_cat = harm_cat

        new_ci, created = CodeItem.objects.get_or_create(
            code_list=gen_cl,
            code_value=ci.code_value,
            defaults={
                "category": target_cat,
                "order": ci.order,
                "is_missing": ci.is_missing,
                "origin": origin,
            },
        )
        if created:
            created_code_urns.append(new_ci.urn)
    return created_code_urns


def _resolve_harmonized_codelist(source_rvs: list[Any]) -> Any | None:
    """Find harmonized or compatible CodeList for a newly generated RepresentedVariable."""
    from fairwddi.models import CodeList, SemanticRelationship

    for rv in source_rvs:
        if getattr(rv, "code_list_id", None):
            harm_cl_urn = (
                SemanticRelationship.objects.filter(
                    predicate="prov:wasDerivedFrom",
                    object_urn=rv.code_list_id,
                    subject_type="CodeList",
                )
                .values_list("subject_urn", flat=True)
                .first()
            )
            if harm_cl_urn:
                harm_cl = CodeList.objects.filter(urn=harm_cl_urn).first()
                if harm_cl is not None:
                    return harm_cl
            return rv.code_list
    return None


def link_to_harmonized_resource(
    source_urns: list[str] | str,
    target_urn: str,
    resource_type: str | None = None,
    provenance_note: str = "",
    canonical_text: Any = None,
    preserved_variants: list[Any] | None = None,
    discarded_variants: list[Any] | None = None,
    variant_type: str | None = None,
    match_type: str | None = None,
    confidence: float | None = None,
    job_id: str | None = None,
) -> dict[str, Any]:
    """Link ``imported`` resources to an existing ``generated``/``instantiated`` resource.

    Preserves all ``imported`` source records intact, enriches the target with missing
    language translations and alternate spellings (``wording_variant``), recomputes hashes,
    and records ``prov:wasDerivedFrom`` lineage in ``SemanticRelationship``.
    """
    from fairwddi.models import EventLog, SemanticRelationship, UrnRegistry

    sources_list = (
        [source_urns.strip()]
        if isinstance(source_urns, str)
        else list(dict.fromkeys(s.strip() for s in source_urns if s and s.strip()))
    )
    target_urn = target_urn.strip()
    sources_list = [s for s in sources_list if s != target_urn]
    if not sources_list:
        raise ValueError("At least one source_urn distinct from target_urn must be provided.")

    reg_target = UrnRegistry.objects.filter(urn=target_urn).first()
    if not reg_target:
        raise ValueError(f"Target URN '{target_urn}' does not exist in UrnRegistry.")

    eff_type = resource_type or reg_target.resource_type
    if reg_target.resource_type != eff_type:
        raise ValueError(
            f"Target URN '{target_urn}' has resource type '{reg_target.resource_type}', "
            f"expected '{eff_type}'."
        )

    reg_sources = list(UrnRegistry.objects.filter(urn__in=sources_list))
    mismatches = [r.urn for r in reg_sources if r.resource_type != eff_type]
    if mismatches:
        raise ValueError(f"Source URN(s) {mismatches} do not match resource type '{eff_type}'.")

    model_cls = _get_model_for_type(eff_type)
    if model_cls is None:
        raise ValueError(f"Unsupported resource type '{eff_type}'.")

    target_obj = model_cls.objects.filter(urn=target_urn).first()
    if target_obj is None:
        raise ValueError(f"Target {eff_type} '{target_urn}' not found.")

    sources = list(model_cls.objects.filter(urn__in=sources_list))
    found_urns = {s.urn for s in sources}
    missing = [u for u in sources_list if u not in found_urns]
    if missing:
        raise ValueError(f"Source {eff_type} record(s) not found: {sorted(missing)}")

    eff_job_id = job_id or f"link-{eff_type.lower()}-{uuid.uuid4().hex[:6]}"
    target_pre_snapshot = _snapshot_target(target_obj, eff_type)
    created_rel_ids: list[int] = []

    with transaction.atomic():
        _enrich_target_from_sources(
            target_obj,
            sources,
            eff_type,
            canonical_text=canonical_text,
            preserved_variants=preserved_variants,
            discarded_variants=discarded_variants,
            variant_type=variant_type,
        )
        target_obj.save()

        for s_urn in sources_list:
            ext_attrs: list[dict[str, Any]] = [
                {"type": "job_id", "value": eff_job_id},
                {"type": "actor", "value": provenance_note or "fairwddi.harmonizer"},
            ]
            if match_type:
                ext_attrs.append({"type": "match_type", "value": match_type})
            if confidence is not None:
                ext_attrs.append({"type": "confidence", "value": confidence})

            rel, created = SemanticRelationship.objects.get_or_create(
                subject_urn=target_urn,
                predicate="prov:wasDerivedFrom",
                object_urn=s_urn,
                defaults={
                    "subject_type": eff_type,
                    "object_type": eff_type,
                    "extended_attributes": ext_attrs,
                },
            )
            if created:
                created_rel_ids.append(rel.id)

        EventLog.objects.create(
            urn=target_urn,
            event_type="linked_harmonized",
            event_data={
                "job_type": "link_existing",
                "job_id": eff_job_id,
                "resource_type": eff_type,
                "target_urn": target_urn,
                "source_urns": sources_list,
                "target_pre_snapshot": target_pre_snapshot,
                "created_rel_ids": created_rel_ids,
            },
        )

    return {
        "job_id": eff_job_id,
        "target_urn": target_urn,
        "resource_type": eff_type,
        "target_origin": reg_target.origin,
        "source_urns": sources_list,
        "semantic_links_created": len(created_rel_ids),
        "created_rel_ids": created_rel_ids,
    }


def create_harmonized_resource(
    source_urns: list[str] | str,
    target_urn: str | None = None,
    resource_type: str | None = None,
    name: list[dict[str, str]] | str | None = None,
    agency: str | None = None,
    origin: str = "generated",
    provenance_note: str = "",
    canonical_text: Any = None,
    preserved_variants: list[Any] | None = None,
    discarded_variants: list[Any] | None = None,
    variant_type: str | None = None,
    match_type: str | None = None,
    confidence: float | None = None,
    job_id: str | None = None,
) -> dict[str, Any]:
    """Create a new ``generated`` or ``instantiated`` harmonized resource from ``imported`` sources.

    Source records remain intact in the database and are linked via ``prov:wasDerivedFrom``.
    """
    from fairwddi.models import EventLog, ResourceOrigin, SemanticRelationship, UrnRegistry

    if origin not in (ResourceOrigin.GENERATED, ResourceOrigin.INSTANTIATED):
        raise ValueError(
            f"Harmonized resources must have origin 'generated' or 'instantiated', got '{origin}'."
        )

    sources_list = (
        [source_urns.strip()]
        if isinstance(source_urns, str)
        else list(dict.fromkeys(s.strip() for s in source_urns if s and s.strip()))
    )
    if target_urn:
        target_urn = target_urn.strip()
        if not validate_ddi_urn(target_urn):
            raise ValueError(
                f"Invalid canonical DDI URN '{target_urn}'. "
                "Must match 'urn:ddi:agency:identifier:version'."
            )
        if UrnRegistry.objects.filter(urn=target_urn).exists():
            raise ValueError(
                f"Target URN '{target_urn}' already exists in UrnRegistry. "
                "Use link_to_harmonized_resource() instead."
            )
        sources_list = [s for s in sources_list if s != target_urn]

    if not sources_list:
        raise ValueError("At least one source_urn must be provided.")

    reg_entries = list(UrnRegistry.objects.filter(urn__in=sources_list))
    if not resource_type:
        types = {r.resource_type for r in reg_entries}
        if len(types) > 1:
            raise ValueError(
                f"Source URNs have mismatched resource types: {sorted(types)}. "
                "All sources must share the same resource type."
            )
        if types:
            resource_type = types.pop()
        else:
            for cand_type in (
                "QuestionItem",
                "RepresentedVariable",
                "ConceptualVariable",
                "CodeList",
                "Category",
                "Concept",
                "StudyUnit",
                "Instrument",
            ):
                cand_cls = _get_model_for_type(cand_type)
                if cand_cls and cand_cls.objects.filter(urn=sources_list[0]).exists():
                    resource_type = cand_type
                    break
        if not resource_type:
            raise ValueError(f"Could not infer resource type for '{sources_list[0]}'.")
    else:
        mismatches = [r.urn for r in reg_entries if r.resource_type != resource_type]
        if mismatches:
            raise ValueError(
                f"Source URN(s) {mismatches} do not match resource type '{resource_type}'."
            )

    model_cls = _get_model_for_type(resource_type)
    if model_cls is None:
        raise ValueError(f"Unsupported resource type '{resource_type}'.")

    sources = list(model_cls.objects.filter(urn__in=sources_list))
    found_urns = {s.urn for s in sources}
    missing = [u for u in sources_list if u not in found_urns]
    if missing:
        raise ValueError(f"Source {resource_type} record(s) not found: {sorted(missing)}")

    # Order sources deterministically according to sources_list
    source_by_urn = {s.urn: s for s in sources}
    ordered_sources = [source_by_urn[u] for u in sources_list]

    if not target_urn:
        slug_seed = None
        if isinstance(name, str) and name:
            slug_seed = name
        elif isinstance(name, list) and name:
            slug_seed = name[0].get("value")
        if not slug_seed:
            first = ordered_sources[0]
            if hasattr(first, "question_text") and first.question_text:
                qd = _to_dict_form(first.question_text)
                slug_seed = qd.get("fr") or qd.get("en") or next(iter(qd.values()), None)
            if not slug_seed and hasattr(first, "label") and first.label:
                ld = _to_dict_form(first.label)
                slug_seed = ld.get("fr") or ld.get("en") or next(iter(ld.values()), None)
            if not slug_seed and hasattr(first, "name") and first.name:
                if isinstance(first.name, list) and first.name:
                    slug_seed = first.name[0].get("value")
                elif isinstance(first.name, str):
                    slug_seed = first.name
        target_urn = generate_generic_urn(
            resource_type=resource_type,
            name_or_text=slug_seed,
            agency=agency,
        )

    if isinstance(name, str) and name:
        eff_name: Any = [{"value": name}]
    elif isinstance(name, list) and name:
        eff_name = name
    elif hasattr(ordered_sources[0], "name") and ordered_sources[0].name:
        first_name = ordered_sources[0].name
        eff_name = first_name if isinstance(first_name, list) else [{"value": str(first_name)}]
    else:
        eff_name = [{"value": f"Harmonized {resource_type}"}]

    merged_label = None
    merged_desc = None
    merged_qt = None
    merged_inst = None
    merged_def = None
    merged_ext: list[Any] = []

    for s in ordered_sources:
        if hasattr(s, "label") and s.label:
            merged_label = _merge_jsonb_dicts(merged_label, s.label)
        if hasattr(s, "description") and s.description:
            merged_desc = _merge_jsonb_dicts(merged_desc, s.description)
        if hasattr(s, "question_text") and s.question_text:
            merged_qt = _merge_jsonb_dicts(merged_qt, s.question_text)
        if hasattr(s, "interviewer_instructions") and s.interviewer_instructions:
            merged_inst = _merge_jsonb_dicts(merged_inst, s.interviewer_instructions)
        if hasattr(s, "definition") and s.definition:
            merged_def = _merge_jsonb_dicts(merged_def, s.definition)

    if resource_type == "QuestionItem":
        qt_items = [
            (s.urn, getattr(s, "question_text", None))
            for s in ordered_sources
            if getattr(s, "question_text", None)
        ]
        if qt_items or canonical_text:
            curated_qt, qt_vars = _curate_multilingual_text(
                qt_items,
                canonical_text=canonical_text,
                preserved_variants=preserved_variants,
                discarded_variants=discarded_variants,
                variant_type=variant_type,
                prefer_list_format=True,
            )
            if curated_qt:
                merged_qt = curated_qt
            if qt_vars:
                merged_ext = _append_unique_ext_attrs(merged_ext, qt_vars)
    else:
        lbl_items = [
            (s.urn, getattr(s, "label", None))
            for s in ordered_sources
            if getattr(s, "label", None)
        ]
        if lbl_items or canonical_text:
            prefer_list = any(isinstance(getattr(s, "label", None), list) for s in ordered_sources)
            curated_lbl, lbl_vars = _curate_multilingual_text(
                lbl_items,
                canonical_text=canonical_text,
                preserved_variants=preserved_variants,
                discarded_variants=discarded_variants,
                variant_type=variant_type,
                prefer_list_format=prefer_list,
            )
            if curated_lbl:
                merged_label = curated_lbl
            if lbl_vars:
                merged_ext = _append_unique_ext_attrs(merged_ext, lbl_vars)

    hash_payload: dict[str, Any] = {
        "name": eff_name,
        "label": merged_label,
        "description": merged_desc,
    }
    if resource_type == "QuestionItem" and merged_qt:
        hash_payload["question_text"] = merged_qt
    elif resource_type == "Concept" and merged_def:
        hash_payload["definition"] = merged_def

    hashes = _compute_hashes(resource_type, hash_payload)
    eff_job_id = job_id or f"harm-{origin}-{resource_type.lower()}-{uuid.uuid4().hex[:6]}"
    first_src = ordered_sources[0]

    create_kwargs: dict[str, Any] = {
        "urn": target_urn,
        "name": eff_name,
        "hashes": hashes,
        "origin": origin,
    }
    if merged_label is not None:
        create_kwargs["label"] = merged_label
    if merged_desc is not None:
        create_kwargs["description"] = merged_desc
    if merged_ext:
        create_kwargs["extended_attributes"] = merged_ext

    if resource_type == "QuestionItem":
        if merged_qt is not None:
            create_kwargs["question_text"] = merged_qt
        if merged_inst is not None:
            create_kwargs["interviewer_instructions"] = merged_inst
        if getattr(first_src, "response_domain", None) and not getattr(
            first_src, "code_list_id", None
        ):
            create_kwargs["response_domain"] = first_src.response_domain
    elif resource_type == "RepresentedVariable":
        resolved_cl = _resolve_harmonized_codelist(ordered_sources)
        if resolved_cl is not None:
            create_kwargs["code_list"] = resolved_cl
        elif getattr(first_src, "value_representation", None):
            create_kwargs["value_representation"] = first_src.value_representation
        if getattr(first_src, "conceptual_variable_id", None):
            create_kwargs["conceptual_variable_id"] = first_src.conceptual_variable_id
    elif resource_type == "Concept":
        if merged_def is not None:
            create_kwargs["definition"] = merged_def
        if getattr(first_src, "vocabulary", None):
            create_kwargs["vocabulary"] = first_src.vocabulary
        if getattr(first_src, "notation", None):
            create_kwargs["notation"] = first_src.notation
    elif resource_type in ("ConceptualVariable", "Category"):
        if getattr(first_src, "concept_id", None):
            create_kwargs["concept_id"] = first_src.concept_id

    created_rel_ids: list[int] = []
    created_code_urns: list[str] = []

    with transaction.atomic():
        harm_obj = model_cls.objects.create(**create_kwargs)

        if resource_type == "CodeList":
            created_code_urns = _copy_codelist_structure(harm_obj, first_src, origin=origin)
        elif resource_type == "QuestionItem" and getattr(first_src, "code_list_id", None):
            resolved_cl = _resolve_harmonized_codelist(ordered_sources)
            if resolved_cl is not None:
                harm_obj.code_list = resolved_cl
                harm_obj.save()

        for s_urn in sources_list:
            ext_attrs: list[dict[str, Any]] = [
                {"type": "job_id", "value": eff_job_id},
                {"type": "actor", "value": provenance_note or "fairwddi.harmonizer"},
            ]
            if match_type:
                ext_attrs.append({"type": "match_type", "value": match_type})
            if confidence is not None:
                ext_attrs.append({"type": "confidence", "value": confidence})

            rel, created = SemanticRelationship.objects.get_or_create(
                subject_urn=target_urn,
                predicate="prov:wasDerivedFrom",
                object_urn=s_urn,
                defaults={
                    "subject_type": resource_type,
                    "object_type": resource_type,
                    "extended_attributes": ext_attrs,
                },
            )
            if created:
                created_rel_ids.append(rel.id)

        EventLog.objects.create(
            urn=target_urn,
            event_type="harmonized_created",
            event_data={
                "job_type": "create_harmonized",
                "job_id": eff_job_id,
                "resource_type": resource_type,
                "origin": origin,
                "target_urn": target_urn,
                "source_urns": sources_list,
                "created_code_urns": created_code_urns,
                "created_rel_ids": created_rel_ids,
            },
        )

    return {
        "job_id": eff_job_id,
        "target_urn": target_urn,
        "resource_type": resource_type,
        "origin": origin,
        "source_urns": sources_list,
        "created_code_urns": created_code_urns,
        "semantic_links_created": len(created_rel_ids),
        "created_rel_ids": created_rel_ids,
    }


def plan_harmonization(
    batch_id: int | None = None,
    resource_type: str | None = None,
    study_urn: str | None = None,
    query: str | None = None,
    threshold: float = 0.75,
    output_dir: str | Path | None = None,
    auto_approve: bool = False,
) -> IngestPlan:
    """Generate a review-gated Harmonization Plan (`IngestPlan(stage='harmonize')`)."""
    candidates = discover_candidates(
        resource_type=resource_type,
        study_urn=study_urn,
        batch_id=batch_id,
        query=query,
        threshold=threshold,
        limit=500,
    )

    actions: list[PlanActionItem] = []
    action_counts: dict[str, int] = {}

    for idx, cand in enumerate(candidates, start=1):
        act_type = cand["recommended_action"]
        details = dict(cand["details"])
        if act_type == "generate_harmonized" and "generated_urn" not in details:
            slug_seed = details.get("canonical_text") or details.get("source_text") or details.get(
                "source_name"
            )
            if isinstance(slug_seed, dict):
                slug_seed = (
                    slug_seed.get("fr")
                    or slug_seed.get("en")
                    or next(iter(slug_seed.values()), None)
                )
            elif isinstance(slug_seed, list) and slug_seed and isinstance(slug_seed[0], dict):
                slug_seed = slug_seed[0].get("value")
            details["generated_urn"] = generate_generic_urn(
                resource_type=cand["resource_type"],
                name_or_text=str(slug_seed) if slug_seed else None,
            )

        action_counts[act_type] = action_counts.get(act_type, 0) + 1
        actions.append(
            PlanActionItem(
                id=f"harm-{idx:04d}",
                stage="harmonize",
                action=act_type,
                resource_type=cand["resource_type"],
                source_urn=cand["source_urn"],
                target_urn=cand["target_urn"],
                confidence=cand["confidence"],
                match_type=cand["match_type"],
                requires_review=cand["requires_review"],
                approved=True,
                details=details,
                notes=f"{cand['match_type']} ({cand['confidence']:.2f}) -> {act_type}",
            )
        )

    scope_tag = f"batch{batch_id}" if batch_id is not None else (resource_type or "bank").lower()
    job_id = f"harmonize-{scope_tag}-{uuid.uuid4().hex[:6]}"
    plan = IngestPlan(
        stage="harmonize",
        job_id=job_id,
        batch_id=batch_id,
        summary={
            "total_candidates": len(actions),
            "threshold": threshold,
            "by_action": action_counts,
        },
        actions=actions,
        review_gate=ReviewGate(approved=auto_approve),
    )
    if plan.is_ready_to_execute(auto_approve=auto_approve):
        plan.review_gate.approved = True

    if output_dir is not None:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        plan.to_yaml(out_dir / f"{job_id}.harmonize.plan.yaml")
        plan.to_markdown(out_dir / f"{job_id}.harmonize.report.md")

    return plan


def apply_harmonization(
    plan_or_path: IngestPlan | Path | str,
    auto_approve: bool = False,
) -> dict[str, Any]:
    """Execute an approved Harmonization Plan and log undo snapshots in EventLog."""
    from fairwddi.models import (
        EventLog,
        Group,
        QuestionVariable,
        SemanticRelationship,
        UrnRegistry,
    )

    plan = (
        plan_or_path if isinstance(plan_or_path, IngestPlan) else IngestPlan.from_yaml(plan_or_path)
    )

    if not plan.is_ready_to_execute(auto_approve=auto_approve):
        raise PermissionError(
            f"Harmonization plan '{plan.job_id}' has {plan.pending_review_count} "
            f"pending review item(s). Approve the plan YAML (review_gate.approved: true) "
            f"or pass --auto-approve."
        )

    linked_existing_count = 0
    generated_count = 0
    grouped_count = 0
    semantic_links_count = 0
    created_rel_ids: list[int] = []
    sub_job_ids: list[str] = []
    created_group_urns: list[str] = []
    group_snapshots: list[dict[str, Any]] = []

    with transaction.atomic():
        for act in plan.actions:
            if not act.approved or act.action == "skip":
                continue

            # A. Declarative Grouping (SHARED_STEM_GRID -> Group with dcterms:isPartOf)
            if act.action == "group":
                g_type = act.details.get("group_type", "question_grid")
                shared_stem = act.details.get("shared_stem", "")
                agency = os.getenv("DDI_AGENCY", "fr.cdsp")
                explicit_g_urn = act.details.get("group_urn")
                if explicit_g_urn and validate_ddi_urn(explicit_g_urn):
                    g_urn = explicit_g_urn
                else:
                    seed_str = shared_stem or f"{act.source_urn}:{act.target_urn}"
                    stem_hash = hashlib.sha256(seed_str.lower().encode("utf-8")).hexdigest()[:6]
                    slug = slugify(shared_stem or g_type, max_len=24)
                    g_urn = f"urn:ddi:{agency}:GRP-{slug}-{stem_hash}:1.0.0"

                grp_obj = Group.objects.filter(urn=g_urn).first()
                if grp_obj is not None:
                    if not any(gs["urn"] == g_urn for gs in group_snapshots) and (
                        g_urn not in created_group_urns
                    ):
                        group_snapshots.append(
                            {
                                "urn": g_urn,
                                "references": list(grp_obj.references or []),
                                "description": grp_obj.description,
                            }
                        )
                    refs = list(grp_obj.references or [])
                else:
                    langs = act.details.get("shared_languages") or ["fr"]
                    lang = langs[0] if isinstance(langs, list) and langs else "fr"
                    g_name = act.details.get("group_name") or f"Grid: {shared_stem[:40]}"
                    desc = [{"lang": lang, "value": shared_stem}] if shared_stem else []
                    grp_obj = Group.objects.create(
                        urn=g_urn,
                        name=[{"lang": lang, "value": g_name}],
                        group_type=g_type,
                        description=desc,
                        references=[],
                        origin="generated",
                    )
                    created_group_urns.append(g_urn)
                    refs = []

                member_specs: list[dict[str, Any]] = []
                if act.source_urn:
                    m_a: dict[str, Any] = {
                        "resource_type": act.resource_type,
                        "urn": act.source_urn,
                    }
                    if act.details.get("sub_item_a"):
                        m_a["sub_item"] = act.details["sub_item_a"]
                    member_specs.append(m_a)
                if act.target_urn:
                    m_b: dict[str, Any] = {
                        "resource_type": act.resource_type,
                        "urn": act.target_urn,
                    }
                    if act.details.get("sub_item_b"):
                        m_b["sub_item"] = act.details["sub_item_b"]
                    member_specs.append(m_b)

                if act.resource_type == "QuestionItem":
                    q_urns = [u for u in (act.source_urn, act.target_urn) if u]
                    for rv_urn in QuestionVariable.objects.filter(
                        question_item_id__in=q_urns
                    ).values_list("represented_variable_id", flat=True):
                        if rv_urn:
                            member_specs.append(
                                {"resource_type": "RepresentedVariable", "urn": rv_urn}
                            )
                elif act.resource_type == "RepresentedVariable":
                    rv_urns = [u for u in (act.source_urn, act.target_urn) if u]
                    for q_urn in QuestionVariable.objects.filter(
                        represented_variable_id__in=rv_urns
                    ).values_list("question_item_id", flat=True):
                        if q_urn:
                            member_specs.append({"resource_type": "QuestionItem", "urn": q_urn})

                existing_ref_urns = {r.get("urn") for r in refs if isinstance(r, dict)}
                for m_spec in member_specs:
                    m_urn = m_spec["urn"]
                    if m_urn not in existing_ref_urns:
                        refs.append(m_spec)
                        existing_ref_urns.add(m_urn)
                    if UrnRegistry.objects.filter(urn=m_urn).exists():
                        rel, created = SemanticRelationship.objects.get_or_create(
                            subject_urn=m_urn,
                            predicate="dcterms:isPartOf",
                            object_urn=g_urn,
                            defaults={
                                "subject_type": m_spec["resource_type"],
                                "object_type": "Group",
                                "extended_attributes": [
                                    {
                                        "type": "provenance",
                                        "value": f"fairwddi.harmonize:{plan.job_id}",
                                    }
                                ],
                            },
                        )
                        if created:
                            created_rel_ids.append(rel.id)
                            semantic_links_count += 1

                grp_obj.references = refs
                grp_obj.save(update_fields=["references", "updated_at"])
                grouped_count += 1
                continue

            if not act.target_urn:
                continue

            # B. Link imported resource to existing generated / instantiated resource
            if act.action == "link_existing":
                res = link_to_harmonized_resource(
                    source_urns=[act.source_urn],
                    target_urn=act.target_urn,
                    resource_type=act.resource_type,
                    provenance_note=f"fairwddi.harmonize:{plan.job_id}:{act.id}",
                    canonical_text=act.details.get("canonical_text"),
                    preserved_variants=act.details.get("preserved_variants"),
                    discarded_variants=act.details.get("discarded_variants"),
                    variant_type=act.details.get("variant_type"),
                    match_type=str(act.match_type) if act.match_type else None,
                    confidence=act.confidence,
                )
                linked_existing_count += 1
                semantic_links_count += res["semantic_links_created"]
                sub_job_ids.append(res["job_id"])
                continue

            # C. Generate new harmonized resource from two imported resources
            if act.action == "generate_harmonized":
                # Check if either source was already derived into a generated parent earlier in plan
                existing_parent = (
                    SemanticRelationship.objects.filter(
                        predicate="prov:wasDerivedFrom",
                        object_urn__in=[act.source_urn, act.target_urn],
                        subject_type=act.resource_type,
                    )
                    .values_list("subject_urn", flat=True)
                    .first()
                )
                if existing_parent:
                    unlinked = [
                        u
                        for u in (act.source_urn, act.target_urn)
                        if not SemanticRelationship.objects.filter(
                            subject_urn=existing_parent,
                            predicate="prov:wasDerivedFrom",
                            object_urn=u,
                        ).exists()
                    ]
                    if unlinked:
                        res = link_to_harmonized_resource(
                            source_urns=unlinked,
                            target_urn=existing_parent,
                            resource_type=act.resource_type,
                            provenance_note=f"fairwddi.harmonize:{plan.job_id}:{act.id}",
                            canonical_text=act.details.get("canonical_text"),
                            preserved_variants=act.details.get("preserved_variants"),
                            discarded_variants=act.details.get("discarded_variants"),
                            variant_type=act.details.get("variant_type"),
                            match_type=str(act.match_type) if act.match_type else None,
                            confidence=act.confidence,
                        )
                        linked_existing_count += 1
                        semantic_links_count += res["semantic_links_created"]
                        sub_job_ids.append(res["job_id"])
                else:
                    res = create_harmonized_resource(
                        source_urns=[act.target_urn, act.source_urn],
                        target_urn=act.details.get("generated_urn"),
                        resource_type=act.resource_type,
                        name=act.details.get("generic_name"),
                        origin="generated",
                        provenance_note=f"fairwddi.harmonize:{plan.job_id}:{act.id}",
                        canonical_text=act.details.get("canonical_text"),
                        preserved_variants=act.details.get("preserved_variants"),
                        discarded_variants=act.details.get("discarded_variants"),
                        variant_type=act.details.get("variant_type"),
                        match_type=str(act.match_type) if act.match_type else None,
                        confidence=act.confidence,
                    )
                    generated_count += 1
                    semantic_links_count += res["semantic_links_created"]
                    sub_job_ids.append(res["job_id"])
                continue

            # D. Semantic peer relationship (link_semantic -> skos:closeMatch / skos:relatedMatch)
            if act.action == "link_semantic":
                predicate = "skos:closeMatch" if act.confidence >= 0.80 else "skos:relatedMatch"
                rel, created = SemanticRelationship.objects.get_or_create(
                    subject_urn=act.source_urn,
                    predicate=predicate,
                    object_urn=act.target_urn,
                    defaults={
                        "subject_type": act.resource_type,
                        "object_type": act.resource_type,
                        "extended_attributes": [
                            {"type": "provenance", "value": f"fairwddi.harmonize:{plan.job_id}"}
                        ],
                    },
                )
                if created:
                    created_rel_ids.append(rel.id)
                    semantic_links_count += 1

        candidate_anchors = [
            *created_group_urns,
            *(a.target_urn for a in plan.actions if a.target_urn),
            *(a.source_urn for a in plan.actions if a.source_urn),
        ]
        anchor_urn = next(
            (u for u in candidate_anchors if u and UrnRegistry.objects.filter(urn=u).exists()),
            None,
        )
        if anchor_urn:
            EventLog.objects.create(
                urn=anchor_urn,
                event_type="harmonized",
                event_data={
                    "job_type": "harmonize",
                    "job_id": plan.job_id,
                    "created_rel_ids": created_rel_ids,
                    "sub_job_ids": sub_job_ids,
                    "created_group_urns": created_group_urns,
                    "group_snapshots": group_snapshots,
                },
            )

    return {
        "job_id": plan.job_id,
        "linked_existing_count": linked_existing_count,
        "generated_count": generated_count,
        "grouped_count": grouped_count,
        "semantic_links_created": semantic_links_count,
    }


def undo_harmonization(job_id: str) -> dict[str, Any]:
    """Revert an applied Harmonization Job using its EventLog snapshot."""
    from fairwddi.models import (
        CodeItem,
        EventLog,
        Group,
        SemanticRelationship,
        UrnRegistry,
    )

    ev = next(
        (
            e
            for e in EventLog.objects.filter(
                event_type__in=["harmonized", "harmonized_created", "linked_harmonized"]
            ).order_by("-id")
            if isinstance(e.event_data, dict) and e.event_data.get("job_id") == job_id
        ),
        None,
    )
    if ev is None:
        raise ValueError(f"Harmonization job '{job_id}' not found in EventLog.")

    data = ev.event_data
    job_type = data.get("job_type")

    with transaction.atomic():
        if job_type == "link_existing":
            snap = data.get("target_pre_snapshot")
            rel_ids = data.get("created_rel_ids", [])
            if rel_ids:
                SemanticRelationship.objects.filter(id__in=rel_ids).delete()
            if snap:
                _restore_target_snapshot(snap)
            ev.delete()
            return {
                "job_id": job_id,
                "status": "reverted",
                "target_urn": data.get("target_urn"),
                "removed_semantic_links": len(rel_ids),
            }

        if job_type == "create_harmonized":
            target_urn = data["target_urn"]
            resource_type = data["resource_type"]
            rel_ids = data.get("created_rel_ids", [])
            created_code_urns = set(data.get("created_code_urns", []))
            model_cls = _get_model_for_type(resource_type)

            # Check if any external resources reference this generated resource
            refs = get_resource_references(target_urn, ignore_urns=created_code_urns)
            extra_links = (
                SemanticRelationship.objects.filter(subject_urn=target_urn)
                .exclude(id__in=rel_ids)
                .count()
            )
            if refs or extra_links:
                raise ValueError(
                    f"Cannot revert harmonized resource '{target_urn}': "
                    f"referenced by {len(refs) + extra_links} active resource(s)/link(s)."
                )

            if rel_ids:
                SemanticRelationship.objects.filter(id__in=rel_ids).delete()
            SemanticRelationship.objects.filter(subject_urn=target_urn).delete()

            with integrity_deletion_context(ignore_urns={target_urn} | created_code_urns):
                if created_code_urns:
                    CodeItem.objects.filter(urn__in=created_code_urns).delete()
                if model_cls is not None:
                    model_cls.objects.filter(urn=target_urn).delete()
                UrnRegistry.objects.filter(urn=target_urn).delete()

            ev.delete()
            return {
                "job_id": job_id,
                "status": "reverted",
                "removed_target_urn": target_urn,
                "removed_semantic_links": len(rel_ids),
            }

        # Batch harmonization job
        created_rel_ids = data.get("created_rel_ids", [])
        sub_job_ids = data.get("sub_job_ids", [])
        created_group_urns = data.get("created_group_urns", [])
        group_snapshots = data.get("group_snapshots", [])

        reverted_sub_jobs = 0
        for sub_id in reversed(sub_job_ids):
            try:
                undo_harmonization(sub_id)
                reverted_sub_jobs += 1
            except ValueError:
                pass

        for g_snap in reversed(group_snapshots):
            grp = Group.objects.filter(urn=g_snap["urn"]).first()
            if grp is not None:
                grp.references = g_snap.get("references", [])
                grp.description = g_snap.get("description", [])
                grp.save(update_fields=["references", "description", "updated_at"])

        if created_rel_ids:
            SemanticRelationship.objects.filter(id__in=created_rel_ids).delete()

        if created_group_urns:
            with integrity_deletion_context(ignore_urns=set(created_group_urns)):
                for g_u in created_group_urns:
                    SemanticRelationship.objects.filter(object_urn=g_u).delete()
                Group.objects.filter(urn__in=created_group_urns).delete()
                UrnRegistry.objects.filter(urn__in=created_group_urns).delete()

        ev.delete()

        return {
            "job_id": job_id,
            "status": "reverted",
            "reverted_sub_jobs": reverted_sub_jobs,
            "removed_groups": len(created_group_urns),
            "removed_semantic_links": len(created_rel_ids),
        }
