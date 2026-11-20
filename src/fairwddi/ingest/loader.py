"""Stage 2 (Direct Ingestion & Undo): Non-destructive streaming ingestion with two-tier matching.

Streams DDI metadata files directly into ReQuest core tables:

- Incoming resources are always persisted with ``origin='imported'`` (never silently absorbed).
- Same-URN collisions always trigger review (`reuse` on matching hash, `quarantine` on drift).
- New incoming resources are matched against the bank with strict two-tier priority:

  1. Tier 1 (`generated` / `instantiated`): emit `link_existing` to link via `prov:wasDerivedFrom`
     and enrich target metadata (alternate spellings / translations).
  2. Tier 2 (unharmonized `imported`): emit `generate_harmonized` to synthesize a new `generated`
     resource uniting both `imported` resources via `prov:wasDerivedFrom`.

- Referential integrity & deletion protection are enforced across `undo_ingestion` and deletes.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from pathlib import Path
from typing import Any

from django.db import transaction

from fairwddi.ingest.comparator import (
    HARMONIZABLE_RESOURCE_TYPES,
    _load_resource_records,
    build_comparison_record,
    find_best_match_for_incoming,
)
from fairwddi.ingest.detector import compute_file_sha256, detect_metadata_format
from fairwddi.ingest.plan import IngestPlan, PlanActionItem, PlanIssue, ReviewGate
from fairwddi.ingest.profiles import ImportProfile, load_profile
from fairwddi.ingest.streaming import RawResourceNode, stream_resources
from fairwddi.utils.integrity import (
    assert_can_delete,
    get_resource_references,
    integrity_deletion_context,
)
from fairwddi.utils.normalize_string import normalize_string


def parse_ddi_urn(urn: str, default_agency: str | None = None) -> tuple[str, str, str, str]:
    """Parse a DDI URN into (canonical_urn, agency, identifier, version)."""
    fallback_agency = default_agency or os.getenv("DDI_AGENCY", "fr.cdsp")
    cleaned = (urn or "").strip()
    if cleaned.startswith("urn:ddi:"):
        parts = cleaned.split(":")
        if len(parts) == 5:
            _, _, agency, identifier, version = parts
            return cleaned, agency or fallback_agency, identifier, version or "1.0.0"
        if len(parts) > 5:
            agency = parts[2] or fallback_agency
            version = parts[-1] or "1.0.0"
            identifier = ":".join(parts[3:-1])
            return f"urn:ddi:{agency}:{identifier}:{version}", agency, identifier, version
        if len(parts) == 4:
            agency = parts[2] or fallback_agency
            identifier = parts[3]
            version = "1.0.0"
            return f"urn:ddi:{agency}:{identifier}:{version}", agency, identifier, version

    safe_id = re.sub(r"[^A-Za-z0-9_.\-]", "_", cleaned) or f"item_{uuid.uuid4().hex[:8]}"
    canonical = f"urn:ddi:{fallback_agency}:{safe_id}:1.0.0"
    return canonical, fallback_agency, safe_id, "1.0.0"


def _extract_multilingual(val: Any, default_lang: str = "en") -> dict[str, str] | None:
    """Extract normalized ISO 639-1 multilingual JSONB dictionary from DDI 4/3.3/2.5 structures."""
    result: dict[str, str] = {}

    def _visit(node: Any, current_lang: str) -> None:
        if node is None:
            return
        if isinstance(node, str):
            cleaned = normalize_string(node)
            if cleaned and current_lang not in result:
                result[current_lang] = cleaned
            return
        if isinstance(node, list):
            for item in node:
                _visit(item, current_lang)
            return
        if isinstance(node, dict):
            lang = (
                node.get("language")
                or node.get("@language")
                or node.get("xml_lang")
                or node.get("lang")
                or node.get("@lang")
                or node.get("@xml:lang")
                or node.get("xml:lang")
                or current_lang
            )
            lang = str(lang).split("-")[0].lower() if lang else default_lang

            for k in (
                "value",
                "@value",
                "StringValue",
                "string_value",
                "MultilingualStringValue",
                "multilingual_string_value",
                "content",
                "#text",
            ):
                if k in node and isinstance(node[k], str):
                    cleaned = normalize_string(node[k])
                    if cleaned:
                        result[lang] = cleaned
                    return

            for k in (
                "String",
                "string",
                "Content",
                "content",
                "TextContent",
                "text_content",
                "Text",
                "text",
                "LiteralText",
                "literal_text",
                "DynamicText",
                "dynamic_text",
                "Name",
                "name",
                "labl",
                "qstnLit",
                "ivuInstr",
                "txt",
                "titl",
            ):
                if k in node:
                    _visit(node[k], lang)

    _visit(val, default_lang)
    return dict(sorted(result.items())) if result else None


def _extract_first_string(val: Any) -> str | None:
    """Extract a single clean string from a multilingual or nested value."""
    ml = _extract_multilingual(val)
    if ml:
        return next(iter(ml.values()))
    if isinstance(val, str) and val.strip():
        return val.strip()
    if isinstance(val, dict):
        for k in (
            "StringValue",
            "string_value",
            "value",
            "@value",
            "#text",
            "content",
            "ID",
            "URN",
        ):
            if isinstance(val.get(k), str) and val[k].strip():
                return val[k].strip()
    return None


def _extract_user_attributes(raw_val: dict[str, Any]) -> dict[str, str]:
    """Extract UserAttributePair key-value pairs from a DDI 4 or 3.3 resource dict."""
    uaps = raw_val.get("UserAttributePair") or raw_val.get("user_attribute_pair") or []
    if isinstance(uaps, dict):
        uaps = [uaps]
    result: dict[str, str] = {}
    for pair in uaps:
        if not isinstance(pair, dict):
            continue
        k = _extract_first_string(pair.get("AttributeKey") or pair.get("attribute_key"))
        v = _extract_first_string(pair.get("AttributeValue") or pair.get("attribute_value"))
        if k and v is not None:
            result[k] = v
    return result


def _extract_ref_urn(ref_obj: Any) -> str | None:
    """Extract a referenced URN from a DDI 4 or DDI 3.3 reference object or list."""
    if isinstance(ref_obj, list):
        for item in ref_obj:
            u = _extract_ref_urn(item)
            if u:
                return u
        return None
    if isinstance(ref_obj, str) and ref_obj.strip():
        return ref_obj.strip()
    if isinstance(ref_obj, dict):
        urn = ref_obj.get("URN") or ref_obj.get("urn")
        if isinstance(urn, str) and urn.strip():
            return urn.strip()
        if isinstance(urn, dict) and isinstance(urn.get("#text"), str):
            return urn["#text"].strip()
        agency = _extract_first_string(ref_obj.get("Agency") or ref_obj.get("agency"))
        rid = _extract_first_string(ref_obj.get("ID") or ref_obj.get("id"))
        ver = _extract_first_string(ref_obj.get("Version") or ref_obj.get("version")) or "1.0.0"
        if agency and rid:
            return f"urn:ddi:{agency}:{rid}:{ver}"
    return None


def _extract_ref_urn_list(ref_obj: Any) -> list[str]:
    """Extract all referenced URNs from a reference field."""
    if ref_obj is None:
        return []
    if isinstance(ref_obj, list):
        res = []
        for item in ref_obj:
            u = _extract_ref_urn(item)
            if u:
                res.append(u)
        return res
    u = _extract_ref_urn(ref_obj)
    return [u] if u else []


def compute_resource_hashes(
    resource_type: str, normalized_fields: dict[str, Any]
) -> dict[str, str]:
    """Compute deterministic SHA-256 content and facet hashes for a normalized resource."""
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


def _extract_variable_stats_and_frequencies(
    raw_value: dict[str, Any], uaps: dict[str, str]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Extract summary statistics dict and category frequency rows from DDI-L 4 or DDI-C."""
    summary_stats: dict[str, Any] = {}
    frequencies: list[dict[str, Any]] = []

    if "ddi:summary_statistics" in uaps:
        try:
            parsed_stats = json.loads(uaps["ddi:summary_statistics"])
            if isinstance(parsed_stats, dict):
                summary_stats.update(parsed_stats)
            elif isinstance(parsed_stats, list):
                for s in parsed_stats:
                    if isinstance(s, dict) and s.get("type"):
                        val = s.get("value")
                        try:
                            summary_stats[str(s["type"])] = float(val) if val is not None else None
                        except (ValueError, TypeError):
                            summary_stats[str(s["type"])] = val
        except Exception:
            pass

    if "ddi:category_statistics" in uaps:
        try:
            cat_stats = json.loads(uaps["ddi:category_statistics"])
            if isinstance(cat_stats, list):
                for cs in cat_stats:
                    if isinstance(cs, dict) and cs.get("type") in ("freq", None):
                        try:
                            freq_val = float(cs.get("value", 0.0))
                        except (ValueError, TypeError):
                            continue
                        frequencies.append(
                            {
                                "code_value": str(cs.get("code_value", ""))[:128],
                                "frequency": freq_val,
                                "weight": cs.get("weight_var"),
                            }
                        )
        except Exception:
            pass

    if not summary_stats and "sumStat" in raw_value:
        raw_sums = raw_value["sumStat"]
        if isinstance(raw_sums, dict):
            raw_sums = [raw_sums]
        for s in raw_sums if isinstance(raw_sums, list) else []:
            if isinstance(s, dict):
                s_type = s.get("@type") or s.get("type")
                s_val = s.get("content") or s.get("#text")
                if s_type and s_val is not None:
                    try:
                        summary_stats[str(s_type)] = float(s_val)
                    except (ValueError, TypeError):
                        summary_stats[str(s_type)] = s_val

    if not frequencies and "catgry" in raw_value:
        raw_cats = raw_value["catgry"]
        if isinstance(raw_cats, dict):
            raw_cats = [raw_cats]
        for cat in raw_cats if isinstance(raw_cats, list) else []:
            if not isinstance(cat, dict):
                continue
            c_val_raw = cat.get("catValu")
            c_val = _extract_first_string(c_val_raw) or ""
            cat_stats = cat.get("catStat") or []
            if isinstance(cat_stats, dict):
                cat_stats = [cat_stats]
            for cs in cat_stats if isinstance(cat_stats, list) else []:
                if isinstance(cs, dict):
                    cs_type = cs.get("@type") or cs.get("type") or "freq"
                    if cs_type == "freq":
                        raw_f = cs.get("content") or cs.get("#text")
                        if raw_f is not None:
                            try:
                                frequencies.append(
                                    {
                                        "code_value": str(c_val)[:128],
                                        "frequency": float(raw_f),
                                        "weight": cs.get("@wgtd") or cs.get("wgt-var"),
                                    }
                                )
                            except (ValueError, TypeError):
                                pass

    return summary_stats, frequencies


