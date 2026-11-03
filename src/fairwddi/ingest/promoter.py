"""Stage 2b (Promotion & Undo): Promote staged DDI resources into ReQuest core tables.

Handles:
- Deterministic URN parsing and normalization
- Multi-algorithm content hash computation
- Duplicate and content-drift detection against UrnRegistry & URNAlias
- ReQuest model shortcut resolution:
  * Variable -> RepresentedVariable + InstanceVariable
  * QuestionItem <-> RepresentedVariable (via QuestionVariable)
  * Instrument -> Sequence -> QuestionConstruct -> QuestionItem (InstrumentQuestion/StudyInstrument)
  * PhysicalInstance / Variable stats -> Datafile + DatafileVariable + DatafileVariableFrequency
- Transactional batch rollback (`undo_promotion`) via EventLog provenance
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from pathlib import Path
from typing import Any

from django.db import transaction

from fairwddi.ingest.plan import IngestPlan, PlanActionItem, PlanIssue, ReviewGate
from fairwddi.ingest.staging import cleanup_staged_import
from fairwddi.utils.normalize_string import normalize_string


def parse_ddi_urn(urn: str, default_agency: str = "fr.cdsp") -> tuple[str, str, str, str]:
    """Parse a DDI URN into (canonical_urn, agency, identifier, version)."""
    cleaned = (urn or "").strip()
    if cleaned.startswith("urn:ddi:"):
        parts = cleaned.split(":")
        if len(parts) == 5:
            _, _, agency, identifier, version = parts
            return cleaned, agency or default_agency, identifier, version or "1.0.0"
        if len(parts) > 5:
            agency = parts[2] or default_agency
            version = parts[-1] or "1.0.0"
            identifier = ":".join(parts[3:-1])
            return f"urn:ddi:{agency}:{identifier}:{version}", agency, identifier, version
        if len(parts) == 4:
            agency = parts[2] or default_agency
            identifier = parts[3]
            version = "1.0.0"
            return f"urn:ddi:{agency}:{identifier}:{version}", agency, identifier, version

    # Fallback synthesis for non-standard URN strings
    safe_id = re.sub(r"[^A-Za-z0-9_.\-]", "_", cleaned) or f"item_{uuid.uuid4().hex[:8]}"
    canonical = f"urn:ddi:{default_agency}:{safe_id}:1.0.0"
    return canonical, default_agency, safe_id, "1.0.0"


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
                or current_lang
            )
            lang = str(lang).split("-")[0].lower() if lang else default_lang

            # Direct value keys
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

            # Nested text structures (e.g. DDI 4 DynamicText / LiteralText or DDI 3.3 String)
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
        return normalize_string(val)
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


def _normalize_staged_node(
    resource_type: str,
    raw_urn: str,
    raw_value: dict[str, Any],
) -> dict[str, Any]:
    """Extract normalized fields for a staged resource node regardless of DDI 4/3.3/2.5 origin."""
    canonical_urn, agency, identifier, version = parse_ddi_urn(raw_urn)
    uaps = _extract_user_attributes(raw_value)

    # Extract name & label (supporting snake_case DDI 4 dicts and PascalCase XML dicts)
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

    # Category from DDI-C raw wrapper
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

    # QuestionItem specifics
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

    # CodeList codes
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
        # DDI-C raw wrapper fallback
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

    # Variable specifics
    codelist_urn = None
    question_urns: list[str] = []
    concept_urn = None
    value_rep: dict[str, Any] | None = None
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
        if not codelist_urn and "catgry" in raw_value:
            # DDI-C raw variable
            pass
        if codelist_urn:
            codelist_urn = parse_ddi_urn(codelist_urn)[0]

        q_refs = _extract_ref_urn_list(
            raw_value.get("QuestionReference") or raw_value.get("question_reference")
        )
        question_urns = [parse_ddi_urn(u)[0] for u in q_refs]
        if not question_urns and "qstn" in raw_value:
            qstn_data = raw_value["qstn"]
            question_text_ml = _extract_multilingual(qstn_data)

        c_ref = _extract_ref_urn(
            raw_value.get("ConceptReference") or raw_value.get("ConceptualVariableReference")
        )
        if c_ref:
            concept_urn = parse_ddi_urn(c_ref)[0]

    # StudyUnit specifics
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
        "value_representation": value_rep,
        "citation": citation_ml,
        "abstract": abstract_ml,
        "user_attributes": uaps,
        "hashes": hashes,
    }


# Resource types that map directly to ReQuest database tables
PROMOTABLE_RESOURCE_TYPES = {
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


def _find_existing_by_content_hash(
    resource_type: str,
    content_hash: str,
) -> str | None:
    """Check if an entity of `resource_type` already exists in the DB with the same content hash."""
    from fairwddi.models import (
        Category,
        CodeList,
        Concept,
        ConceptualVariable,
        QuestionItem,
        RepresentedVariable,
    )

    model_map = {
        "Category": Category,
        "CodeList": CodeList,
        "QuestionItem": QuestionItem,
        "Concept": Concept,
        "ConceptualVariable": ConceptualVariable,
        "RepresentedVariable": RepresentedVariable,
    }
    model_cls = model_map.get(resource_type)
    if model_cls is None:
        return None

    for obj in model_cls.objects.exclude(hashes__isnull=True).only("urn", "hashes"):
        if isinstance(obj.hashes, dict) and obj.hashes.get("content") == content_hash:
            return obj.urn
    return None


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


def plan_promotion(
    import_id: int,
    output_dir: str | Path | None = None,
    auto_approve: bool = False,
) -> IngestPlan:
    """Build a review-gated Promotion Plan (`IngestPlan(stage='promote')`) for a staged batch."""
    from fairwddi.models import StagedImport, StagedResourceNode, UrnRegistry

    staged_import = StagedImport.objects.filter(id=import_id).first()
    if not staged_import:
        raise ValueError(f"StagedImport #{import_id} does not exist.")

    nodes = list(StagedResourceNode.objects.filter(staged_import=staged_import).order_by("id"))
    existing_urns = set(UrnRegistry.objects.values_list("urn", flat=True))

    actions: list[PlanActionItem] = []
    issues: list[PlanIssue] = []
    action_counts: dict[str, int] = {
        "create": 0,
        "reuse": 0,
        "alias": 0,
        "quarantine": 0,
        "skip": 0,
    }

    for idx, node in enumerate(nodes, start=1):
        r_type = node.resource_type
        if r_type not in PROMOTABLE_RESOURCE_TYPES:
            action_counts["skip"] += 1
            continue

        norm = _normalize_staged_node(r_type, node.raw_urn, node.raw_value)
        c_urn = norm["canonical_urn"]
        c_hash = norm["hashes"]["content"]

        if c_urn in existing_urns:
            existing_hash = _get_existing_content_hash(c_urn)
            if existing_hash is None or existing_hash == c_hash:
                act_type = "reuse"
                target_urn = c_urn
                req_review = False
                notes = "Identical URN and content already in UrnRegistry."
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
                        code="PROM-DRIFT-001",
                        resource_type=r_type,
                        resource_urn=c_urn,
                        message=notes,
                        requires_review=True,
                    )
                )
        else:
            matched_urn = _find_existing_by_content_hash(r_type, c_hash)
            if matched_urn and matched_urn != c_urn:
                act_type = "alias"
                target_urn = matched_urn
                req_review = False
                notes = (
                    f"Exact content hash match with existing {r_type} "
                    f"'{matched_urn}'; will register URNAlias."
                )
            else:
                act_type = "create"
                target_urn = c_urn
                req_review = False
                notes = (
                    "Split into RepresentedVariable + InstanceVariable"
                    if r_type == "Variable"
                    else f"Create {r_type} in ReQuest core schema."
                )

        action_counts[act_type] += 1
        actions.append(
            PlanActionItem(
                id=f"prom-{idx:04d}",
                stage="promote",
                action=act_type,  # type: ignore[arg-type]
                resource_type=r_type,
                source_urn=node.raw_urn,
                target_urn=target_urn,
                confidence=1.0,
                requires_review=req_review,
                details={
                    "node_id": node.id,
                    "canonical_urn": c_urn,
                    "content_hash": c_hash,
                    "name": norm["name"],
                },
                notes=notes,
            )
        )

    job_id = f"promote-batch-{import_id}-{uuid.uuid4().hex[:6]}"
    plan = IngestPlan(
        stage="promote",
        job_id=job_id,
        source_file=staged_import.file_name,
        source_format=staged_import.source_format,
        file_sha256=staged_import.import_options.get("file_sha256"),
        staged_import_id=import_id,
        summary={
            "total_staged_nodes": len(nodes),
            "promotable_actions": len(actions),
            **action_counts,
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
        stem = Path(staged_import.file_name).stem
        plan.to_yaml(out_dir / f"{stem}.batch{import_id}.promote.plan.yaml")
        plan.to_markdown(out_dir / f"{stem}.batch{import_id}.promote.report.md")

    return plan


def apply_promotion(
    import_id_or_plan: int | str | Path | IngestPlan,
    auto_approve: bool = False,
    compact: bool = False,
) -> dict[str, Any]:
    """Execute Stage 2b promotion of a staged batch into the ReQuest core database tables.

    Enforces the review gate if any drift/quarantine items require review.
    Records full batch provenance in EventLog to support `undo_promotion(import_id)`.
    """
    from django.utils import timezone

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
        EventLog,
        InstanceVariable,
        Instrument,
        InstrumentQuestion,
        MetadataQuarantine,
        QuestionItem,
        QuestionScheme,
        QuestionVariable,
        RepresentedVariable,
        RepresentedVariableScheme,
        StagedImport,
        StagedResourceNode,
        StudyInstrument,
        StudyUnit,
        URNAlias,
        UrnRegistry,
        VariableGroup,
        VariableScheme,
    )

    if isinstance(import_id_or_plan, IngestPlan):
        plan = import_id_or_plan
    elif isinstance(import_id_or_plan, int) or (
        isinstance(import_id_or_plan, str) and import_id_or_plan.isdigit()
    ):
        plan = plan_promotion(int(import_id_or_plan), auto_approve=auto_approve)
    else:
        plan = IngestPlan.from_yaml(import_id_or_plan)

    if not plan.is_ready_to_execute(auto_approve=auto_approve):
        raise PermissionError(
            f"Promotion plan '{plan.job_id}' has {plan.pending_review_count} pending review "
            f"item(s) and {plan.error_count} error(s). Approve the plan YAML "
            f"(review_gate.approved: true) or pass --auto-approve."
        )

    import_id = plan.staged_import_id
    if import_id is None:
        raise ValueError("Promotion plan is missing staged_import_id.")

    staged_import = StagedImport.objects.filter(id=import_id).first()
    if not staged_import:
        raise ValueError(f"StagedImport #{import_id} does not exist.")

    nodes = list(StagedResourceNode.objects.filter(staged_import=staged_import).order_by("id"))
    nodes_by_type: dict[str, list[StagedResourceNode]] = {}
    for n in nodes:
        nodes_by_type.setdefault(n.resource_type, []).append(n)

    action_by_node_id: dict[int, PlanActionItem] = {}
    for act in plan.actions:
        nid = act.details.get("node_id")
        if isinstance(nid, int):
            action_by_node_id[nid] = act

    created_urns: list[str] = []
    reused_urns: list[str] = []
    created_aliases: list[str] = []
    quarantine_ids: list[int] = []
    urn_remap: dict[str, str] = {}

    def _register_or_check(
        node: StagedResourceNode,
        norm: dict[str, Any],
    ) -> tuple[str, str]:
        """Return (action_taken, resolved_canonical_urn) for a node."""
        c_urn = norm["canonical_urn"]
        act = action_by_node_id.get(node.id)
        act_type = act.action if act else "create"

        if act_type == "quarantine":
            existing_hash = _get_existing_content_hash(c_urn) or "unknown"
            mq = MetadataQuarantine.objects.create(
                incoming_urn=c_urn,
                existing_urn=c_urn,
                entity_type=node.resource_type,
                existing_content_hash=existing_hash[:64],
                incoming_content_hash=norm["hashes"]["content"][:64],
                incoming_content=node.raw_value,
                conflict_type="hash_mismatch",
                source_file=staged_import.file_name,
            )
            quarantine_ids.append(mq.id)
            node.status = "quarantined"
            node.canonical_urn = c_urn
            node.save(update_fields=["status", "canonical_urn"])
            return "quarantine", c_urn

        if act_type == "alias" and act and act.target_urn:
            target = act.target_urn
            urn_remap[c_urn] = target
            urn_remap[node.raw_urn] = target
            if not URNAlias.objects.filter(alias_urn=node.raw_urn).exists():
                URNAlias.objects.create(
                    alias_urn=node.raw_urn,
                    canonical_urn=target,
                    entity_type=node.resource_type,
                    source_file=staged_import.file_name,
                )
                created_aliases.append(node.raw_urn)
            node.status = "normalized"
            node.canonical_urn = target
            node.save(update_fields=["status", "canonical_urn"])
            return "alias", target

        if UrnRegistry.objects.filter(urn=c_urn).exists():
            reused_urns.append(c_urn)
            node.status = "normalized"
            node.canonical_urn = c_urn
            node.save(update_fields=["status", "canonical_urn"])
            return "reuse", c_urn

        return "create", c_urn

    with transaction.atomic():
        # 1. StudyUnit (ensure at least one StudyUnit exists for dataset-level entities)
        primary_study: StudyUnit | None = None
        for node in nodes_by_type.get("StudyUnit", []):
            norm = _normalize_staged_node("StudyUnit", node.raw_urn, node.raw_value)
            status, c_urn = _register_or_check(node, norm)
            if status == "create":
                primary_study = StudyUnit.objects.create(
                    urn=c_urn,
                    name=norm["name"],
                    title=norm["label"] or norm["citation"],
                    description=norm["description"] or norm["abstract"],
                    hashes=norm["hashes"],
                )
                created_urns.append(c_urn)
                node.status = "normalized"
                node.canonical_urn = c_urn
                node.save(update_fields=["status", "canonical_urn"])
            else:
                primary_study = StudyUnit.objects.filter(urn=c_urn).first() or primary_study

            # Also check for embedded PhysicalInstanceReference on StudyUnit
            pi_refs = node.raw_value.get("PhysicalInstanceReference") or []
            if isinstance(pi_refs, dict):
                pi_refs = [pi_refs]
            for pi_dict in pi_refs:
                if isinstance(pi_dict, dict) and ("URN" in pi_dict or "ID" in pi_dict):
                    pi_urn_raw = (
                        pi_dict.get("URN")
                        or f"urn:ddi:{norm['agency']}:{pi_dict.get('ID')}:{norm['version']}"
                    )
                    pi_norm = _normalize_staged_node("PhysicalInstance", str(pi_urn_raw), pi_dict)
                    pi_c_urn = pi_norm["canonical_urn"]
                    if primary_study and not Datafile.objects.filter(urn=pi_c_urn).exists():
                        pi_uaps = pi_norm["user_attributes"]
                        f_name = pi_uaps.get("ddi:file_name") or pi_norm["name"]
                        ext_attrs: list[dict[str, Any]] = [{"type": "file_name", "value": f_name}]
                        if pi_uaps.get("ddi:file_id"):
                            ext_attrs.append({"type": "file_id", "value": pi_uaps["ddi:file_id"]})
                        if pi_uaps.get("ddi:case_count", "").isdigit():
                            ext_attrs.append(
                                {"type": "case_count", "value": int(pi_uaps["ddi:case_count"])}
                            )
                        if pi_uaps.get("ddi:var_count", "").isdigit():
                            ext_attrs.append(
                                {"type": "variable_count", "value": int(pi_uaps["ddi:var_count"])}
                            )
                        Datafile.objects.create(
                            urn=pi_c_urn,
                            name=f_name,
                            description=pi_norm["label"],
                            study_unit=primary_study,
                            extended_attributes=ext_attrs,
                            hashes=pi_norm["hashes"],
                        )
                        created_urns.append(pi_c_urn)

        if primary_study is None and (
            nodes_by_type.get("Variable") or nodes_by_type.get("InstanceVariable")
        ):
            # Synthesize a fallback StudyUnit for fragment files lacking an explicit StudyUnit
            fallback_urn = f"urn:ddi:fr.cdsp:study_batch_{import_id}:1.0.0"
            primary_study = StudyUnit.objects.filter(urn=fallback_urn).first()
            if not primary_study:
                primary_study = StudyUnit.objects.create(
                    urn=fallback_urn,
                    name=Path(staged_import.file_name).stem,
                    title={"en": Path(staged_import.file_name).stem},
                )
                created_urns.append(fallback_urn)

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
                norm = _normalize_staged_node(s_type, node.raw_urn, node.raw_value)
                status, c_urn = _register_or_check(node, norm)
                if status == "create":
                    s_cls.objects.create(
                        urn=c_urn,
                        name=norm["name_ml"],
                        description=norm["description"],
                    )
                    created_urns.append(c_urn)
                    node.status = "normalized"
                    node.canonical_urn = c_urn
                    node.save(update_fields=["status", "canonical_urn"])

        # 3. Concept & ConceptualVariable
        for node in nodes_by_type.get("Concept", []):
            norm = _normalize_staged_node("Concept", node.raw_urn, node.raw_value)
            status, c_urn = _register_or_check(node, norm)
            if status == "create":
                Concept.objects.create(
                    urn=c_urn,
                    label=norm["label"] or {"en": norm["name"]},
                    description=norm["description"],
                    hashes=norm["hashes"],
                )
                created_urns.append(c_urn)
                node.status = "normalized"
                node.canonical_urn = c_urn
                node.save(update_fields=["status", "canonical_urn"])

        for node in nodes_by_type.get("ConceptualVariable", []):
            norm = _normalize_staged_node("ConceptualVariable", node.raw_urn, node.raw_value)
            status, c_urn = _register_or_check(node, norm)
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
                )
                created_urns.append(c_urn)
                node.status = "normalized"
                node.canonical_urn = c_urn
                node.save(update_fields=["status", "canonical_urn"])

        # 4. Categories
        for node in nodes_by_type.get("Category", []):
            norm = _normalize_staged_node("Category", node.raw_urn, node.raw_value)
            status, c_urn = _register_or_check(node, norm)
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
                )
                created_urns.append(c_urn)
                node.status = "normalized"
                node.canonical_urn = c_urn
                node.save(update_fields=["status", "canonical_urn"])

        # 5. CodeLists & CodeItems
        for node in nodes_by_type.get("CodeList", []):
            norm = _normalize_staged_node("CodeList", node.raw_urn, node.raw_value)
            status, c_urn = _register_or_check(node, norm)
            if status == "create":
                cl_obj = CodeList.objects.create(
                    urn=c_urn,
                    name=norm["name"],
                    description=norm["description"] or norm["label"],
                    hashes=norm["hashes"],
                )
                created_urns.append(c_urn)
                for c_entry in norm["codes"]:
                    cat_u = c_entry.get("category_urn")
                    if cat_u:
                        resolved_cat_u = urn_remap.get(cat_u, cat_u)
                        cat_obj = Category.objects.filter(urn=resolved_cat_u).first()
                        if cat_obj:
                            ci_obj, ci_created = CodeItem.objects.get_or_create(
                                code_list=cl_obj,
                                code_value=str(c_entry["value"])[:64],
                                defaults={
                                    "category": cat_obj,
                                    "order": c_entry.get("order", 1),
                                    "is_missing": bool(c_entry.get("is_missing", False)),
                                },
                            )
                            if ci_created:
                                created_urns.append(ci_obj.urn)
                node.status = "normalized"
                node.canonical_urn = c_urn
                node.save(update_fields=["status", "canonical_urn"])

        # 6. QuestionItems
        for node in nodes_by_type.get("QuestionItem", []):
            norm = _normalize_staged_node("QuestionItem", node.raw_urn, node.raw_value)
            status, c_urn = _register_or_check(node, norm)
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
                )
                created_urns.append(c_urn)
                node.status = "normalized"
                node.canonical_urn = c_urn
                node.save(update_fields=["status", "canonical_urn"])

        # 7. Explicit RepresentedVariables
        for node in nodes_by_type.get("RepresentedVariable", []):
            norm = _normalize_staged_node("RepresentedVariable", node.raw_urn, node.raw_value)
            status, c_urn = _register_or_check(node, norm)
            if status == "create":
                cl_u = (
                    urn_remap.get(norm["codelist_urn"], norm["codelist_urn"])
                    if norm["codelist_urn"]
                    else None
                )
                cl_obj = CodeList.objects.filter(urn=cl_u).first() if cl_u else None
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
                )
                created_urns.append(c_urn)
                for idx, q_u in enumerate(norm["question_urns"], start=1):
                    resolved_q_u = urn_remap.get(q_u, q_u)
                    q_obj = QuestionItem.objects.filter(urn=resolved_q_u).first()
                    if q_obj:
                        QuestionVariable.objects.get_or_create(
                            question_item=q_obj,
                            represented_variable=rv_obj,
                            defaults={"order": idx},
                        )
                node.status = "normalized"
                node.canonical_urn = c_urn
                node.save(update_fields=["status", "canonical_urn"])

        # 8. VariableGroups
        for node in nodes_by_type.get("VariableGroup", []):
            norm = _normalize_staged_node("VariableGroup", node.raw_urn, node.raw_value)
            status, c_urn = _register_or_check(node, norm)
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
                )
                created_urns.append(c_urn)
                node.status = "normalized"
                node.canonical_urn = c_urn
                node.save(update_fields=["status", "canonical_urn"])

        # 9. Variables & InstanceVariables (resolving the Variable Cascade + Datafile shortcuts)
        for var_type in ("Variable", "InstanceVariable"):
            for var_order, node in enumerate(nodes_by_type.get(var_type, []), start=1):
                norm = _normalize_staged_node(var_type, node.raw_urn, node.raw_value)
                status, c_urn = _register_or_check(node, norm)
                if status in ("quarantine", "alias"):
                    continue

                cl_u = (
                    urn_remap.get(norm["codelist_urn"], norm["codelist_urn"])
                    if norm["codelist_urn"]
                    else None
                )
                cl_obj = CodeList.objects.filter(urn=cl_u).first() if cl_u else None
                if cl_obj is None and "catgry" in node.raw_value:
                    # Fallback lookup for DDI-C raw codelist
                    for ref_u in node.raw_value.get("_referenced_urns", []):
                        cl_obj = CodeList.objects.filter(urn=urn_remap.get(ref_u, ref_u)).first()
                        if cl_obj:
                            break

                # Synthesize or reuse a RepresentedVariable in the Variable Cascade
                rv_payload = {
                    "label": norm["label"],
                    "codelist_urn": cl_obj.urn if cl_obj else None,
                    "question_urns": [urn_remap.get(u, u) for u in norm["question_urns"]],
                    "value_representation": norm["value_representation"],
                }
                rv_hashes = compute_resource_hashes("RepresentedVariable", rv_payload)
                existing_rv_urn = _find_existing_by_content_hash(
                    "RepresentedVariable", rv_hashes["content"]
                )
                if existing_rv_urn:
                    rv_obj = RepresentedVariable.objects.filter(urn=existing_rv_urn).first()
                else:
                    rv_id = f"rv_{norm['identifier']}_{rv_hashes['content'].split(':')[-1][:8]}"
                    rv_urn = f"urn:ddi:{norm['agency']}:{rv_id}:{norm['version']}"
                    rv_obj = RepresentedVariable.objects.filter(urn=rv_urn).first()
                    if not rv_obj:
                        rv_obj = RepresentedVariable.objects.create(
                            urn=rv_urn,
                            name=norm["name"],
                            label=norm["label"],
                            description=norm["description"],
                            code_list=cl_obj,
                            value_representation=norm["value_representation"],
                            hashes=rv_hashes,
                        )
                        created_urns.append(rv_urn)

                # If DDI-C variable had inline question text without a separate QuestionItem node
                if not norm["question_urns"] and norm["question_text"] and rv_obj:
                    q_hashes = compute_resource_hashes(
                        "QuestionItem",
                        {"name": f"q_{norm['name']}", "question_text": norm["question_text"]},
                    )
                    existing_q_urn = _find_existing_by_content_hash(
                        "QuestionItem", q_hashes["content"]
                    )
                    if existing_q_urn:
                        q_obj = QuestionItem.objects.filter(urn=existing_q_urn).first()
                    else:
                        q_id = f"qi_{norm['identifier']}_{q_hashes['content'].split(':')[-1][:8]}"
                        q_urn = f"urn:ddi:{norm['agency']}:{q_id}:{norm['version']}"
                        q_obj = QuestionItem.objects.filter(urn=q_urn).first()
                        if not q_obj:
                            q_obj = QuestionItem.objects.create(
                                urn=q_urn,
                                name=f"q_{norm['name']}"[:255],
                                question_text=norm["question_text"],
                                hashes=q_hashes,
                            )
                            created_urns.append(q_urn)
                    if q_obj:
                        QuestionVariable.objects.get_or_create(
                            question_item=q_obj,
                            represented_variable=rv_obj,
                            defaults={"order": 1},
                        )

                # Link explicit QuestionItems to RepresentedVariable via QuestionVariable shortcut
                if rv_obj:
                    for idx, q_u in enumerate(norm["question_urns"], start=1):
                        resolved_q_u = urn_remap.get(q_u, q_u)
                        q_obj = QuestionItem.objects.filter(urn=resolved_q_u).first()
                        if q_obj:
                            QuestionVariable.objects.get_or_create(
                                question_item=q_obj,
                                represented_variable=rv_obj,
                                defaults={"order": idx},
                            )

                # Create or reuse InstanceVariable
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
                    )
                    created_urns.append(c_urn)
                    node.status = "normalized"
                    node.canonical_urn = c_urn
                    node.save(update_fields=["status", "canonical_urn"])
                else:
                    iv_obj = InstanceVariable.objects.filter(urn=c_urn).first()

                # Populate DatafileVariable & DatafileVariableFrequency if statistics exist
                uaps = norm["user_attributes"]
                if (
                    iv_obj
                    and primary_study
                    and (
                        "ddi:summary_statistics" in uaps
                        or "ddi:category_statistics" in uaps
                        or "ddi:file_id" in uaps
                    )
                ):
                    file_id = uaps.get("ddi:file_id") or "F1"
                    df_obj = Datafile.objects.filter(study_unit=primary_study).first()
                    if not df_obj:
                        df_urn = (
                            f"urn:ddi:{norm['agency']}:"
                            f"df_{primary_study.identifier}_{file_id}:{norm['version']}"
                        )
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
                            )
                            created_urns.append(df_urn)

                    stats_payload = {}
                    if "ddi:summary_statistics" in uaps:
                        try:
                            stats_payload = json.loads(uaps["ddi:summary_statistics"])
                        except Exception:
                            stats_payload = {}

                    DatafileVariable.objects.get_or_create(
                        datafile=df_obj,
                        instance_variable=iv_obj,
                        defaults={
                            "order": var_order,
                            "statistics": stats_payload or {},
                        },
                    )

                    if "ddi:category_statistics" in uaps:
                        try:
                            cat_stats = json.loads(uaps["ddi:category_statistics"])
                            for cs in cat_stats:
                                if isinstance(cs, dict) and cs.get("type") in ("freq", None):
                                    DatafileVariableFrequency.objects.get_or_create(
                                        datafile=df_obj,
                                        instance_variable=iv_obj,
                                        code_value=str(cs.get("code_value", ""))[:100],
                                        weight=cs.get("weight_var"),
                                        defaults={
                                            "frequency": float(cs.get("value", 0.0)),
                                        },
                                    )
                        except Exception:
                            pass

        # 10. Instruments, StudyInstrument & InstrumentQuestion shortcut tables
        primary_instrument: Instrument | None = None
        for node in nodes_by_type.get("Instrument", []):
            norm = _normalize_staged_node("Instrument", node.raw_urn, node.raw_value)
            status, c_urn = _register_or_check(node, norm)
            if status == "create":
                primary_instrument = Instrument.objects.create(
                    urn=c_urn,
                    name=norm["name"],
                    label=norm["label"],
                    description=norm["description"],
                    hashes=norm["hashes"],
                )
                created_urns.append(c_urn)
                node.status = "normalized"
                node.canonical_urn = c_urn
                node.save(update_fields=["status", "canonical_urn"])
            else:
                primary_instrument = (
                    Instrument.objects.filter(urn=c_urn).first() or primary_instrument
                )

            if primary_study and primary_instrument:
                StudyInstrument.objects.get_or_create(
                    study_unit=primary_study,
                    instrument=primary_instrument,
                )

        # Flatten QuestionConstruct nodes into InstrumentQuestion shortcut rows
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
                )
                created_urns.append(inst_urn)
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
                    q_c_urn = urn_remap.get(q_c_urn, q_c_urn)
                    q_obj = QuestionItem.objects.filter(urn=q_c_urn).first()
                    if q_obj:
                        InstrumentQuestion.objects.get_or_create(
                            instrument=primary_instrument,
                            question_item=q_obj,
                            defaults={
                                "path": f"/{primary_instrument.name}/{qc_order}",
                                "order": qc_order,
                            },
                        )
                qc_node.status = "normalized"
                qc_node.canonical_urn = parse_ddi_urn(qc_node.raw_urn)[0]
                qc_node.save(update_fields=["status", "canonical_urn"])

        # Mark remaining structural/routing nodes (Sequence, etc.) as normalized
        for node in nodes:
            if node.status == "staged":
                node.status = "normalized"
                node.canonical_urn = parse_ddi_urn(node.raw_urn)[0]
                node.save(update_fields=["status", "canonical_urn"])

        # Update StagedImport batch status
        normalized_cnt = StagedResourceNode.objects.filter(
            staged_import=staged_import, status="normalized"
        ).count()
        staged_import.processed_resources = normalized_cnt
        staged_import.processed_at = timezone.now()
        staged_import.status = "quarantined" if quarantine_ids else "normalized"
        staged_import.save(update_fields=["processed_resources", "processed_at", "status"])

        # Record batch promotion in EventLog for Undo
        anchor_urn = created_urns[0] if created_urns else (reused_urns[0] if reused_urns else None)
        if anchor_urn and UrnRegistry.objects.filter(urn=anchor_urn).exists():
            EventLog.objects.create(
                urn=anchor_urn,
                event_type="promoted",
                event_data={
                    "job_type": "promote",
                    "job_id": plan.job_id,
                    "staged_import_id": import_id,
                    "created_urns": created_urns,
                    "reused_urns": reused_urns,
                    "created_aliases": created_aliases,
                    "quarantine_ids": quarantine_ids,
                },
            )

    compacted_res = None
    if compact:
        compacted_res = cleanup_staged_import(import_id=import_id, compact_only=True)

    return {
        "job_id": plan.job_id,
        "staged_import_id": import_id,
        "status": staged_import.status,
        "created_count": len(created_urns),
        "reused_count": len(reused_urns),
        "alias_count": len(created_aliases),
        "quarantine_count": len(quarantine_ids),
        "compacted_nodes_count": compacted_res["compacted_nodes_count"] if compacted_res else 0,
    }


def undo_promotion(import_id: int, force: bool = False) -> dict[str, Any]:
    """Roll back a promoted StagedImport batch using EventLog provenance.

    Deletes UrnRegistry records created exclusively by `import_id` (which cascades cleanly
    to all child DDI tables and shortcut tables), removes URNAlias and MetadataQuarantine
    records created by the batch, and resets StagedImport and StagedResourceNode statuses
    back to `'staged'`.
    """
    from fairwddi.models import (
        EventLog,
        MetadataQuarantine,
        StagedImport,
        StagedResourceNode,
        URNAlias,
        UrnRegistry,
    )

    staged_import = StagedImport.objects.filter(id=import_id).first()
    if not staged_import:
        raise ValueError(f"StagedImport #{import_id} does not exist.")

    # Find EventLog entries for this staged_import_id
    promo_logs = [
        ev
        for ev in EventLog.objects.filter(event_type="promoted").order_by("-id")
        if isinstance(ev.event_data, dict) and ev.event_data.get("staged_import_id") == import_id
    ]

    created_urns: list[str] = []
    created_aliases: list[str] = []
    quarantine_ids: list[int] = []
    for ev in promo_logs:
        created_urns.extend(ev.event_data.get("created_urns", []))
        created_aliases.extend(ev.event_data.get("created_aliases", []))
        quarantine_ids.extend(ev.event_data.get("quarantine_ids", []))

    with transaction.atomic():
        if created_aliases:
            URNAlias.objects.filter(alias_urn__in=created_aliases).delete()

        if quarantine_ids:
            MetadataQuarantine.objects.filter(id__in=quarantine_ids).delete()

        deleted_urns_count = 0
        if created_urns:
            created_urns_set = set(created_urns)
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
                InstanceVariable,
                Instrument,
                QuestionItem,
                QuestionScheme,
                RepresentedVariable,
                RepresentedVariableScheme,
                StudyUnit,
                VariableGroup,
                VariableScheme,
            )

            for m_cls in (
                Code,
                Datafile,
                InstanceVariable,
                RepresentedVariable,
                QuestionItem,
                CodeList,
                Category,
                ConceptualVariable,
                Concept,
                Instrument,
                VariableGroup,
                StudyUnit,
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

        # Delete the promo event log rows
        for ev in promo_logs:
            ev.delete()

        # Reset staged nodes back to 'staged'
        reset_nodes = StagedResourceNode.objects.filter(staged_import=staged_import).update(
            status="staged",
            canonical_urn=None,
        )
        staged_import.status = "staged"
        staged_import.processed_resources = 0
        staged_import.processed_at = None
        staged_import.save(update_fields=["status", "processed_resources", "processed_at"])

    return {
        "staged_import_id": import_id,
        "status": "staged",
        "deleted_core_resources_count": deleted_urns_count,
        "deleted_aliases_count": len(created_aliases),
        "reset_staged_nodes_count": reset_nodes,
    }