def _extract_ddil33_variable_statistics(
    raw_value: dict[str, Any],
) -> tuple[str | None, dict[str, Any], list[dict[str, Any]]]:
    """Parse a DDI-L 3.3 `VariableStatistics` element into (var_urn, summary_dict, freq_list)."""
    var_ref_urn = _extract_ref_urn(
        raw_value.get("VariableReference") or raw_value.get("variable_reference")
    )
    if var_ref_urn:
        var_ref_urn = parse_ddi_urn(var_ref_urn)[0]

    summary_stats: dict[str, Any] = {}
    frequencies: list[dict[str, Any]] = []

    sum_items = raw_value.get("SummaryStatistic") or raw_value.get("summary_statistic") or []
    if isinstance(sum_items, dict):
        sum_items = [sum_items]
    for s in sum_items if isinstance(sum_items, list) else []:
        if isinstance(s, dict):
            s_type = _extract_first_string(
                s.get("TypeOfSummaryStatistic") or s.get("type_of_summary_statistic")
            )
            stat_entry = s.get("Statistic") or s.get("statistic") or s
            s_val = _extract_first_string(stat_entry)
            if s_type and s_val is not None:
                try:
                    summary_stats[s_type] = float(s_val)
                except (ValueError, TypeError):
                    summary_stats[s_type] = s_val

    cat_items = (
        raw_value.get("UnfilteredCategoryStatistics")
        or raw_value.get("FilteredCategoryStatistics")
        or raw_value.get("CategoryStatistics")
        or []
    )
    if isinstance(cat_items, dict):
        cat_items = [cat_items]
    for block in cat_items if isinstance(cat_items, list) else []:
        if not isinstance(block, dict):
            continue
        inner = block.get("StatisticsCategory") or block.get("CategoryStatistic") or [block]
        if isinstance(inner, dict):
            inner = [inner]
        for entry in inner if isinstance(inner, list) else []:
            if not isinstance(entry, dict):
                continue
            code_val = _extract_first_string(entry.get("CategoryValue") or entry.get("CodeValue"))
            cs_list = entry.get("CategoryStatistic") or [entry]
            if isinstance(cs_list, dict):
                cs_list = [cs_list]
            for cs in cs_list if isinstance(cs_list, list) else []:
                if not isinstance(cs, dict):
                    continue
                cs_type = _extract_first_string(
                    cs.get("TypeOfCategoryStatistic") or cs.get("type_of_category_statistic")
                )
                if cs_type and "freq" not in cs_type.lower() and "count" not in cs_type.lower():
                    continue
                stat_node = cs.get("Statistic") or cs.get("Value") or cs
                f_str = _extract_first_string(stat_node)
                if code_val is not None and f_str is not None:
                    try:
                        frequencies.append(
                            {
                                "code_value": str(code_val)[:128],
                                "frequency": float(f_str),
                                "weight": None,
                            }
                        )
                    except (ValueError, TypeError):
                        pass

    return var_ref_urn, summary_stats, frequencies


def _normalize_node(
    resource_type: str,
    raw_urn: str,
    raw_value: dict[str, Any],
) -> dict[str, Any]:
    """Extract normalized fields for an incoming resource node across DDI 4/3.3/2.5."""
    canonical_urn, agency, identifier, version = parse_ddi_urn(raw_urn)
    uaps = _extract_user_attributes(raw_value)

    name_ml = (
        _extract_multilingual(raw_value.get("VariableName") or raw_value.get("variable_name"))
        or _extract_multilingual(
            raw_value.get("QuestionItemName") or raw_value.get("question_item_name")
        )
        or _extract_multilingual(raw_value.get("CodeListName") or raw_value.get("code_list_name"))
        or _extract_multilingual(raw_value.get("CategoryName") or raw_value.get("category_name"))
        or _extract_multilingual(raw_value.get("ConceptName") or raw_value.get("concept_name"))
        or _extract_multilingual(
            raw_value.get("VariableGroupName") or raw_value.get("variable_group_name")
        )
        or _extract_multilingual(
            raw_value.get("InstrumentName") or raw_value.get("instrument_name")
        )
        or _extract_multilingual(
            raw_value.get(f"{resource_type}Name")
            or raw_value.get(f"{resource_type[0].lower()}{resource_type[1:]}_name")
            if resource_type.endswith("Scheme")
            else None
        )
    )
    name_str = (
        next(iter(name_ml.values()))
        if name_ml
        else (
            raw_value.get("@name")
            or raw_value.get("name")
            or raw_value.get("code_list_name")
            or identifier
        )
    )
    name_str = str(name_str)[:255]

    label_ml = _extract_multilingual(
        raw_value.get("label") or raw_value.get("Label") or raw_value.get("labl")
    )
    desc_ml = _extract_multilingual(
        raw_value.get("description") or raw_value.get("Description") or raw_value.get("txt")
    )

    if (
        resource_type == "Category"
        and "category" in raw_value
        and isinstance(raw_value["category"], dict)
    ):
        cat_inner = raw_value["category"]
        label_ml = label_ml or _extract_multilingual(
            cat_inner.get("label")
            or cat_inner.get("Label")
            or cat_inner.get("labl")
            or cat_inner.get("catValu")
        )
        desc_ml = desc_ml or _extract_multilingual(
            cat_inner.get("description") or cat_inner.get("Description") or cat_inner.get("txt")
        )

    question_text_ml = None
    interviewer_instr_ml = None
    if resource_type == "QuestionItem":
        question_text_ml = (
            _extract_multilingual(raw_value.get("question_text") or raw_value.get("QuestionText"))
            or label_ml
        )
        if "ddi:interviewer_instructions" in uaps:
            try:
                instr_data = json.loads(uaps["ddi:interviewer_instructions"])
                interviewer_instr_ml = _extract_multilingual(instr_data)
            except Exception:
                interviewer_instr_ml = {"en": uaps["ddi:interviewer_instructions"]}

    codes_list: list[dict[str, Any]] = []
    if resource_type == "CodeList":
        raw_codes = raw_value.get("Code") or raw_value.get("code") or []
        if isinstance(raw_codes, dict):
            raw_codes = [raw_codes]
        for idx, c in enumerate(raw_codes, start=1):
            if not isinstance(c, dict):
                continue
            c_val = _extract_first_string(c.get("Value") or c.get("value")) or str(idx)
            cat_ref_urn = _extract_ref_urn(
                c.get("CategoryReference") or c.get("category_reference")
            )
            if cat_ref_urn:
                cat_ref_urn = parse_ddi_urn(cat_ref_urn)[0]
            codes_list.append(
                {
                    "value": c_val,
                    "category_urn": cat_ref_urn,
                    "order": idx,
                    "is_missing": False,
                }
            )
        if (
            not codes_list
            and "categories" in raw_value
            and isinstance(raw_value["categories"], list)
        ):
            for idx, cat_u in enumerate(raw_value["categories"], start=1):
                c_urn = parse_ddi_urn(str(cat_u))[0]
                val_part = (
                    str(cat_u).split(":")[-2].rsplit("-", 1)[-1] if "-" in str(cat_u) else str(idx)
                )
                codes_list.append(
                    {
                        "value": val_part,
                        "category_urn": c_urn,
                        "order": idx,
                        "is_missing": False,
                    }
                )

    codelist_urn = None
    question_urns: list[str] = []
    concept_urn = None
    represented_var_urn = None
    value_rep: dict[str, Any] | None = None
    summary_stats: dict[str, Any] = {}
    frequencies: list[dict[str, Any]] = []

    if resource_type in ("Variable", "RepresentedVariable", "InstanceVariable"):
        var_rep = raw_value.get("VariableRepresentation") or raw_value.get("Representation") or {}
        if isinstance(var_rep, dict):
            val_rep_inner = (
                var_rep.get("ValueRepresentation") or var_rep.get("CodeRepresentation") or var_rep
            )
            if isinstance(val_rep_inner, dict):
                codelist_urn = _extract_ref_urn(
                    val_rep_inner.get("CodeListReference") or var_rep.get("CodeListReference")
                )
                if not codelist_urn:
                    value_rep = val_rep_inner
        if codelist_urn:
            codelist_urn = parse_ddi_urn(codelist_urn)[0]

        q_refs = _extract_ref_urn_list(
            raw_value.get("QuestionReference") or raw_value.get("question_reference")
        )
        question_urns = [parse_ddi_urn(u)[0] for u in q_refs]
        if not question_urns and "qstn" in raw_value:
            question_text_ml = _extract_multilingual(raw_value["qstn"])

        c_ref = _extract_ref_urn(
            raw_value.get("ConceptReference") or raw_value.get("ConceptualVariableReference")
        )
        if c_ref:
            concept_urn = parse_ddi_urn(c_ref)[0]

        rv_ref = _extract_ref_urn(
            raw_value.get("RepresentedVariableReference")
            or raw_value.get("represented_variable_reference")
        )
        if rv_ref:
            represented_var_urn = parse_ddi_urn(rv_ref)[0]

        summary_stats, frequencies = _extract_variable_stats_and_frequencies(raw_value, uaps)

    citation_ml = None
    abstract_ml = None
    if resource_type == "StudyUnit":
        cit = raw_value.get("Citation") or raw_value.get("stdyDscr", {}).get("citation", {})
        if isinstance(cit, dict):
            title_ml = _extract_multilingual(
                cit.get("Title") or cit.get("titlStmt", {}).get("titl")
            )
            if title_ml:
                label_ml = label_ml or title_ml
                citation_ml = {"title": title_ml}
        abstract_ml = _extract_multilingual(raw_value.get("Abstract"))

    hash_fields: dict[str, Any] = {
        "name": name_str,
        "label": label_ml,
        "description": desc_ml,
    }
    if question_text_ml:
        hash_fields["question_text"] = question_text_ml
    if interviewer_instr_ml:
        hash_fields["interviewer_instructions"] = interviewer_instr_ml
    if codes_list:
        hash_fields["codes"] = [
            {"value": c["value"], "category_urn": c["category_urn"]} for c in codes_list
        ]
    if codelist_urn:
        hash_fields["codelist_urn"] = codelist_urn
    if question_urns:
        hash_fields["question_urns"] = question_urns

    hashes = compute_resource_hashes(resource_type, hash_fields)

    return {
        "canonical_urn": canonical_urn,
        "agency": agency,
        "identifier": identifier,
        "version": version,
        "name": name_str,
        "name_ml": name_ml or {"en": name_str},
        "label": label_ml,
        "description": desc_ml,
        "question_text": question_text_ml,
        "interviewer_instructions": interviewer_instr_ml,
        "codes": codes_list,
        "codelist_urn": codelist_urn,
        "question_urns": question_urns,
        "concept_urn": concept_urn,
        "represented_variable_urn": represented_var_urn,
        "value_representation": value_rep,
        "summary_stats": summary_stats,
        "frequencies": frequencies,
        "citation": citation_ml,
        "abstract": abstract_ml,
        "user_attributes": uaps,
        "hashes": hashes,
    }


CORE_RESOURCE_TYPES = {
    "CategoryScheme",
    "Category",
    "CodeListScheme",
    "CodeList",
    "QuestionScheme",
    "QuestionItem",
    "ConceptScheme",
    "Concept",
    "ConceptualVariableScheme",
    "ConceptualVariable",
    "RepresentedVariableScheme",
    "RepresentedVariable",
    "VariableScheme",
    "VariableGroup",
    "Variable",
    "InstanceVariable",
    "InstrumentScheme",
    "Instrument",
    "StudyUnit",
    "PhysicalInstance",
}


def _get_existing_content_hash(urn: str) -> str | None:
    """Return existing `hashes['content']` for a URN in UrnRegistry if it is a versionable item."""
    from fairwddi.models import (
        Category,
        CodeList,
        Concept,
        ConceptualVariable,
        Datafile,
        InstanceVariable,
        Instrument,
        QuestionItem,
        RepresentedVariable,
        StudyUnit,
        VariableGroup,
    )

    for model_cls in (
        Category,
        CodeList,
        QuestionItem,
        RepresentedVariable,
        InstanceVariable,
        ConceptualVariable,
        Concept,
        StudyUnit,
        VariableGroup,
        Instrument,
        Datafile,
    ):
        obj = model_cls.objects.filter(urn=urn).only("hashes").first()
        if obj is not None and isinstance(obj.hashes, dict):
            return obj.hashes.get("content")
    return None


def _find_active_batch_by_sha256(file_sha256: str) -> Any | None:
    from fairwddi.models import IngestBatch

    return (
        IngestBatch.objects.filter(file_sha256=file_sha256)
        .exclude(status__in=["failed", "undone"])
        .order_by("-id")
        .first()
    )


def _plan_harmonizable_resource(
    *,
    action_id: str,
    r_type: str,
    source_urn: str,
    c_urn: str,
    norm: dict[str, Any],
    existing_urns: set[str],
    pool_by_type: dict[str, list[dict[str, Any]]],
    cat_labels: dict[str, Any],
    codelist_hashes: dict[str, str],
    codelist_pairs_cache: dict[str, list[tuple[str, str]]],
    lineage_map: dict[str, set[str]],
    match_threshold: float,
    action_counts: dict[str, int],
    issues: list[PlanIssue],
    extra_details: dict[str, Any] | None = None,
    notes_suffix: str = "",
) -> PlanActionItem:
    """Plan creation + two-tier origin matching or same-URN collision check for one resource."""
    c_hash = norm["hashes"]["content"]
    details: dict[str, Any] = {
        "raw_urn": source_urn,
        "canonical_urn": c_urn,
        "content_hash": c_hash,
        "name": norm["name"],
        "origin": "imported",
        **(extra_details or {}),
    }

    if c_urn in existing_urns:
        existing_hash = _get_existing_content_hash(c_urn)
        if existing_hash is None or existing_hash == c_hash:
            act_type = "reuse"
            target_urn = c_urn
            req_review = True
            notes = (
                f"Same-URN collision: {r_type} '{c_urn}' already exists with identical content. "
                "Review to confirm cross-file reuse."
            )
            issues.append(
                PlanIssue(
                    severity="warning",
                    code="ING-URN-REUSE-001",
                    resource_type=r_type,
                    resource_urn=c_urn,
                    message=notes,
                    requires_review=False,
                )
            )
        else:
            act_type = "quarantine"
            target_urn = c_urn
            req_review = True
            notes = (
                f"Content drift detected on existing URN "
                f"(existing={existing_hash[:19]}, incoming={c_hash[:19]})."
            )
            issues.append(
                PlanIssue(
                    severity="warning",
                    code="ING-DRIFT-001",
                    resource_type=r_type,
                    resource_urn=c_urn,
                    message=notes,
                    requires_review=False,
                )
            )
        action_counts[act_type] = action_counts.get(act_type, 0) + 1
        return PlanActionItem(
            id=action_id,
            stage="ingest",
            action=act_type,  # type: ignore[arg-type]
            resource_type=r_type,
            source_urn=source_urn,
            target_urn=target_urn,
            confidence=1.0,
            requires_review=req_review,
            details=details,
            notes=notes,
        )

    # New URN: always create as imported, and evaluate two-tier matching if harmonizable
    existing_urns.add(c_urn)
    if r_type not in HARMONIZABLE_RESOURCE_TYPES:
        action_counts["create"] = action_counts.get("create", 0) + 1
        return PlanActionItem(
            id=action_id,
            stage="ingest",
            action="create",
            resource_type=r_type,
            source_urn=source_urn,
            target_urn=c_urn,
            confidence=1.0,
            requires_review=False,
            details=details,
            notes=f"Create {r_type} (origin='imported'){notes_suffix}.",
        )

    inc_rec = build_comparison_record(
        r_type,
        c_urn,
        norm,
        origin="imported",
        cat_labels=cat_labels,
        codelist_hashes=codelist_hashes,
    )
    if r_type == "CodeList" and inc_rec.get("codes"):
        codelist_pairs_cache[c_urn] = [(v, lbl) for v, lbl, _ in inc_rec["codes"]]

    pool = pool_by_type.setdefault(r_type, [])
    match = find_best_match_for_incoming(
        inc_rec,
        pool,
        threshold=match_threshold,
        codes_cache=codelist_pairs_cache,
        lineage_map=lineage_map,
        agency=norm.get("agency"),
    )

    if match and match["recommended_action"] == "link_existing":
        act_type = "link_existing"
        target_urn = match["target_urn"]
        conf = match["confidence"]
        m_type = match["match_type"]
        req_rev = bool(match["requires_review"])
        inc_rec["harmonized_targets"] = [target_urn]
        lineage_map.setdefault(c_urn, set()).add(target_urn)
        pool.append(inc_rec)
        details.update(match["details"])
        notes = (
            f"Create {r_type} (imported) and link to existing "
            f"{match['details'].get('target_origin', 'harmonized')} '{target_urn}' ({m_type})."
        )
    elif match and match["recommended_action"] == "generate_harmonized":
        act_type = "generate_harmonized"
        target_urn = match["target_urn"]
        gen_urn = match["details"]["generated_urn"]
        conf = match["confidence"]
        m_type = match["match_type"]
        req_rev = bool(match["requires_review"])

        # Mark matched imported record as now having a harmonized target so subsequent
        # items in the same batch match the generated resource in Tier 1!
        for rec in pool:
            if rec["urn"] == target_urn:
                rec.setdefault("harmonized_targets", []).append(gen_urn)
                break
        inc_rec["harmonized_targets"] = [gen_urn]
        lineage_map.setdefault(target_urn, set()).add(gen_urn)
        lineage_map.setdefault(c_urn, set()).add(gen_urn)
        pool.append(inc_rec)

        # Register synthetic generated record in Tier 1 pool for intra-batch chaining
        gen_rec = dict(inc_rec)
        gen_rec["urn"] = gen_urn
        gen_rec["origin"] = "generated"
        gen_rec["harmonized_targets"] = []
        if match["details"].get("canonical_text"):
            gen_rec["text"] = match["details"]["canonical_text"]
        pool.append(gen_rec)

        details.update(match["details"])
        notes = (
            f"Create {r_type} (imported) + new generated '{gen_urn}' "
            f"harmonizing '{target_urn}' & '{c_urn}' ({m_type})."
        )
    else:
        act_type = "create"
        target_urn = c_urn
        conf = 1.0
        m_type = None
        req_rev = False
        pool.append(inc_rec)
        notes = f"Create {r_type} (origin='imported'){notes_suffix}."

    action_counts[act_type] = action_counts.get(act_type, 0) + 1
    return PlanActionItem(
        id=action_id,
        stage="ingest",
        action=act_type,  # type: ignore[arg-type]
        resource_type=r_type,
        source_urn=source_urn,
        target_urn=target_urn,
        confidence=conf,
        match_type=m_type,
        requires_review=req_rev,
        details=details,
        notes=notes,
    )


def plan_ingestion(
    file_path: str | Path,
    profile: str | Path | ImportProfile = "request",
    output_dir: str | Path | None = None,
    force_reload: bool = False,
    auto_approve: bool = False,
    match_threshold: float = 0.75,
) -> IngestPlan:
    """Stream a metadata file in memory and build a review-gated Ingestion Plan (zero DB writes)."""
    from fairwddi.models import Category, CodeList, SemanticRelationship, UrnRegistry

    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Metadata file not found: {path}")

    resolved_profile = profile if isinstance(profile, ImportProfile) else load_profile(profile)
    fmt = detect_metadata_format(path)
    file_sha256 = compute_file_sha256(path)
    active_batch = _find_active_batch_by_sha256(file_sha256)
    existing_batch = None if force_reload else active_batch
    replaced_urns: set[str] = (
        set(active_batch.created_urns or []) | set(active_batch.generated_urns or [])
        if force_reload and active_batch is not None
        else set()
    )

    nodes = list(stream_resources(path, resolved_profile, format_info=fmt))
    existing_urns = set(UrnRegistry.objects.values_list("urn", flat=True)) - replaced_urns

    pool_by_type: dict[str, list[dict[str, Any]]] = {
        rt: [
            {
                **rec,
                "harmonized_targets": [
                    u for u in rec.get("harmonized_targets", []) if u not in replaced_urns
                ],
            }
            for rec in _load_resource_records(rt)
            if rec["urn"] not in replaced_urns
        ]
        for rt in HARMONIZABLE_RESOURCE_TYPES
    }
    cat_labels: dict[str, Any] = {
        cat.urn: cat.label
        for cat in Category.objects.only("urn", "label")
        if cat.label and cat.urn not in replaced_urns
    }
    codelist_hashes: dict[str, str] = {
        cl.urn: (cl.hashes.get("codes") or cl.hashes.get("content") or "")
        for cl in CodeList.objects.only("urn", "hashes")
        if isinstance(cl.hashes, dict) and cl.urn not in replaced_urns
    }
    codelist_pairs_cache: dict[str, list[tuple[str, str]]] = {}
    lineage_map: dict[str, set[str]] = {}
    for subj_u, obj_u in SemanticRelationship.objects.filter(
        predicate="prov:wasDerivedFrom"
    ).values_list("subject_urn", "object_urn"):
        if subj_u not in replaced_urns and obj_u not in replaced_urns:
            lineage_map.setdefault(obj_u, set()).add(subj_u)

    actions: list[PlanActionItem] = []
    issues: list[PlanIssue] = []
    skipped_types: set[str] = set()
    action_counts: dict[str, int] = {
        "create": 0,
        "link_existing": 0,
        "generate_harmonized": 0,
        "reuse": 0,
        "quarantine": 0,
        "skip": 0,
    }
    planned_frequency_rows = 0
    planned_summary_stat_vars = 0

    if existing_batch is not None:
        issues.append(
            PlanIssue(
                severity="warning",
                code="ING-DUP-001",
                message=(
                    f"File with identical SHA-256 was already ingested in "
                    f"IngestBatch #{existing_batch.id}. Pass --force-reload to re-ingest."
                ),
                requires_review=True,
            )
        )

    act_seq = 0
    for node in nodes:
        r_type = node.resource_type
        if r_type == "VariableStatistics":
            _, s_dict, f_list = _extract_ddil33_variable_statistics(node.raw_value)
            if s_dict:
                planned_summary_stat_vars += 1
            planned_frequency_rows += len(f_list)
            continue

        if r_type not in CORE_RESOURCE_TYPES:
            act_seq += 1
            action_counts["skip"] += 1
            skipped_types.add(r_type)
            actions.append(
                PlanActionItem(
                    id=f"ing-{act_seq:04d}",
                    stage="ingest",
                    action="skip",
                    resource_type=r_type,
                    source_urn=node.raw_urn,
                    target_urn=None,
                    confidence=1.0,
                    requires_review=False,
                    details={"raw_urn": node.raw_urn, "type": r_type},
                    notes=(
                        f"Non-core structural container wrapper '{r_type}' skipped "
                        f"(enclosed schemes and entities are ingested into core tables)."
                    ),
                )
            )
            continue

        norm = _normalize_node(r_type, node.raw_urn, node.raw_value)
        c_urn = norm["canonical_urn"]
        if norm["summary_stats"]:
            planned_summary_stat_vars += 1
        planned_frequency_rows += len(norm["frequencies"])

        if r_type == "Category" and norm["label"]:
            cat_labels[c_urn] = norm["label"]
        elif r_type == "CodeList":
            codelist_hashes[c_urn] = norm["hashes"].get("codes") or norm["hashes"]["content"]

        if r_type == "Variable":
            # Synthesize study-specific imported RepresentedVariable (+ optional QuestionItem)
            rv_urn = norm["represented_variable_urn"] or (
                f"urn:ddi:{norm['agency']}:rv_{norm['identifier']}:{norm['version']}"
            )
            inline_q_urn: str | None = None
            if not norm["question_urns"] and norm["question_text"]:
                inline_q_urn = f"urn:ddi:{norm['agency']}:qi_{norm['identifier']}:{norm['version']}"
                q_payload = {
                    "name": f"q_{norm['name']}",
                    "label": norm["question_text"],
                    "question_text": norm["question_text"],
                }
                q_hashes = compute_resource_hashes("QuestionItem", q_payload)
                q_norm = {**q_payload, "agency": norm["agency"], "hashes": q_hashes}
                act_seq += 1
                actions.append(
                    _plan_harmonizable_resource(
                        action_id=f"ing-{act_seq:04d}",
                        r_type="QuestionItem",
                        source_urn=inline_q_urn,
                        c_urn=inline_q_urn,
                        norm=q_norm,
                        existing_urns=existing_urns,
                        pool_by_type=pool_by_type,
                        cat_labels=cat_labels,
                        codelist_hashes=codelist_hashes,
                        codelist_pairs_cache=codelist_pairs_cache,
                        lineage_map=lineage_map,
                        match_threshold=match_threshold,
                        action_counts=action_counts,
                        issues=issues,
                        extra_details={"synthesized_from_variable": c_urn},
                    )
                )

            rv_q_urns = [inline_q_urn] if inline_q_urn else norm["question_urns"]
            rv_codelist_urn = norm["codelist_urn"]
            if rv_codelist_urn is None and node.referenced_urns:
                for ref_u in node.referenced_urns:
                    parsed_ref = parse_ddi_urn(ref_u)[0]
                    if parsed_ref in codelist_hashes:
                        rv_codelist_urn = parsed_ref
                        break
            rv_payload = {
                "name": norm["name"],
                "label": norm["label"],
                "description": norm["description"],
                "codelist_urn": rv_codelist_urn,
                "question_urns": rv_q_urns,
                "value_representation": norm["value_representation"],
            }
            rv_hashes = compute_resource_hashes("RepresentedVariable", rv_payload)
            rv_norm = {**rv_payload, "agency": norm["agency"], "hashes": rv_hashes}
            act_seq += 1
            actions.append(
                _plan_harmonizable_resource(
                    action_id=f"ing-{act_seq:04d}",
                    r_type="RepresentedVariable",
                    source_urn=rv_urn,
                    c_urn=rv_urn,
                    norm=rv_norm,
                    existing_urns=existing_urns,
                    pool_by_type=pool_by_type,
                    cat_labels=cat_labels,
                    codelist_hashes=codelist_hashes,
                    codelist_pairs_cache=codelist_pairs_cache,
                    lineage_map=lineage_map,
                    match_threshold=match_threshold,
                    action_counts=action_counts,
                    issues=issues,
                    extra_details={"synthesized_from_variable": c_urn},
                )
            )

            var_extra: dict[str, Any] = {
                "instance_variable_urn": c_urn,
                "represented_variable_urn": rv_urn,
            }
            if inline_q_urn:
                var_extra["inline_question_urn"] = inline_q_urn
            if norm["frequencies"]:
                var_extra["frequency_count"] = len(norm["frequencies"])
            if norm["summary_stats"]:
                var_extra["summary_stats"] = norm["summary_stats"]

            freq_parts: list[str] = []
            if norm["frequencies"]:
                freq_parts.append(f"{len(norm['frequencies'])} frequency rows")
            if norm["summary_stats"]:
                freq_parts.append("summary stats")
            extra_note = f" [{', '.join(freq_parts)}]" if freq_parts else ""

            act_seq += 1
            actions.append(
                _plan_harmonizable_resource(
                    action_id=f"ing-{act_seq:04d}",
                    r_type="Variable",
                    source_urn=node.raw_urn,
                    c_urn=c_urn,
                    norm=norm,
                    existing_urns=existing_urns,
                    pool_by_type=pool_by_type,
                    cat_labels=cat_labels,
                    codelist_hashes=codelist_hashes,
                    codelist_pairs_cache=codelist_pairs_cache,
                    lineage_map=lineage_map,
                    match_threshold=match_threshold,
                    action_counts=action_counts,
                    issues=issues,
                    extra_details=var_extra,
                    notes_suffix=(
                        f" -> InstanceVariable + RepresentedVariable ({rv_urn}){extra_note}"
                    ),
                )
            )
            continue

        act_seq += 1
        actions.append(
            _plan_harmonizable_resource(
                action_id=f"ing-{act_seq:04d}",
                r_type=r_type,
                source_urn=node.raw_urn,
                c_urn=c_urn,
                norm=norm,
                existing_urns=existing_urns,
                pool_by_type=pool_by_type,
                cat_labels=cat_labels,
                codelist_hashes=codelist_hashes,
                codelist_pairs_cache=codelist_pairs_cache,
                lineage_map=lineage_map,
                match_threshold=match_threshold,
                action_counts=action_counts,
                issues=issues,
            )
        )

    job_id = f"ingest-{path.stem}-{uuid.uuid4().hex[:6]}"
    plan = IngestPlan(
        stage="ingest",
        job_id=job_id,
        source_file=path.name,
        source_path=str(path),
        source_format=fmt.canonical_slug,
        file_sha256=file_sha256,
        batch_id=existing_batch.id if existing_batch else None,
        profile=resolved_profile.name,
        summary={
            "streamed_nodes": len(nodes),
            "planned_actions": len(actions),
            "planned_frequency_rows": planned_frequency_rows,
            "planned_summary_stat_variables": planned_summary_stat_vars,
            **action_counts,
            "skipped_types": sorted(skipped_types),
        },
        issues=issues,
        actions=actions,
        review_gate=ReviewGate(approved=auto_approve),
    )
    if plan.is_ready_to_execute(auto_approve=auto_approve):
        plan.review_gate.approved = True

    if output_dir is not None:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        plan.to_yaml(out_dir / f"{path.stem}.ingest.plan.yaml")
        plan.to_markdown(out_dir / f"{path.stem}.ingest.report.md")

    return plan


def _extract_datafile_attributes(
    raw_val: dict[str, Any], pi_norm: dict[str, Any]
) -> tuple[str, list[dict[str, Any]]]:
    """Extract filename and extended attributes from a PhysicalInstance or DDI-C fileDscr."""
    pi_uaps = pi_norm["user_attributes"]
    raw_file_txt = raw_val.get("fileTxt")
    if isinstance(raw_file_txt, list) and raw_file_txt:
        raw_file_txt = raw_file_txt[0]
    file_txt = raw_file_txt if isinstance(raw_file_txt, dict) else {}
    ddic_fname = _extract_first_string(file_txt.get("fileName")) if file_txt else None
    f_name = pi_uaps.get("ddi:file_name") or ddic_fname or pi_norm["name"]
    ext_attrs: list[dict[str, Any]] = [{"type": "file_name", "value": f_name}]

    f_id = pi_uaps.get("ddi:file_id") or raw_val.get("@ID") or raw_val.get("ID")
    if f_id:
        ext_attrs.append({"type": "file_id", "value": str(f_id)})

    raw_dimensns = file_txt.get("dimensns")
    if isinstance(raw_dimensns, list) and raw_dimensns:
        raw_dimensns = raw_dimensns[0]
    dimensns = raw_dimensns if isinstance(raw_dimensns, dict) else {}
    case_cnt = pi_uaps.get("ddi:case_count") or _extract_first_string(dimensns.get("caseQnty"))
    if case_cnt and str(case_cnt).isdigit():
        ext_attrs.append({"type": "case_count", "value": int(case_cnt)})

    var_cnt = pi_uaps.get("ddi:var_count") or _extract_first_string(dimensns.get("varQnty"))
    if var_cnt and str(var_cnt).isdigit():
        ext_attrs.append({"type": "variable_count", "value": int(var_cnt)})

    return str(f_name)[:255], ext_attrs


def apply_ingestion(
    file_or_plan: str | Path | IngestPlan,
    profile: str | Path | ImportProfile = "request",
    force_reload: bool = False,
    auto_approve: bool = False,
) -> dict[str, Any]:
    """Stream a metadata file into ReQuest core tables and execute planned lineage harmonization."""
    from fairwddi.ingest.harmonizer import (
        create_harmonized_resource,
        link_to_harmonized_resource,
    )
    from fairwddi.models import (
        Category,
        CategoryScheme,
        CodeItem,
        CodeList,
        Concept,
        ConceptScheme,
        ConceptualVariable,
        ConceptualVariableScheme,
        Datafile,
        DatafileVariable,
        DatafileVariableFrequency,
        IngestBatch,
        InstanceVariable,
        Instrument,
        InstrumentQuestion,
        MetadataQuarantine,
        QuestionItem,
        QuestionScheme,
        QuestionVariable,
        RepresentedVariable,
        RepresentedVariableScheme,
        SemanticRelationship,
        StudyInstrument,
        StudyUnit,
        UrnRegistry,
        VariableGroup,
        VariableScheme,
    )

    if isinstance(file_or_plan, IngestPlan):
        plan = file_or_plan
    else:
        candidate_path = Path(file_or_plan)
        if candidate_path.name.endswith((".plan.yaml", ".plan.yml")):
            plan = IngestPlan.from_yaml(candidate_path)
        else:
            plan = plan_ingestion(
                candidate_path,
                profile=profile,
                force_reload=force_reload,
                auto_approve=auto_approve,
            )

    if not plan.source_path:
        raise ValueError("Ingestion plan is missing `source_path` to stream.")

    src_path = Path(plan.source_path)
    if not src_path.exists():
        raise FileNotFoundError(f"Source file referenced by plan not found: {src_path}")

    current_sha = compute_file_sha256(src_path)
    if plan.file_sha256 and current_sha != plan.file_sha256:
        raise ValueError(
            f"SHA-256 mismatch for '{src_path.name}': file changed since plan generation."
        )

    existing_batch = _find_active_batch_by_sha256(current_sha)
    if existing_batch is not None and not force_reload:
        return {
            "job_id": plan.job_id,
            "batch_id": existing_batch.id,
            "status": "already_ingested",
            "created_count": 0,
            "generated_count": 0,
            "linked_count": 0,
            "reused_count": len(existing_batch.reused_urns or []),
            "quarantine_count": 0,
            "frequency_rows_count": 0,
        }

    if not plan.is_ready_to_execute(auto_approve=auto_approve):
        raise PermissionError(
            f"Ingestion plan '{plan.job_id}' has {plan.pending_review_count} pending review "
            f"item(s) and {plan.error_count} error(s). Approve the plan YAML "
            f"(review_gate.approved: true) or pass --auto-approve."
        )

    if existing_batch is not None and force_reload:
        undo_ingestion(existing_batch.id)

    resolved_profile = (
        profile if isinstance(profile, ImportProfile) else load_profile(plan.profile or profile)
    )
    fmt = detect_metadata_format(src_path)
    nodes = list(stream_resources(src_path, resolved_profile, format_info=fmt))

    nodes_by_type: dict[str, list[RawResourceNode]] = {}
    for n in nodes:
        nodes_by_type.setdefault(n.resource_type, []).append(n)

    action_by_key: dict[tuple[str, str], PlanActionItem] = {
        (act.resource_type, act.source_urn): act for act in plan.actions
    }
    action_by_source_urn: dict[str, PlanActionItem] = {act.source_urn: act for act in plan.actions}

    created_urns: list[str] = []
    generated_urns: list[str] = []
    linked_urns: list[str] = []
    reused_urns: list[str] = []
    quarantine_ids: list[int] = []
    harmonize_sub_job_ids: list[str] = []
    created_rel_ids: list[int] = []
    entity_counts: dict[str, int] = {}

    def _inc(entity_name: str, amount: int = 1) -> None:
        if amount > 0:
            entity_counts[entity_name] = entity_counts.get(entity_name, 0) + amount

    def _lookup_action(resource_type: str, raw_urn: str) -> PlanActionItem | None:
        return action_by_key.get((resource_type, raw_urn)) or action_by_source_urn.get(raw_urn)

    def _register_or_check(
        resource_type: str,
        raw_urn: str,
        canonical_urn: str,
        hashes: dict[str, str],
        raw_value: dict[str, Any],
    ) -> tuple[str, str]:
        act = _lookup_action(resource_type, raw_urn)
        act_type = act.action if act else "create"

        if act_type == "quarantine":
            existing_hash = _get_existing_content_hash(canonical_urn) or "unknown"
            mq = MetadataQuarantine.objects.create(
                incoming_urn=canonical_urn,
                existing_urn=canonical_urn,
                entity_type=resource_type,
                existing_content_hash=existing_hash[:64],
                incoming_content_hash=hashes["content"][:64],
                incoming_content=raw_value,
                conflict_type="hash_mismatch",
                source_file=src_path.name,
            )
            quarantine_ids.append(mq.id)
            return "quarantine", canonical_urn

        if act_type == "reuse" or UrnRegistry.objects.filter(urn=canonical_urn).exists():
            if canonical_urn not in reused_urns:
                reused_urns.append(canonical_urn)
            return "reuse", canonical_urn

        return "create", canonical_urn

    with transaction.atomic():
        # 1. StudyUnit & Datafile (PhysicalInstance)
        primary_study: StudyUnit | None = None
        primary_datafile: Datafile | None = None

        for node in nodes_by_type.get("StudyUnit", []):
            norm = _normalize_node("StudyUnit", node.raw_urn, node.raw_value)
            status, c_urn = _register_or_check(
                "StudyUnit", node.raw_urn, norm["canonical_urn"], norm["hashes"], node.raw_value
            )
            if status == "create":
                primary_study = StudyUnit.objects.create(
                    urn=c_urn,
                    name=norm["name"],
                    title=norm["label"] or norm["citation"],
                    description=norm["description"] or norm["abstract"],
                    hashes=norm["hashes"],
                    origin="imported",
                )
                created_urns.append(c_urn)
                _inc("StudyUnit")
            else:
                primary_study = StudyUnit.objects.filter(urn=c_urn).first() or primary_study

            pi_refs = node.raw_value.get("PhysicalInstanceReference") or []
            if isinstance(pi_refs, dict):
                pi_refs = [pi_refs]
            for pi_dict in pi_refs:
                if isinstance(pi_dict, dict) and ("URN" in pi_dict or "ID" in pi_dict):
                    pi_urn_raw = (
                        pi_dict.get("URN")
                        or f"urn:ddi:{norm['agency']}:{pi_dict.get('ID')}:{norm['version']}"
                    )
                    pi_norm = _normalize_node("PhysicalInstance", str(pi_urn_raw), pi_dict)
                    pi_c_urn = pi_norm["canonical_urn"]
                    if primary_study and not Datafile.objects.filter(urn=pi_c_urn).exists():
                        f_name, ext_attrs = _extract_datafile_attributes(pi_dict, pi_norm)
                        primary_datafile = Datafile.objects.create(
                            urn=pi_c_urn,
                            name=f_name,
                            description=pi_norm["label"],
                            study_unit=primary_study,
                            extended_attributes=ext_attrs,
                            hashes=pi_norm["hashes"],
                            origin="imported",
                        )
                        created_urns.append(pi_c_urn)
                        _inc("Datafile")

        if primary_study is None and (
            nodes_by_type.get("Variable") or nodes_by_type.get("InstanceVariable")
        ):
            fallback_urn = f"urn:ddi:fr.cdsp:study_{current_sha[:10]}:1.0.0"
            primary_study = StudyUnit.objects.filter(urn=fallback_urn).first()
            if not primary_study:
                primary_study = StudyUnit.objects.create(
                    urn=fallback_urn,
                    name=src_path.stem[:255],
                    title={"en": src_path.stem},
                    origin="imported",
                )
                created_urns.append(fallback_urn)
                _inc("StudyUnit")

        for node in nodes_by_type.get("PhysicalInstance", []):
            pi_norm = _normalize_node("PhysicalInstance", node.raw_urn, node.raw_value)
            status, pi_c_urn = _register_or_check(
                "PhysicalInstance",
                node.raw_urn,
                pi_norm["canonical_urn"],
                pi_norm["hashes"],
                node.raw_value,
            )
            if status == "create" and primary_study:
                f_name, ext_attrs = _extract_datafile_attributes(node.raw_value, pi_norm)
                df_obj = Datafile.objects.create(
                    urn=pi_c_urn,
                    name=f_name,
                    description=pi_norm["label"],
                    study_unit=primary_study,
                    extended_attributes=ext_attrs,
                    hashes=pi_norm["hashes"],
                    origin="imported",
                )
                primary_datafile = primary_datafile or df_obj
                created_urns.append(pi_c_urn)
                _inc("Datafile")
            elif primary_datafile is None:
                primary_datafile = Datafile.objects.filter(urn=pi_c_urn).first()

        # 2. Schemes
        scheme_models = {
            "CategoryScheme": CategoryScheme,
            "QuestionScheme": QuestionScheme,
            "ConceptScheme": ConceptScheme,
            "ConceptualVariableScheme": ConceptualVariableScheme,
            "RepresentedVariableScheme": RepresentedVariableScheme,
            "VariableScheme": VariableScheme,
            "InstanceVariableScheme": VariableScheme,
        }
        for s_type, s_cls in scheme_models.items():
            for node in nodes_by_type.get(s_type, []):
                norm = _normalize_node(s_type, node.raw_urn, node.raw_value)
                status, c_urn = _register_or_check(
                    s_type, node.raw_urn, norm["canonical_urn"], norm["hashes"], node.raw_value
                )
                if status == "create":
                    s_cls.objects.create(
                        urn=c_urn,
                        name=norm["name_ml"],
                        description=norm["description"],
                        origin="imported",
                    )
                    created_urns.append(c_urn)
                    _inc(s_type)

        # 3. Concept & ConceptualVariable
        for node in nodes_by_type.get("Concept", []):
            norm = _normalize_node("Concept", node.raw_urn, node.raw_value)
            status, c_urn = _register_or_check(
                "Concept", node.raw_urn, norm["canonical_urn"], norm["hashes"], node.raw_value
            )
            if status == "create":
                Concept.objects.create(
                    urn=c_urn,
                    label=norm["label"] or {"en": norm["name"]},
                    description=norm["description"],
                    hashes=norm["hashes"],
                    origin="imported",
                )
                created_urns.append(c_urn)
                _inc("Concept")

        for node in nodes_by_type.get("ConceptualVariable", []):
            norm = _normalize_node("ConceptualVariable", node.raw_urn, node.raw_value)
            status, c_urn = _register_or_check(
                "ConceptualVariable",
                node.raw_urn,
                norm["canonical_urn"],
                norm["hashes"],
                node.raw_value,
            )
            if status == "create":
                concept_obj = (
                    Concept.objects.filter(urn=norm["concept_urn"]).first()
                    if norm["concept_urn"]
                    else None
                )
                ConceptualVariable.objects.create(
                    urn=c_urn,
                    name=norm["name"],
                    label=norm["label"],
                    description=norm["description"],
                    concept=concept_obj,
                    hashes=norm["hashes"],
                    origin="imported",
                )
                created_urns.append(c_urn)
                _inc("ConceptualVariable")

        # 4. Categories
        for node in nodes_by_type.get("Category", []):
            norm = _normalize_node("Category", node.raw_urn, node.raw_value)
            status, c_urn = _register_or_check(
                "Category", node.raw_urn, norm["canonical_urn"], norm["hashes"], node.raw_value
            )
            if status == "create":
                cat_ext: list[dict[str, Any]] = []
                if norm["description"]:
                    cat_ext.append({"type": "description", "value": norm["description"]})
                Category.objects.create(
                    urn=c_urn,
                    name=norm["name"],
                    label=norm["label"],
                    extended_attributes=cat_ext,
                    hashes=norm["hashes"],
                    origin="imported",
                )
                created_urns.append(c_urn)
                _inc("Category")

        # 5. CodeLists & CodeItems
        for node in nodes_by_type.get("CodeList", []):
            norm = _normalize_node("CodeList", node.raw_urn, node.raw_value)
            status, c_urn = _register_or_check(
                "CodeList", node.raw_urn, norm["canonical_urn"], norm["hashes"], node.raw_value
            )
            if status == "create":
                cl_obj = CodeList.objects.create(
                    urn=c_urn,
                    name=norm["name"],
                    description=norm["description"] or norm["label"],
                    hashes=norm["hashes"],
                    origin="imported",
                )
                created_urns.append(c_urn)
                _inc("CodeList")
                for c_entry in norm["codes"]:
                    cat_u = c_entry.get("category_urn")
                    if cat_u:
                        cat_obj = Category.objects.filter(urn=cat_u).first()
                        if cat_obj:
                            ci_obj, ci_created = CodeItem.objects.get_or_create(
                                code_list=cl_obj,
                                code_value=str(c_entry["value"])[:64],
                                defaults={
                                    "category": cat_obj,
                                    "order": c_entry.get("order", 1),
                                    "is_missing": bool(c_entry.get("is_missing", False)),
                                    "origin": "imported",
                                },
                            )
                            if ci_created:
                                created_urns.append(ci_obj.urn)
                                _inc("Code")

        # 6. QuestionItems
        for node in nodes_by_type.get("QuestionItem", []):
            norm = _normalize_node("QuestionItem", node.raw_urn, node.raw_value)
            status, c_urn = _register_or_check(
                "QuestionItem",
                node.raw_urn,
                norm["canonical_urn"],
                norm["hashes"],
                node.raw_value,
            )
            if status == "create":
                qi_ext: list[dict[str, Any]] = []
                if norm["interviewer_instructions"]:
                    qi_ext.append(
                        {
                            "type": "interviewer_instructions",
                            "value": norm["interviewer_instructions"],
                        }
                    )
                if norm["label"]:
                    qi_ext.append({"type": "label", "value": norm["label"]})
                if norm["description"]:
                    qi_ext.append({"type": "description", "value": norm["description"]})
                QuestionItem.objects.create(
                    urn=c_urn,
                    name=norm["name"],
                    question_text=norm["question_text"] or norm["label"],
                    extended_attributes=qi_ext,
                    hashes=norm["hashes"],
                    origin="imported",
                )
                created_urns.append(c_urn)
                _inc("QuestionItem")

        # 7. Explicit RepresentedVariables
        for node in nodes_by_type.get("RepresentedVariable", []):
            norm = _normalize_node("RepresentedVariable", node.raw_urn, node.raw_value)
            status, c_urn = _register_or_check(
                "RepresentedVariable",
                node.raw_urn,
                norm["canonical_urn"],
                norm["hashes"],
                node.raw_value,
            )
            if status == "create":
                cl_obj = (
                    CodeList.objects.filter(urn=norm["codelist_urn"]).first()
                    if norm["codelist_urn"]
                    else None
                )
                cv_obj = (
                    ConceptualVariable.objects.filter(urn=norm["concept_urn"]).first()
                    if norm["concept_urn"]
                    else None
                )
                rv_obj = RepresentedVariable.objects.create(
                    urn=c_urn,
                    name=norm["name"],
                    label=norm["label"],
                    description=norm["description"],
                    conceptual_variable=cv_obj,
                    code_list=cl_obj,
                    value_representation=norm["value_representation"],
                    hashes=norm["hashes"],
                    origin="imported",
                )
                created_urns.append(c_urn)
                _inc("RepresentedVariable")
                for idx, q_u in enumerate(norm["question_urns"], start=1):
                    q_obj = QuestionItem.objects.filter(urn=q_u).first()
                    if q_obj:
                        QuestionVariable.objects.get_or_create(
                            question_item=q_obj,
                            represented_variable=rv_obj,
                            defaults={"order": idx},
                        )

        # 8. VariableGroups
        for node in nodes_by_type.get("VariableGroup", []):
            norm = _normalize_node("VariableGroup", node.raw_urn, node.raw_value)
            status, c_urn = _register_or_check(
                "VariableGroup",
                node.raw_urn,
                norm["canonical_urn"],
                norm["hashes"],
                node.raw_value,
            )
            if status == "create":
                vg_refs = (
                    [{"resource_type": "StudyUnit", "urn": primary_study.urn}]
                    if primary_study
                    else []
                )
                VariableGroup.objects.create(
                    urn=c_urn,
                    name=norm["name"],
                    description=norm["description"] or norm["label"],
                    group_type="variable_group",
                    references=vg_refs,
                    hashes=norm["hashes"],
                    origin="imported",
                )
                created_urns.append(c_urn)
                _inc("VariableGroup")

        # 9. Variables & InstanceVariables + Synthesized RepresentedVariables + Bulk Frequencies
        freq_rows_to_insert: list[DatafileVariableFrequency] = []
        iv_by_urn: dict[str, InstanceVariable] = {}

        def _ensure_datafile(agency: str, version: str, file_id: str = "F1") -> Datafile | None:
            nonlocal primary_datafile
            if primary_datafile is not None:
                return primary_datafile
            if primary_study is None:
                return None
            existing_df = Datafile.objects.filter(study_unit=primary_study).first()
            if existing_df:
                primary_datafile = existing_df
                return existing_df
            df_urn = f"urn:ddi:{agency}:df_{primary_study.identifier}_{file_id}:{version}"
            df_obj = Datafile.objects.filter(urn=df_urn).first()
            if not df_obj:
                df_obj = Datafile.objects.create(
                    urn=df_urn,
                    name=file_id[:255],
                    study_unit=primary_study,
                    extended_attributes=[
                        {"type": "file_id", "value": file_id},
                        {"type": "file_name", "value": file_id},
                    ],
                    origin="imported",
                )
                created_urns.append(df_urn)
                _inc("Datafile")
            primary_datafile = df_obj
            return df_obj

        for var_type in ("Variable", "InstanceVariable"):
            for var_order, node in enumerate(nodes_by_type.get(var_type, []), start=1):
                norm = _normalize_node(var_type, node.raw_urn, node.raw_value)
                status, c_urn = _register_or_check(
                    var_type, node.raw_urn, norm["canonical_urn"], norm["hashes"], node.raw_value
                )
                if status == "quarantine":
                    continue

                var_act = _lookup_action(var_type, node.raw_urn)
                cl_obj = (
                    CodeList.objects.filter(urn=norm["codelist_urn"]).first()
                    if norm["codelist_urn"]
                    else None
                )
                if cl_obj is None and node.referenced_urns:
                    for ref_u in node.referenced_urns:
                        parsed_ref = parse_ddi_urn(ref_u)[0]
                        cl_obj = CodeList.objects.filter(urn=parsed_ref).first()
                        if cl_obj:
                            break

                # Resolve or create inline QuestionItem (for direct DDI-C XML)
                inline_q_obj: QuestionItem | None = None
                inline_q_urn = (
                    var_act.details.get("inline_question_urn")
                    if var_act and isinstance(var_act.details, dict)
                    else None
                )
                if not norm["question_urns"] and norm["question_text"]:
                    q_urn = (
                        inline_q_urn
                        or f"urn:ddi:{norm['agency']}:qi_{norm['identifier']}:{norm['version']}"
                    )
                    q_payload = {
                        "name": f"q_{norm['name']}",
                        "label": norm["question_text"],
                        "question_text": norm["question_text"],
                    }
                    q_hashes = compute_resource_hashes("QuestionItem", q_payload)
                    q_status, q_c_urn = _register_or_check(
                        "QuestionItem", q_urn, q_urn, q_hashes, q_payload
                    )
                    if q_status == "create":
                        inline_q_obj = QuestionItem.objects.create(
                            urn=q_c_urn,
                            name=f"q_{norm['name']}"[:255],
                            question_text=norm["question_text"],
                            hashes=q_hashes,
                            origin="imported",
                        )
                        created_urns.append(q_c_urn)
                        _inc("QuestionItem")
                    elif q_status == "reuse":
                        inline_q_obj = QuestionItem.objects.filter(urn=q_c_urn).first()

                # Resolve or create study-specific imported RepresentedVariable
                rv_urn_planned = (
                    var_act.details.get("represented_variable_urn")
                    if var_act and isinstance(var_act.details, dict)
                    else None
                )
                rv_urn = (
                    norm["represented_variable_urn"]
                    or rv_urn_planned
                    or f"urn:ddi:{norm['agency']}:rv_{norm['identifier']}:{norm['version']}"
                )
                rv_q_urns = [inline_q_obj.urn] if inline_q_obj else norm["question_urns"]
                rv_payload = {
                    "name": norm["name"],
                    "label": norm["label"],
                    "description": norm["description"],
                    "codelist_urn": cl_obj.urn if cl_obj else None,
                    "question_urns": rv_q_urns,
                    "value_representation": norm["value_representation"],
                }
                rv_hashes = compute_resource_hashes("RepresentedVariable", rv_payload)
                rv_status, rv_c_urn = _register_or_check(
                    "RepresentedVariable", rv_urn, rv_urn, rv_hashes, rv_payload
                )
                if rv_status == "create":
                    rv_obj = RepresentedVariable.objects.create(
                        urn=rv_c_urn,
                        name=norm["name"],
                        label=norm["label"],
                        description=norm["description"],
                        code_list=cl_obj,
                        value_representation=norm["value_representation"],
                        hashes=rv_hashes,
                        origin="imported",
                    )
                    created_urns.append(rv_c_urn)
                    _inc("RepresentedVariable")
                else:
                    rv_obj = RepresentedVariable.objects.filter(urn=rv_c_urn).first()

                if rv_obj and inline_q_obj:
                    QuestionVariable.objects.get_or_create(
                        question_item=inline_q_obj,
                        represented_variable=rv_obj,
                        defaults={"order": 1},
                    )
                if rv_obj:
                    for idx, q_u in enumerate(norm["question_urns"], start=1):
                        q_obj = QuestionItem.objects.filter(urn=q_u).first()
                        if q_obj:
                            QuestionVariable.objects.get_or_create(
                                question_item=q_obj,
                                represented_variable=rv_obj,
                                defaults={"order": idx},
                            )

                if status == "create" and primary_study:
                    su_ext = [{"type": "study_unit_urn", "value": primary_study.urn}]
                    iv_obj = InstanceVariable.objects.create(
                        urn=c_urn,
                        name=norm["name"],
                        label=norm["label"],
                        description=norm["description"],
                        represented_variable=rv_obj,
                        extended_attributes=su_ext,
                        hashes=norm["hashes"],
                        origin="imported",
                    )
                    created_urns.append(c_urn)
                    _inc("InstanceVariable")
                else:
                    iv_obj = InstanceVariable.objects.filter(urn=c_urn).first()

                if iv_obj:
                    iv_by_urn[c_urn] = iv_obj

                uaps = norm["user_attributes"]
                has_df_link = bool(
                    norm["summary_stats"]
                    or norm["frequencies"]
                    or "ddi:file_id" in uaps
                    or node.raw_value.get("@files")
                    or primary_datafile is not None
                )
                if iv_obj and primary_study and has_df_link:
                    file_id = (
                        uaps.get("ddi:file_id")
                        or str(node.raw_value.get("@files") or "F1").split()[0]
                    )
                    df_obj = _ensure_datafile(norm["agency"], norm["version"], file_id=file_id)
                    if df_obj:
                        _, dfv_created = DatafileVariable.objects.update_or_create(
                            datafile=df_obj,
                            instance_variable=iv_obj,
                            defaults={
                                "order": var_order,
                                "statistics": norm["summary_stats"] or {},
                            },
                        )
                        if dfv_created:
                            _inc("DatafileVariable")

                        for freq_entry in norm["frequencies"]:
                            freq_rows_to_insert.append(
                                DatafileVariableFrequency(
                                    datafile=df_obj,
                                    instance_variable=iv_obj,
                                    code_value=freq_entry["code_value"],
                                    frequency=freq_entry["frequency"],
                                    weight=freq_entry["weight"],
                                )
                            )

        # Direct DDI-L 3.3 VariableStatistics -> SQL DatafileVariable & DatafileVariableFrequency
        for vs_node in nodes_by_type.get("VariableStatistics", []):
            var_u, s_dict, f_list = _extract_ddil33_variable_statistics(vs_node.raw_value)
            if not var_u:
                continue
            iv_obj = iv_by_urn.get(var_u) or InstanceVariable.objects.filter(urn=var_u).first()
            if iv_obj and primary_study:
                df_obj = _ensure_datafile(iv_obj.agency, iv_obj.version)
                if df_obj:
                    if s_dict:
                        DatafileVariable.objects.update_or_create(
                            datafile=df_obj,
                            instance_variable=iv_obj,
                            defaults={"statistics": s_dict},
                        )
                    for freq_entry in f_list:
                        freq_rows_to_insert.append(
                            DatafileVariableFrequency(
                                datafile=df_obj,
                                instance_variable=iv_obj,
                                code_value=freq_entry["code_value"],
                                frequency=freq_entry["frequency"],
                                weight=freq_entry["weight"],
                            )
                        )

        if freq_rows_to_insert:
            DatafileVariableFrequency.objects.bulk_create(freq_rows_to_insert, batch_size=1000)
            _inc("DatafileVariableFrequency", len(freq_rows_to_insert))

        # 10. Instruments, StudyInstrument & InstrumentQuestion shortcut tables
        primary_instrument: Instrument | None = None
        for node in nodes_by_type.get("Instrument", []):
            norm = _normalize_node("Instrument", node.raw_urn, node.raw_value)
            status, c_urn = _register_or_check(
                "Instrument", node.raw_urn, norm["canonical_urn"], norm["hashes"], node.raw_value
            )
            if status == "create":
                primary_instrument = Instrument.objects.create(
                    urn=c_urn,
                    name=norm["name"],
                    label=norm["label"],
                    description=norm["description"],
                    hashes=norm["hashes"],
                    origin="imported",
                )
                created_urns.append(c_urn)
                _inc("Instrument")
            else:
                primary_instrument = (
                    Instrument.objects.filter(urn=c_urn).first() or primary_instrument
                )

            if primary_study and primary_instrument:
                StudyInstrument.objects.get_or_create(
                    study_unit=primary_study,
                    instrument=primary_instrument,
                )

        qc_nodes = nodes_by_type.get("QuestionConstruct", [])
        if qc_nodes and primary_study and primary_instrument is None:
            inst_urn = (
                f"urn:ddi:{primary_study.agency}:"
                f"inst_{primary_study.identifier}:{primary_study.version}"
            )
            primary_instrument = Instrument.objects.filter(urn=inst_urn).first()
            if not primary_instrument:
                primary_instrument = Instrument.objects.create(
                    urn=inst_urn,
                    name=f"Instrument for {primary_study.name}"[:255],
                    label=primary_study.label,
                    origin="imported",
                )
                created_urns.append(inst_urn)
                _inc("Instrument")
            StudyInstrument.objects.get_or_create(
                study_unit=primary_study,
                instrument=primary_instrument,
            )

        if primary_instrument:
            for qc_order, qc_node in enumerate(qc_nodes, start=1):
                q_ref = _extract_ref_urn(
                    qc_node.raw_value.get("QuestionReference")
                    or qc_node.raw_value.get("question_reference")
                )
                if q_ref:
                    q_c_urn = parse_ddi_urn(q_ref)[0]
                    q_obj = QuestionItem.objects.filter(urn=q_c_urn).first()
                    if q_obj:
                        _, iq_created = InstrumentQuestion.objects.get_or_create(
                            instrument=primary_instrument,
                            question_item=q_obj,
                            defaults={
                                "path": f"/{primary_instrument.name}/{qc_order}",
                                "order": qc_order,
                            },
                        )
                        if iq_created:
                            _inc("InstrumentQuestion")

        # 11. Execute Approved Harmonization / Lineage Actions in Dependency Order
        harmonization_order = {rt: idx for idx, rt in enumerate(HARMONIZABLE_RESOURCE_TYPES)}
        harm_actions = sorted(
            [
                a
                for a in plan.actions
                if a.approved and a.action in ("link_existing", "generate_harmonized")
            ],
            key=lambda a: (harmonization_order.get(a.resource_type, 99), a.id),
        )

        for act in harm_actions:
            src_urn = act.details.get("canonical_urn") or act.source_urn
            if act.action == "link_existing" and act.target_urn:
                if not UrnRegistry.objects.filter(urn=src_urn).exists():
                    continue
                if not UrnRegistry.objects.filter(urn=act.target_urn).exists():
                    continue
                if SemanticRelationship.objects.filter(
                    subject_urn=act.target_urn,
                    predicate="prov:wasDerivedFrom",
                    object_urn=src_urn,
                ).exists():
                    continue
                link_res = link_to_harmonized_resource(
                    source_urns=[src_urn],
                    target_urn=act.target_urn,
                    resource_type=act.resource_type,
                    provenance_note=f"fairwddi.ingest:{plan.job_id}",
                    canonical_text=act.details.get("canonical_text"),
                    preserved_variants=act.details.get("preserved_variants"),
                    discarded_variants=act.details.get("discarded_variants"),
                    variant_type=act.details.get("variant_type"),
                    match_type=str(act.match_type) if act.match_type else None,
                    confidence=act.confidence,
                    job_id=f"{plan.job_id}:{act.id}",
                )
                if act.target_urn not in linked_urns:
                    linked_urns.append(act.target_urn)
                created_rel_ids.extend(link_res["created_rel_ids"])
                harmonize_sub_job_ids.append(link_res["job_id"])

            elif act.action == "generate_harmonized" and act.target_urn:
                gen_urn = act.details.get("generated_urn")
                if not UrnRegistry.objects.filter(urn=src_urn).exists():
                    continue
                if not UrnRegistry.objects.filter(urn=act.target_urn).exists():
                    continue

                if gen_urn and UrnRegistry.objects.filter(urn=gen_urn).exists():
                    link_res = link_to_harmonized_resource(
                        source_urns=[src_urn],
                        target_urn=gen_urn,
                        resource_type=act.resource_type,
                        provenance_note=f"fairwddi.ingest:{plan.job_id}",
                        canonical_text=act.details.get("canonical_text"),
                        preserved_variants=act.details.get("preserved_variants"),
                        discarded_variants=act.details.get("discarded_variants"),
                        variant_type=act.details.get("variant_type"),
                        match_type=str(act.match_type) if act.match_type else None,
                        confidence=act.confidence,
                        job_id=f"{plan.job_id}:{act.id}",
                    )
                    if gen_urn not in linked_urns:
                        linked_urns.append(gen_urn)
                    created_rel_ids.extend(link_res["created_rel_ids"])
                    harmonize_sub_job_ids.append(link_res["job_id"])
                else:
                    gen_res = create_harmonized_resource(
                        source_urns=[act.target_urn, src_urn],
                        target_urn=gen_urn,
                        resource_type=act.resource_type,
                        origin="generated",
                        provenance_note=f"fairwddi.ingest:{plan.job_id}",
                        canonical_text=act.details.get("canonical_text"),
                        preserved_variants=act.details.get("preserved_variants"),
                        discarded_variants=act.details.get("discarded_variants"),
                        variant_type=act.details.get("variant_type"),
                        match_type=str(act.match_type) if act.match_type else None,
                        confidence=act.confidence,
                        job_id=f"{plan.job_id}:{act.id}",
                    )
                    created_gen = gen_res["target_urn"]
                    if created_gen not in generated_urns:
                        generated_urns.append(created_gen)
                    for cu in gen_res.get("created_code_urns", []):
                        if cu not in generated_urns:
                            generated_urns.append(cu)
                    created_rel_ids.extend(gen_res["created_rel_ids"])
                    harmonize_sub_job_ids.append(gen_res["job_id"])
                    _inc(f"Generated{act.resource_type}")

        # 12. Record lightweight IngestBatch receipt
        batch_status = "quarantined" if quarantine_ids else "completed"
        batch = IngestBatch.objects.create(
            source_format=fmt.canonical_slug,
            file_name=src_path.name,
            file_sha256=current_sha,
            file_path=str(src_path),
            status=batch_status,
            options={
                "job_id": plan.job_id,
                "profile": resolved_profile.name,
                "quarantine_ids": quarantine_ids,
                "harmonize_sub_job_ids": harmonize_sub_job_ids,
                "created_rel_ids": created_rel_ids,
            },
            created_urns=created_urns,
            generated_urns=generated_urns,
            linked_urns=linked_urns,
            reused_urns=reused_urns,
            created_aliases=[],
            stats=entity_counts,
        )

    return {
        "job_id": plan.job_id,
        "batch_id": batch.id,
        "status": batch.status,
        "created_count": len(created_urns),
        "generated_count": len(generated_urns),
        "linked_count": len(linked_urns),
        "reused_count": len(reused_urns),
        "alias_count": 0,
        "quarantine_count": len(quarantine_ids),
        "frequency_rows_count": len(freq_rows_to_insert),
        "stats": entity_counts,
    }


def undo_ingestion(batch_id: int) -> dict[str, Any]:
    """Roll back an IngestBatch in a single atomic transaction respecting referential integrity.

    - Reverts target enrichments and removes ``prov:wasDerivedFrom`` links created by this batch.
    - Removes ``generated`` resources minted by this batch ONLY if no subsequent batch/resource
      still links to or references them.
    - Verifies that no external resource outside the batch references any ``imported`` resource
      in ``created_urns`` before deleting them in leaf-to-root order.
    """
    from fairwddi.ingest.harmonizer import undo_harmonization
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
        IngestBatch,
        InstanceVariable,
        Instrument,
        InstrumentQuestion,
        MetadataQuarantine,
        QuestionItem,
        QuestionScheme,
        QuestionVariable,
        RepresentedVariable,
        RepresentedVariableScheme,
        SemanticRelationship,
        StudyInstrument,
        StudyUnit,
        UrnRegistry,
        VariableGroup,
        VariableScheme,
    )

    batch = IngestBatch.objects.filter(id=batch_id).first()
    if not batch:
        raise ValueError(f"IngestBatch #{batch_id} does not exist.")

    created_urns = list(batch.created_urns or [])
    generated_urns = list(batch.generated_urns or [])
    opts = batch.options or {}
    quarantine_ids = list(opts.get("quarantine_ids", []))
    sub_job_ids = list(opts.get("harmonize_sub_job_ids", []))
    created_urns_set = set(created_urns)
    generated_urns_set = set(generated_urns)

    pre_gen_count = (
        UrnRegistry.objects.filter(urn__in=generated_urns_set).count() if generated_urns_set else 0
    )

    with transaction.atomic():
        # 1. Unwind harmonization sub-jobs in reverse order
        for sub_id in reversed(sub_job_ids):
            try:
                undo_harmonization(sub_id)
            except ValueError as err:
                # If a generated resource created by this batch is now referenced externally
                # (e.g. a later batch linked to it), keep the generated resource alive and
                # delete only this batch's provenance link to it.
                if "referenced by" in str(err):
                    SemanticRelationship.objects.filter(
                        predicate="prov:wasDerivedFrom",
                        object_urn__in=created_urns_set,
                        subject_urn__in=generated_urns_set,
                    ).delete()
                else:
                    pass

        # Clean up any leftover generated_urns created by this batch that are no longer referenced
        if generated_urns_set:
            remaining_gen = set(
                UrnRegistry.objects.filter(urn__in=generated_urns_set).values_list("urn", flat=True)
            )
            for gen_u in list(remaining_gen):
                other_links = SemanticRelationship.objects.filter(
                    subject_urn=gen_u, predicate="prov:wasDerivedFrom"
                ).exclude(object_urn__in=created_urns_set)
                ext_refs = get_resource_references(
                    gen_u, ignore_urns=created_urns_set | remaining_gen
                )
                if other_links.count() > 1 or ext_refs:
                    remaining_gen.discard(gen_u)

            if remaining_gen:
                with integrity_deletion_context(ignore_urns=created_urns_set | remaining_gen):
                    SemanticRelationship.objects.filter(subject_urn__in=remaining_gen).delete()
                    Code.objects.filter(urn__in=remaining_gen).delete()
                    for m_cls in (
                        RepresentedVariable,
                        QuestionItem,
                        CodeList,
                        Category,
                        ConceptualVariable,
                    ):
                        m_cls.objects.filter(urn__in=remaining_gen).delete()
                    UrnRegistry.objects.filter(urn__in=remaining_gen).delete()

        deleted_generated_count = (
            pre_gen_count - UrnRegistry.objects.filter(urn__in=generated_urns_set).count()
            if generated_urns_set
            else 0
        )

        if quarantine_ids:
            MetadataQuarantine.objects.filter(id__in=quarantine_ids).delete()

        # 2. Verify zero external references exist to any imported resource in created_urns
        if created_urns_set:
            for c_u in created_urns:
                assert_can_delete(c_u, ignore_urns=created_urns_set)

            with integrity_deletion_context(ignore_urns=created_urns_set):
                # Remove junction & frequency rows owned by this batch's resources
                DatafileVariableFrequency.objects.filter(
                    instance_variable_id__in=created_urns_set
                ).delete()
                DatafileVariableFrequency.objects.filter(datafile_id__in=created_urns_set).delete()
                DatafileVariable.objects.filter(instance_variable_id__in=created_urns_set).delete()
                DatafileVariable.objects.filter(datafile_id__in=created_urns_set).delete()
                StudyInstrument.objects.filter(study_unit_id__in=created_urns_set).delete()
                StudyInstrument.objects.filter(instrument_id__in=created_urns_set).delete()
                InstrumentQuestion.objects.filter(instrument_id__in=created_urns_set).delete()
                InstrumentQuestion.objects.filter(question_item_id__in=created_urns_set).delete()
                QuestionVariable.objects.filter(question_item_id__in=created_urns_set).delete()
                QuestionVariable.objects.filter(
                    represented_variable_id__in=created_urns_set
                ).delete()
                SemanticRelationship.objects.filter(subject_urn__in=created_urns_set).delete()

                # Clear self-referential parent links within the batch
                Code.objects.filter(urn__in=created_urns_set).update(parent=None)
                Category.objects.filter(urn__in=created_urns_set).update(parent=None)
                Concept.objects.filter(urn__in=created_urns_set).update(parent=None)

                # Delete core resources in strict leaf-to-root order
                for m_cls in (
                    InstanceVariable,
                    Datafile,
                    StudyUnit,
                    Code,
                    RepresentedVariable,
                    QuestionItem,
                    CodeList,
                    Category,
                    ConceptualVariable,
                    Concept,
                    Instrument,
                    VariableGroup,
                    CategoryScheme,
                    QuestionScheme,
                    ConceptScheme,
                    ConceptualVariableScheme,
                    RepresentedVariableScheme,
                    VariableScheme,
                ):
                    m_cls.objects.filter(urn__in=created_urns_set).delete()

                qs = UrnRegistry.objects.filter(urn__in=created_urns_set)
                deleted_urns_count = qs.count()
                qs.delete()
        else:
            deleted_urns_count = 0

        batch.status = "undone"
        batch.save(update_fields=["status", "updated_at"])

    return {
        "batch_id": batch.id,
        "status": batch.status,
        "deleted_core_resources_count": deleted_urns_count,
        "deleted_generated_resources_count": deleted_generated_count,
        "deleted_aliases_count": 0,
    }


def list_ingest_batches(status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    """Return a summary list of IngestBatch receipts ordered newest first."""
    from fairwddi.models import IngestBatch

    qs = IngestBatch.objects.order_by("-id")
    if status:
        qs = qs.filter(status=status)

    results: list[dict[str, Any]] = []
    for b in qs[:limit]:
        results.append(
            {
                "id": b.id,
                "file_name": b.file_name,
                "source_format": b.source_format,
                "status": b.status,
                "created_count": len(b.created_urns or []),
                "generated_count": len(b.generated_urns or []),
                "linked_count": len(b.linked_urns or []),
                "reused_count": len(b.reused_urns or []),
                "alias_count": len(b.created_aliases or []),
                "stats": b.stats or {},
                "created_at": b.created_at.isoformat() if b.created_at else None,
            }
        )
    return results


def get_ingest_batch_status(batch_id: int) -> dict[str, Any]:
    """Return full status and statistics for a single IngestBatch receipt."""
    from fairwddi.models import IngestBatch

    b = IngestBatch.objects.filter(id=batch_id).first()
    if not b:
        raise ValueError(f"IngestBatch #{batch_id} does not exist.")

    return {
        "id": b.id,
        "file_name": b.file_name,
        "file_path": b.file_path,
        "file_sha256": b.file_sha256,
        "source_format": b.source_format,
        "status": b.status,
        "options": b.options or {},
        "created_count": len(b.created_urns or []),
        "generated_count": len(b.generated_urns or []),
        "linked_count": len(b.linked_urns or []),
        "reused_count": len(b.reused_urns or []),
        "alias_count": len(b.created_aliases or []),
        "stats": b.stats or {},
        "created_at": b.created_at.isoformat() if b.created_at else None,
        "updated_at": b.updated_at.isoformat() if b.updated_at else None,
    }


# Convenience alias for executing an IngestPlan
execute_ingestion = apply_ingestion
