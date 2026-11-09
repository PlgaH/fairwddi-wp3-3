"""Stage 3b (Harmonization & Undo): Review-gated harmonization planning, execution, and rollback.

Supports:
- Multilingual label/question text merging (`merge_multilingual`)
- Canonical URN aliasing & cascade pointer consolidation (`alias` / `harmonize`)
- Semantic relationship linking (`link_semantic` -> skos:exactMatch / skos:closeMatch)
- Full transactional rollback (`undo_harmonization`) via EventLog snapshots
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

from django.db import transaction

from fairwddi.ingest.comparator import discover_candidates
from fairwddi.ingest.loader import compute_resource_hashes
from fairwddi.ingest.plan import IngestPlan, PlanActionItem, ReviewGate
from fairwddi.utils.urn import generate_generic_urn, validate_ddi_urn

logger = logging.getLogger(__name__)


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
                details=cand["details"],
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


def apply_harmonization(
    plan_or_path: IngestPlan | Path | str,
    auto_approve: bool = False,
) -> dict[str, Any]:
    """Execute an approved Harmonization Plan and log undo snapshots in EventLog."""
    from fairwddi.models import (
        EventLog,
        InstanceVariable,
        QuestionVariable,
        SemanticRelationship,
        URNAlias,
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

    merged_count = 0
    aliased_count = 0
    linked_count = 0
    created_aliases: list[str] = []
    created_rel_ids: list[int] = []
    target_snapshots: list[dict[str, Any]] = []
    repointed_ivs: list[dict[str, str]] = []
    repointed_qvs: list[dict[str, Any]] = []

    with transaction.atomic():
        for act in plan.actions:
            if not act.approved or not act.target_urn:
                continue

            model_cls = _get_model_for_type(act.resource_type)
            if model_cls is None:
                continue

            src_obj = model_cls.objects.filter(urn=act.source_urn).first()
            tgt_obj = model_cls.objects.filter(urn=act.target_urn).first()
            if not src_obj or not tgt_obj:
                continue

            # 1. Merge multilingual JSONB fields onto target_urn
            if act.action in ("merge_multilingual", "alias", "harmonize"):
                snap: dict[str, Any] = {
                    "resource_type": act.resource_type,
                    "urn": tgt_obj.urn,
                    "label": dict(tgt_obj.label)
                    if isinstance(tgt_obj.label, dict)
                    else tgt_obj.label,
                    "description": (
                        dict(tgt_obj.description)
                        if isinstance(tgt_obj.description, dict)
                        else tgt_obj.description
                    ),
                    "hashes": dict(tgt_obj.hashes)
                    if isinstance(tgt_obj.hashes, dict)
                    else tgt_obj.hashes,
                }
                tgt_obj.label = _merge_jsonb_dicts(tgt_obj.label, src_obj.label)
                tgt_obj.description = _merge_jsonb_dicts(tgt_obj.description, src_obj.description)

                hash_payload: dict[str, Any] = {
                    "name": tgt_obj.name,
                    "label": tgt_obj.label,
                    "description": tgt_obj.description,
                }
                if act.resource_type == "QuestionItem":
                    snap["question_text"] = (
                        dict(tgt_obj.question_text)
                        if isinstance(tgt_obj.question_text, dict)
                        else tgt_obj.question_text
                    )
                    snap["interviewer_instructions"] = (
                        dict(tgt_obj.interviewer_instructions)
                        if isinstance(tgt_obj.interviewer_instructions, dict)
                        else tgt_obj.interviewer_instructions
                    )
                    tgt_obj.question_text = _merge_jsonb_dicts(
                        tgt_obj.question_text, src_obj.question_text
                    )
                    tgt_obj.interviewer_instructions = _merge_jsonb_dicts(
                        tgt_obj.interviewer_instructions, src_obj.interviewer_instructions
                    )
                    if tgt_obj.question_text:
                        hash_payload["question_text"] = tgt_obj.question_text

                tgt_obj.hashes = compute_resource_hashes(act.resource_type, hash_payload)
                tgt_obj.save()
                target_snapshots.append(snap)
                if act.action == "merge_multilingual":
                    merged_count += 1

            # 2. Alias / cascade pointer consolidation
            if act.action in ("alias", "harmonize"):
                if not URNAlias.objects.filter(alias_urn=src_obj.urn).exists():
                    URNAlias.objects.create(
                        alias_urn=src_obj.urn,
                        canonical_urn=tgt_obj.urn,
                        entity_type=act.resource_type,
                    )
                    created_aliases.append(src_obj.urn)
                aliased_count += 1

                if act.resource_type == "RepresentedVariable":
                    for iv in InstanceVariable.objects.filter(represented_variable=src_obj):
                        repointed_ivs.append({"iv_urn": iv.urn, "old_rv_urn": src_obj.urn})
                        iv.represented_variable = tgt_obj
                        iv.save(update_fields=["represented_variable"])

                elif act.resource_type == "QuestionItem":
                    for qv in QuestionVariable.objects.filter(question_item=src_obj):
                        if not QuestionVariable.objects.filter(
                            question_item=tgt_obj,
                            represented_variable=qv.represented_variable,
                        ).exists():
                            repointed_qvs.append({"qv_id": qv.id, "old_q_urn": src_obj.urn})
                            qv.question_item = tgt_obj
                            qv.save(update_fields=["question_item"])

            # 3. Record SemanticRelationship
            predicate = (
                "skos:exactMatch"
                if act.action in ("alias", "harmonize", "merge_multilingual")
                else "skos:closeMatch"
            )
            rel, created = SemanticRelationship.objects.get_or_create(
                subject_urn=src_obj.urn,
                predicate=predicate,
                object_urn=tgt_obj.urn,
                defaults={
                    "subject_type": act.resource_type,
                    "object_type": act.resource_type,
                    "extended_attributes": [
                        {"type": "provenance", "value": f"fairwddi.ingest.harmonize:{plan.job_id}"}
                    ],
                },
            )
            if created:
                created_rel_ids.append(rel.id)
                linked_count += 1

        # Record EventLog for undo
        anchor_urn = plan.actions[0].target_urn if plan.actions else None
        if anchor_urn and UrnRegistry.objects.filter(urn=anchor_urn).exists():
            EventLog.objects.create(
                urn=anchor_urn,
                event_type="harmonized",
                event_data={
                    "job_type": "harmonize",
                    "job_id": plan.job_id,
                    "created_aliases": created_aliases,
                    "created_rel_ids": created_rel_ids,
                    "target_snapshots": target_snapshots,
                    "repointed_ivs": repointed_ivs,
                    "repointed_qvs": repointed_qvs,
                },
            )

    logger.info(
        "Applied harmonization plan %s: %d merged, %d aliased, %d semantic links",
        plan.job_id,
        merged_count,
        aliased_count,
        linked_count,
    )

    return {
        "job_id": plan.job_id,
        "merged_multilingual_count": merged_count,
        "aliased_count": aliased_count,
        "semantic_links_created": linked_count,
        "repointed_instance_variables": len(repointed_ivs),
    }


def undo_harmonization(job_id: str) -> dict[str, Any]:
    """Revert an applied Harmonization Job or Elevation Job using its EventLog snapshot."""
    from fairwddi.models import (
        Code,
        EventLog,
        InstanceVariable,
        InstrumentQuestion,
        QuestionItem,
        QuestionVariable,
        RepresentedVariable,
        SemanticRelationship,
        URNAlias,
        UrnRegistry,
    )

    ev = next(
        (
            e
            for e in EventLog.objects.filter(
                event_type__in=["harmonized", "elevated", "absorbed"]
            ).order_by("-id")
            if isinstance(e.event_data, dict) and e.event_data.get("job_id") == job_id
        ),
        None,
    )
    if ev is None:
        raise ValueError(f"Harmonization job '{job_id}' not found in EventLog.")

    data = ev.event_data

    # 1. Handling for elevation or absorption jobs
    if ev.event_type in ("elevated", "absorbed") or data.get("job_type") in ("elevate", "absorb"):
        resource_type = data.get("resource_type", "")
        model_cls = _get_model_for_type(resource_type)
        generic_urn = data.get("generic_urn", "")
        source_urns = data.get("source_urns", [])
        source_snapshots = data.get("source_snapshots", [])
        created_aliases = data.get("created_aliases", [])
        created_rel_ids = data.get("created_rel_ids", [])
        retire_sources = data.get("retire_sources", True)

        with transaction.atomic():
            # Re-create retired sources
            if retire_sources and model_cls is not None:
                for snap in source_snapshots:
                    s_urn = snap["urn"]
                    if not model_cls.objects.filter(urn=s_urn).exists():
                        create_kwargs: dict[str, Any] = {"urn": s_urn}
                        for fld in (
                            "name",
                            "label",
                            "description",
                            "hashes",
                            "question_text",
                            "interviewer_instructions",
                            "definition",
                            "vocabulary",
                            "notation",
                            "extended_attributes",
                            "response_domain",
                            "value_representation",
                        ):
                            if fld in snap and snap[fld] is not None:
                                create_kwargs[fld] = snap[fld]
                        for fk_fld in (
                            "code_list_id",
                            "conceptual_variable_id",
                            "concept_id",
                            "scheme_id",
                        ):
                            if fk_fld in snap and snap[fk_fld]:
                                create_kwargs[fk_fld] = snap[fk_fld]
                        model_cls.objects.create(**create_kwargs)

            # If absorption, restore target_obj to pre-snapshot
            is_absorption = data.get("is_absorption", False)
            target_pre_snapshot = data.get("target_pre_snapshot")
            target_reg_ext_attrs = data.get("target_reg_ext_attrs")
            repointed_refs = data.get("repointed_references", [])

            if is_absorption and target_pre_snapshot and model_cls:
                target_obj = model_cls.objects.filter(urn=generic_urn).first()
                if target_obj is not None:
                    for fld in (
                        "name",
                        "label",
                        "description",
                        "hashes",
                        "extended_attributes",
                        "question_text",
                        "interviewer_instructions",
                        "definition",
                        "response_domain",
                        "value_representation",
                    ):
                        if fld in target_pre_snapshot and hasattr(target_obj, fld):
                            setattr(target_obj, fld, target_pre_snapshot[fld])
                    target_obj.save()

                if target_reg_ext_attrs is not None:
                    UrnRegistry.objects.filter(urn=generic_urn).update(
                        extended_attributes=target_reg_ext_attrs
                    )

            # Re-create retired sources
            if retire_sources and model_cls is not None:
                for snap in source_snapshots:
                    s_urn = snap["urn"]
                    if not model_cls.objects.filter(urn=s_urn).exists():
                        create_kwargs: dict[str, Any] = {"urn": s_urn}
                        for fld in (
                            "name",
                            "label",
                            "description",
                            "hashes",
                            "question_text",
                            "interviewer_instructions",
                            "definition",
                            "vocabulary",
                            "notation",
                            "extended_attributes",
                            "response_domain",
                            "value_representation",
                        ):
                            if fld in snap and snap[fld] is not None:
                                create_kwargs[fld] = snap[fld]
                        for fk_fld in (
                            "code_list_id",
                            "conceptual_variable_id",
                            "concept_id",
                            "scheme_id",
                        ):
                            if fk_fld in snap and snap[fk_fld]:
                                create_kwargs[fk_fld] = snap[fk_fld]
                        model_cls.objects.create(**create_kwargs)

            # Restore UrnRegistry status for source URNs to 'active'
            UrnRegistry.objects.filter(urn__in=source_urns).update(status="active")

            # Restore references
            if repointed_refs:
                for item in repointed_refs:
                    action = item.get("action", "update")
                    tbl = item["table"]
                    ref_model = _get_model_for_type(tbl)
                    if ref_model is None:
                        from fairwddi.models import (
                            Code,
                            InstrumentQuestion,
                            QuestionVariable,
                        )

                        if tbl == "QuestionVariable":
                            ref_model = QuestionVariable
                        elif tbl == "InstrumentQuestion":
                            ref_model = InstrumentQuestion
                        elif tbl == "Code":
                            ref_model = Code
                    if ref_model:
                        if action == "deleted_duplicate":
                            ref_model.objects.create(**item["data"])
                        else:
                            ref_model.objects.filter(**item["filter"]).update(
                                **{item["field"]: item["old_val"]}
                            )
            else:
                primary_src = source_urns[0] if source_urns else None
                if primary_src:
                    if resource_type == "QuestionItem":
                        QuestionVariable.objects.filter(question_item_id=generic_urn).update(
                            question_item_id=primary_src
                        )
                        InstrumentQuestion.objects.filter(question_item_id=generic_urn).update(
                            question_item_id=primary_src
                        )
                    elif resource_type == "RepresentedVariable":
                        InstanceVariable.objects.filter(represented_variable_id=generic_urn).update(
                            represented_variable_id=primary_src
                        )
                        QuestionVariable.objects.filter(represented_variable_id=generic_urn).update(
                            represented_variable_id=primary_src
                        )
                    elif resource_type == "ConceptualVariable":
                        RepresentedVariable.objects.filter(conceptual_variable_id=generic_urn).update(
                            conceptual_variable_id=primary_src
                        )
                    elif resource_type == "CodeList":
                        QuestionItem.objects.filter(code_list_id=generic_urn).update(
                            code_list_id=primary_src
                        )
                        RepresentedVariable.objects.filter(code_list_id=generic_urn).update(
                            code_list_id=primary_src
                        )
                        Code.objects.filter(code_list_id=generic_urn).update(code_list_id=primary_src)
                    elif resource_type == "Category":
                        Code.objects.filter(category_id=generic_urn).update(category_id=primary_src)
                    elif resource_type == "Concept":
                        RepresentedVariable.objects.filter(concept_id=generic_urn).update(
                            concept_id=primary_src
                        )

            # Remove aliases & relationships
            if created_aliases:
                URNAlias.objects.filter(alias_urn__in=created_aliases).delete()
            if created_rel_ids:
                SemanticRelationship.objects.filter(id__in=created_rel_ids).delete()
            SemanticRelationship.objects.filter(
                object_urn=generic_urn, subject_urn__in=source_urns
            ).delete()

            # Delete generic object & clean UrnRegistry ONLY if not absorption
            if not is_absorption:
                if model_cls is not None:
                    model_cls.objects.filter(urn=generic_urn).delete()
                UrnRegistry.objects.filter(urn=generic_urn).delete()

            ev.delete()

        logger.info(
            "Reverted %s job %s: restored %d sources, removed %d aliases",
            "absorption" if is_absorption else "elevation",
            job_id,
            len(source_snapshots),
            len(created_aliases),
        )

        return {
            "job_id": job_id,
            "status": "reverted",
            "is_absorption": is_absorption,
            "target_urn": generic_urn,
            "restored_sources": len(source_snapshots),
            "removed_generic_urn": None if is_absorption else generic_urn,
            "removed_aliases": len(created_aliases),
        }

    # 2. Handling for standard harmonization jobs
    created_aliases = data.get("created_aliases", [])
    created_rel_ids = data.get("created_rel_ids", [])
    target_snapshots = data.get("target_snapshots", [])
    repointed_ivs = data.get("repointed_ivs", [])
    repointed_qvs = data.get("repointed_qvs", [])

    with transaction.atomic():
        for iv_entry in repointed_ivs:
            InstanceVariable.objects.filter(urn=iv_entry["iv_urn"]).update(
                represented_variable_id=iv_entry["old_rv_urn"]
            )

        for qv_entry in repointed_qvs:
            QuestionVariable.objects.filter(id=qv_entry["qv_id"]).update(
                question_item_id=qv_entry["old_q_urn"]
            )

        for snap in reversed(target_snapshots):
            model_cls = _get_model_for_type(snap["resource_type"])
            if model_cls is None:
                continue
            obj = model_cls.objects.filter(urn=snap["urn"]).first()
            if obj is not None:
                obj.label = snap.get("label")
                obj.description = snap.get("description")
                obj.hashes = snap.get("hashes")
                if snap["resource_type"] == "QuestionItem":
                    obj.question_text = snap.get("question_text")
                    obj.interviewer_instructions = snap.get("interviewer_instructions")
                obj.save()

        if created_aliases:
            URNAlias.objects.filter(alias_urn__in=created_aliases).delete()
        if created_rel_ids:
            SemanticRelationship.objects.filter(id__in=created_rel_ids).delete()

        ev.delete()

    return {
        "job_id": job_id,
        "status": "reverted",
        "restored_targets": len(target_snapshots),
        "removed_aliases": len(created_aliases),
        "removed_semantic_links": len(created_rel_ids),
    }


def elevate_resource(
    source_urns: list[str] | str,
    generic_urn: str | None = None,
    resource_type: str | None = None,
    generic_name: list[dict[str, str]] | str | None = None,
    agency: str | None = None,
    retire_sources: bool = True,
    update_references: bool = True,
    provenance_note: str = "",
    allow_existing: bool = False,
    is_absorption: bool = False,
) -> dict[str, Any]:
    """Elevate one or more study-specific resources into a generic harmonized resource.

    Args:
        source_urns: One or more study-specific URNs to elevate/merge.
        generic_urn: Optional explicit canonical DDI URN (auto-generated if omitted).
        resource_type: Optional DDI Model name. Auto-inferred from source URNs if omitted.
        generic_name: Optional human label or multilingual name list for the elevated resource.
        agency: DDI maintenance agency identifier (defaults to DDI_AGENCY or 'fr.cdsp').
        retire_sources: If True, deletes superseded source rows while maintaining URNAliases.
        update_references: If True, updates foreign keys and junction tables across cascade.
        provenance_note: Audit note stored in URNAlias / EventLog.
        allow_existing: If True, permits target generic_urn to already exist (used for absorb).
        is_absorption: If True, performs absorption into an existing target resource.

    Returns:
        Summary dict containing job_id, generic_urn, source_urns, and update statistics.
    """
    from fairwddi.models import UrnRegistry

    if isinstance(source_urns, str):
        sources_list = [source_urns.strip()]
    else:
        sources_list = [s.strip() for s in source_urns if s and s.strip()]

    # Deduplicate while preserving order
    sources_list = list(dict.fromkeys(sources_list))
    if generic_urn:
        generic_urn = generic_urn.strip()
        if generic_urn in sources_list:
            sources_list = [s for s in sources_list if s != generic_urn]

    if not sources_list:
        raise ValueError("At least one source_urn (distinct from target URN) must be provided.")

    target_exists = False
    if generic_urn:
        if not validate_ddi_urn(generic_urn):
            raise ValueError(
                f"Invalid canonical DDI URN '{generic_urn}'. "
                "Must match 'urn:ddi:agency:identifier:version'."
            )
        target_exists = UrnRegistry.objects.filter(urn=generic_urn).exists()
        if is_absorption and not target_exists:
            raise ValueError(
                f"Target URN '{generic_urn}' does not exist in UrnRegistry. "
                "Cannot absorb into a non-existent resource. "
                "Use 'elevate_resource' (or 'fairwddi harmonize elevate') to create new resource."
            )
        if target_exists and not allow_existing:
            raise ValueError(
                f"Target generic URN '{generic_urn}' already exists in UrnRegistry. "
                "Use 'absorb_resource' (or 'fairwddi harmonize absorb') to absorb resources."
            )

    # Infer resource_type from target or sources
    if not resource_type:
        if target_exists:
            reg_target = UrnRegistry.objects.filter(urn=generic_urn).first()
            if reg_target:
                resource_type = reg_target.resource_type
        if not resource_type:
            reg_entries = list(UrnRegistry.objects.filter(urn__in=sources_list))
            if reg_entries:
                types = {r.resource_type for r in reg_entries}
                if len(types) > 1:
                    raise ValueError(
                        f"Source URNs have mismatched resource types: {sorted(types)}. "
                        "All sources to elevate must belong to the same resource type."
                    )
                resource_type = types.pop()
            else:
                for candidate in (
                    "QuestionItem",
                    "RepresentedVariable",
                    "ConceptualVariable",
                    "CodeList",
                    "Category",
                    "Concept",
                    "StudyUnit",
                    "Instrument",
                ):
                    cand_cls = _get_model_for_type(candidate)
                    if cand_cls and cand_cls.objects.filter(urn=sources_list[0]).exists():
                        resource_type = candidate
                        break
        if not resource_type:
            raise ValueError(
                f"Could not infer resource type for source URN '{sources_list[0]}'. "
                "Ensure source exists in database or specify resource_type explicitly."
            )
    else:
        reg_entries = list(UrnRegistry.objects.filter(urn__in=sources_list))
        mismatches = [r.urn for r in reg_entries if r.resource_type != resource_type]
        if mismatches:
            raise ValueError(
                f"Source URN(s) {mismatches} do not match resource type '{resource_type}'."
            )
        if target_exists:
            reg_t = UrnRegistry.objects.filter(urn=generic_urn).first()
            if reg_t and reg_t.resource_type != resource_type:
                raise ValueError(
                    f"Target URN '{generic_urn}' has resource type '{reg_t.resource_type}', "
                    f"which does not match requested type '{resource_type}'."
                )

    model_cls = _get_model_for_type(resource_type)
    if model_cls is None:
        raise ValueError(
            f"Unsupported resource type '{resource_type}'. Supported: "
            "Category, CodeList, QuestionItem, RepresentedVariable, Concept, "
            "ConceptualVariable, StudyUnit, Instrument."
        )

    sources = list(model_cls.objects.filter(urn__in=sources_list))
    found_urns = {s.urn for s in sources}
    missing_urns = [u for u in sources_list if u not in found_urns]
    if missing_urns:
        raise ValueError(
            f"Source {resource_type} record(s) not found in database: {sorted(missing_urns)}"
        )

    # 1. Resolve & Validate Canonical Generic URN if not provided
    if not generic_urn:
        slug_seed = None
        if isinstance(generic_name, str) and generic_name:
            slug_seed = generic_name
        elif isinstance(generic_name, list) and generic_name:
            slug_seed = generic_name[0].get("value")
        if not slug_seed and sources:
            first = sources[0]
            if hasattr(first, "question_text") and first.question_text:
                qd = _to_dict_form(first.question_text)
                slug_seed = (
                    qd.get("fr") or qd.get("en") or (next(iter(qd.values())) if qd else None)
                )
            if not slug_seed and hasattr(first, "label") and first.label:
                ld = _to_dict_form(first.label)
                slug_seed = (
                    ld.get("fr") or ld.get("en") or (next(iter(ld.values())) if ld else None)
                )
            if not slug_seed and hasattr(first, "name") and first.name:
                if isinstance(first.name, list) and first.name:
                    slug_seed = first.name[0].get("value")
                elif isinstance(first.name, str):
                    slug_seed = first.name

        generic_urn = generate_generic_urn(
            resource_type=resource_type,
            name_or_text=slug_seed,
            agency=agency,
        )

    # 2. Absorption vs Elevation Preparation
    target_obj = None
    target_pre_snapshot: dict[str, Any] | None = None
    target_reg_ext_attrs: list[Any] | None = None
    create_kwargs: dict[str, Any] = {}

    if is_absorption:
        target_obj = model_cls.objects.filter(urn=generic_urn).first()
        if not target_obj:
            raise ValueError(
                f"Target {resource_type} record '{generic_urn}' not found in database."
            )
        target_pre_snapshot = {
            "urn": target_obj.urn,
            "name": getattr(target_obj, "name", None),
            "label": getattr(target_obj, "label", None),
            "description": getattr(target_obj, "description", None),
            "hashes": getattr(target_obj, "hashes", None),
            "extended_attributes": getattr(target_obj, "extended_attributes", None),
        }
        if resource_type == "QuestionItem":
            target_pre_snapshot["question_text"] = getattr(target_obj, "question_text", None)
            target_pre_snapshot["interviewer_instructions"] = getattr(
                target_obj, "interviewer_instructions", None
            )
            target_pre_snapshot["response_domain"] = getattr(
                target_obj, "response_domain", None
            )
        elif resource_type == "RepresentedVariable":
            target_pre_snapshot["value_representation"] = getattr(
                target_obj, "value_representation", None
            )
        elif resource_type == "Concept":
            target_pre_snapshot["definition"] = getattr(target_obj, "definition", None)

        reg_t_obj = UrnRegistry.objects.filter(urn=generic_urn).first()
        target_reg_ext_attrs = reg_t_obj.extended_attributes if reg_t_obj else None

        # Multilingual fusion directly onto target_obj
        for s in sources:
            if hasattr(s, "label") and s.label:
                target_obj.label = _merge_jsonb_dicts(target_obj.label, s.label)
            if hasattr(s, "description") and s.description:
                target_obj.description = _merge_jsonb_dicts(target_obj.description, s.description)
            if hasattr(s, "question_text") and s.question_text:
                target_obj.question_text = _merge_jsonb_dicts(
                    target_obj.question_text, s.question_text
                )
            if hasattr(s, "interviewer_instructions") and s.interviewer_instructions:
                target_obj.interviewer_instructions = _merge_jsonb_dicts(
                    target_obj.interviewer_instructions, s.interviewer_instructions
                )
            if hasattr(s, "definition") and s.definition:
                target_obj.definition = _merge_jsonb_dicts(target_obj.definition, s.definition)
            if hasattr(s, "extended_attributes") and isinstance(s.extended_attributes, list):
                target_ext = list(target_obj.extended_attributes or [])
                for item in s.extended_attributes:
                    if item not in target_ext:
                        target_ext.append(item)
                target_obj.extended_attributes = target_ext

        # Recompute hashes for target_obj
        hash_payload: dict[str, Any] = {
            "name": target_obj.name,
            "label": target_obj.label,
            "description": target_obj.description,
        }
        if resource_type == "QuestionItem" and hasattr(target_obj, "question_text"):
            hash_payload["question_text"] = target_obj.question_text
        elif resource_type == "Concept" and hasattr(target_obj, "definition"):
            hash_payload["definition"] = target_obj.definition

        target_obj.hashes = compute_resource_hashes(resource_type, hash_payload)
        job_id = f"absorb-{resource_type.lower()}-{uuid.uuid4().hex[:6]}"
    else:
        # Determine Name for newly elevated resource
        if isinstance(generic_name, str) and generic_name:
            eff_name = [{"value": generic_name}]
        elif isinstance(generic_name, list) and generic_name:
            eff_name = generic_name
        elif sources and hasattr(sources[0], "name") and sources[0].name:
            first_name = sources[0].name
            eff_name = first_name if isinstance(first_name, list) else [{"value": str(first_name)}]
        else:
            eff_name = [{"value": f"Generic {resource_type}"}]

        # Multilingual Fusion & Hashes across sources
        merged_label = None
        merged_desc = None
        merged_qt = None
        merged_inst = None
        merged_def = None
        merged_ext: list[Any] = []

        for s in sources:
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
            if hasattr(s, "extended_attributes") and isinstance(s.extended_attributes, list):
                for item in s.extended_attributes:
                    if item not in merged_ext:
                        merged_ext.append(item)

        hash_payload = {
            "name": eff_name,
            "label": merged_label,
            "description": merged_desc,
        }
        if resource_type == "QuestionItem" and merged_qt:
            hash_payload["question_text"] = merged_qt
        elif resource_type == "Concept" and merged_def:
            hash_payload["definition"] = merged_def

        hashes = compute_resource_hashes(resource_type, hash_payload)

        first_src = sources[0]
        create_kwargs = {
            "urn": generic_urn,
            "name": eff_name,
            "hashes": hashes,
        }
        if merged_label is not None:
            create_kwargs["label"] = merged_label
        if merged_desc is not None:
            create_kwargs["description"] = merged_desc
        if merged_ext:
            create_kwargs["extended_attributes"] = merged_ext
        if hasattr(first_src, "scheme_id") and first_src.scheme_id:
            create_kwargs["scheme_id"] = first_src.scheme_id

        if resource_type == "QuestionItem":
            if merged_qt is not None:
                create_kwargs["question_text"] = merged_qt
            if merged_inst is not None:
                create_kwargs["interviewer_instructions"] = merged_inst
            if hasattr(first_src, "code_list_id") and first_src.code_list_id:
                create_kwargs["code_list_id"] = first_src.code_list_id
            if hasattr(first_src, "response_domain") and first_src.response_domain:
                create_kwargs["response_domain"] = first_src.response_domain
        elif resource_type == "RepresentedVariable":
            if hasattr(first_src, "conceptual_variable_id") and first_src.conceptual_variable_id:
                create_kwargs["conceptual_variable_id"] = first_src.conceptual_variable_id
            if hasattr(first_src, "code_list_id") and first_src.code_list_id:
                create_kwargs["code_list_id"] = first_src.code_list_id
            if hasattr(first_src, "value_representation") and first_src.value_representation:
                create_kwargs["value_representation"] = first_src.value_representation
        elif resource_type == "Concept":
            if merged_def is not None:
                create_kwargs["definition"] = merged_def
            if hasattr(first_src, "vocabulary") and first_src.vocabulary:
                create_kwargs["vocabulary"] = first_src.vocabulary
            if hasattr(first_src, "notation") and first_src.notation:
                create_kwargs["notation"] = first_src.notation
        elif resource_type == "ConceptualVariable":
            if hasattr(first_src, "concept_id") and first_src.concept_id:
                create_kwargs["concept_id"] = first_src.concept_id
        elif resource_type == "Category":
            if hasattr(first_src, "concept_id") and first_src.concept_id:
                create_kwargs["concept_id"] = first_src.concept_id

        job_id = f"elevate-{resource_type.lower()}-{uuid.uuid4().hex[:6]}"

    # 3. Snapshots of sources for rollback
    source_snapshots: list[dict[str, Any]] = []
    for s in sources:
        snap: dict[str, Any] = {
            "urn": s.urn,
            "name": getattr(s, "name", None),
            "label": getattr(s, "label", None),
            "description": getattr(s, "description", None),
            "hashes": getattr(s, "hashes", None),
            "scheme_id": getattr(s, "scheme_id", None),
            "extended_attributes": getattr(s, "extended_attributes", None),
        }
        if resource_type == "QuestionItem":
            snap["question_text"] = getattr(s, "question_text", None)
            snap["interviewer_instructions"] = getattr(s, "interviewer_instructions", None)
            snap["code_list_id"] = getattr(s, "code_list_id", None)
            snap["response_domain"] = getattr(s, "response_domain", None)
        elif resource_type == "RepresentedVariable":
            snap["conceptual_variable_id"] = getattr(s, "conceptual_variable_id", None)
            snap["code_list_id"] = getattr(s, "code_list_id", None)
            snap["value_representation"] = getattr(s, "value_representation", None)
        elif resource_type == "Concept":
            snap["definition"] = getattr(s, "definition", None)
            snap["vocabulary"] = getattr(s, "vocabulary", None)
            snap["notation"] = getattr(s, "notation", None)
        elif resource_type == "ConceptualVariable":
            snap["concept_id"] = getattr(s, "concept_id", None)
        elif resource_type == "Category":
            snap["concept_id"] = getattr(s, "concept_id", None)
        source_snapshots.append(snap)

    created_aliases: list[str] = []
    created_rel_ids: list[int] = []
    updated_references_summary: dict[str, int] = {}
    repointed_references: list[dict[str, Any]] = []

    with transaction.atomic():
        from fairwddi.models import (
            Code,
            EventLog,
            Group,
            InstanceVariable,
            InstrumentQuestion,
            QuestionItem,
            QuestionVariable,
            RepresentedVariable,
            SemanticRelationship,
            URNAlias,
        )

        if is_absorption:
            absorption_meta = {
                "type": "absorption",
                "job_id": job_id,
                "absorbed_urns": sources_list,
                "note": provenance_note,
            }
            target_ext = list(target_obj.extended_attributes or [])
            target_ext.append(absorption_meta)
            target_obj.extended_attributes = target_ext
            target_obj.save()

            if reg_t_obj:
                reg_ext = list(reg_t_obj.extended_attributes or [])
                reg_ext.append(absorption_meta)
                reg_t_obj.extended_attributes = reg_ext
                reg_t_obj.save(update_fields=["extended_attributes"])
        else:
            elevation_meta = {
                "type": "elevation",
                "is_elevated": True,
                "source_urns": sources_list,
                "job_id": job_id,
            }
            UrnRegistry.objects.update_or_create(
                urn=generic_urn,
                defaults={
                    "resource_type": resource_type,
                    "status": "elevated",
                    "extended_attributes": [elevation_meta],
                },
            )
            create_kwargs.setdefault("extended_attributes", []).append(elevation_meta)
            model_cls.objects.create(**create_kwargs)

        # Aliases & Semantic Relationships
        for s_urn in sources_list:
            if not URNAlias.objects.filter(alias_urn=s_urn).exists():
                URNAlias.objects.create(
                    alias_urn=s_urn,
                    canonical_urn=generic_urn,
                    entity_type=resource_type,
                    hash_strategy=(
                        "harmonization_absorption"
                        if is_absorption
                        else "harmonization_elevation"
                    ),
                    source_file=provenance_note or f"fairwddi.harmonize:{job_id}",
                )
                created_aliases.append(s_urn)

            URNAlias.objects.filter(canonical_urn=s_urn).exclude(alias_urn=generic_urn).update(
                canonical_urn=generic_urn
            )

            rel, created = SemanticRelationship.objects.get_or_create(
                subject_urn=s_urn,
                predicate="skos:exactMatch",
                object_urn=generic_urn,
                defaults={
                    "subject_type": resource_type,
                    "object_type": resource_type,
                    "extended_attributes": [
                        {"type": "provenance", "value": f"fairwddi.harmonize:{job_id}"}
                    ],
                },
            )
            if created:
                created_rel_ids.append(rel.id)

        # Update References across the DDI cascade if requested
        if update_references:
            if resource_type == "QuestionItem":
                qv_updated = 0
                for qv in list(QuestionVariable.objects.filter(question_item_id__in=sources_list)):
                    if QuestionVariable.objects.filter(
                        question_item_id=generic_urn,
                        represented_variable_id=qv.represented_variable_id,
                    ).exists():
                        repointed_references.append({
                            "table": "QuestionVariable",
                            "action": "deleted_duplicate",
                            "data": {
                                "represented_variable_id": qv.represented_variable_id,
                                "question_item_id": qv.question_item_id,
                            },
                        })
                        qv.delete()
                    else:
                        repointed_references.append({
                            "table": "QuestionVariable",
                            "filter": {"id": qv.id},
                            "field": "question_item_id",
                            "old_val": qv.question_item_id,
                        })
                        qv.question_item_id = generic_urn
                        qv.save(update_fields=["question_item"])
                        qv_updated += 1
                updated_references_summary["QuestionVariable"] = qv_updated

                iq_updated = 0
                for iq in list(
                    InstrumentQuestion.objects.filter(question_item_id__in=sources_list)
                ):
                    if InstrumentQuestion.objects.filter(
                        question_item_id=generic_urn,
                        instrument_id=iq.instrument_id,
                    ).exists():
                        repointed_references.append({
                            "table": "InstrumentQuestion",
                            "action": "deleted_duplicate",
                            "data": {
                                "instrument_id": iq.instrument_id,
                                "question_item_id": iq.question_item_id,
                            },
                        })
                        iq.delete()
                    else:
                        repointed_references.append({
                            "table": "InstrumentQuestion",
                            "filter": {"id": iq.id},
                            "field": "question_item_id",
                            "old_val": iq.question_item_id,
                        })
                        iq.question_item_id = generic_urn
                        iq.save(update_fields=["question_item"])
                        iq_updated += 1
                updated_references_summary["InstrumentQuestion"] = iq_updated

            elif resource_type == "RepresentedVariable":
                iv_updated = 0
                for iv in list(InstanceVariable.objects.filter(
                    represented_variable_id__in=sources_list
                )):
                    repointed_references.append({
                        "table": "InstanceVariable",
                        "filter": {"urn": iv.urn},
                        "field": "represented_variable_id",
                        "old_val": iv.represented_variable_id,
                    })
                    iv.represented_variable_id = generic_urn
                    iv.save(update_fields=["represented_variable"])
                    iv_updated += 1
                updated_references_summary["InstanceVariable"] = iv_updated

                qv_updated = 0
                for qv in list(
                    QuestionVariable.objects.filter(represented_variable_id__in=sources_list)
                ):
                    if QuestionVariable.objects.filter(
                        represented_variable_id=generic_urn,
                        question_item_id=qv.question_item_id,
                    ).exists():
                        repointed_references.append({
                            "table": "QuestionVariable",
                            "action": "deleted_duplicate",
                            "data": {
                                "represented_variable_id": qv.represented_variable_id,
                                "question_item_id": qv.question_item_id,
                            },
                        })
                        qv.delete()
                    else:
                        repointed_references.append({
                            "table": "QuestionVariable",
                            "filter": {"id": qv.id},
                            "field": "represented_variable_id",
                            "old_val": qv.represented_variable_id,
                        })
                        qv.represented_variable_id = generic_urn
                        qv.save(update_fields=["represented_variable"])
                        qv_updated += 1
                updated_references_summary["QuestionVariable"] = qv_updated

            elif resource_type == "ConceptualVariable":
                rv_updated = 0
                for rv in list(RepresentedVariable.objects.filter(
                    conceptual_variable_id__in=sources_list
                )):
                    repointed_references.append({
                        "table": "RepresentedVariable",
                        "filter": {"urn": rv.urn},
                        "field": "conceptual_variable_id",
                        "old_val": rv.conceptual_variable_id,
                    })
                    rv.conceptual_variable_id = generic_urn
                    rv.save(update_fields=["conceptual_variable"])
                    rv_updated += 1
                updated_references_summary["RepresentedVariable.conceptual_variable"] = rv_updated

            elif resource_type == "CodeList":
                qi_updated = 0
                for qi in list(QuestionItem.objects.filter(code_list_id__in=sources_list)):
                    repointed_references.append({
                        "table": "QuestionItem",
                        "filter": {"urn": qi.urn},
                        "field": "code_list_id",
                        "old_val": qi.code_list_id,
                    })
                    qi.code_list_id = generic_urn
                    qi.save(update_fields=["code_list"])
                    qi_updated += 1

                rv_updated = 0
                for rv in list(RepresentedVariable.objects.filter(code_list_id__in=sources_list)):
                    repointed_references.append({
                        "table": "RepresentedVariable",
                        "filter": {"urn": rv.urn},
                        "field": "code_list_id",
                        "old_val": rv.code_list_id,
                    })
                    rv.code_list_id = generic_urn
                    rv.save(update_fields=["code_list"])
                    rv_updated += 1

                code_updated = 0
                for c in list(Code.objects.filter(code_list_id__in=sources_list)):
                    repointed_references.append({
                        "table": "Code",
                        "filter": {"urn": c.urn},
                        "field": "code_list_id",
                        "old_val": c.code_list_id,
                    })
                    c.code_list_id = generic_urn
                    c.save(update_fields=["code_list"])
                    code_updated += 1

                updated_references_summary["QuestionItem.code_list"] = qi_updated
                updated_references_summary["RepresentedVariable.code_list"] = rv_updated
                updated_references_summary["Code.code_list"] = code_updated

                for qi in QuestionItem.objects.all():
                    if (
                        isinstance(qi.response_domain, dict)
                        and qi.response_domain.get("code_list_urn") in sources_list
                    ):
                        qi.response_domain["code_list_urn"] = generic_urn
                        qi.save(update_fields=["response_domain", "updated_at"])

                for rv in RepresentedVariable.objects.all():
                    if (
                        isinstance(rv.value_representation, dict)
                        and rv.value_representation.get("code_list_urn") in sources_list
                    ):
                        rv.value_representation["code_list_urn"] = generic_urn
                        rv.save(update_fields=["value_representation", "updated_at"])

            elif resource_type == "Category":
                c_updated = 0
                for c in list(Code.objects.filter(category_id__in=sources_list)):
                    repointed_references.append({
                        "table": "Code",
                        "filter": {"urn": c.urn},
                        "field": "category_id",
                        "old_val": c.category_id,
                    })
                    c.category_id = generic_urn
                    c.save(update_fields=["category"])
                    c_updated += 1
                updated_references_summary["Code.category"] = c_updated

            elif resource_type == "Concept":
                from fairwddi.models import ConceptualVariable

                rv_updated = 0
                for rv in list(RepresentedVariable.objects.filter(concept_id__in=sources_list)):
                    repointed_references.append({
                        "table": "RepresentedVariable",
                        "filter": {"urn": rv.urn},
                        "field": "concept_id",
                        "old_val": rv.concept_id,
                    })
                    rv.concept_id = generic_urn
                    rv.save(update_fields=["concept"])
                    rv_updated += 1

                cv_updated = 0
                for cv in list(ConceptualVariable.objects.filter(concept_id__in=sources_list)):
                    repointed_references.append({
                        "table": "ConceptualVariable",
                        "filter": {"urn": cv.urn},
                        "field": "concept_id",
                        "old_val": cv.concept_id,
                    })
                    cv.concept_id = generic_urn
                    cv.save(update_fields=["concept"])
                    cv_updated += 1

                updated_references_summary["RepresentedVariable.concept"] = rv_updated
                updated_references_summary["ConceptualVariable.concept"] = cv_updated

            grp_updated = 0
            for grp in Group.objects.all():
                if isinstance(grp.references, list):
                    modified = False
                    for ref in grp.references:
                        if isinstance(ref, dict) and ref.get("urn") in sources_list:
                            ref["urn"] = generic_urn
                            modified = True
                    if modified:
                        grp.save(update_fields=["references", "updated_at"])
                        grp_updated += 1
            if grp_updated:
                updated_references_summary["Group.references"] = grp_updated

        # Handle source records disposition
        if retire_sources:
            model_cls.objects.filter(urn__in=sources_list).delete()
            for s_urn in sources_list:
                UrnRegistry.objects.update_or_create(
                    urn=s_urn,
                    defaults={"resource_type": resource_type, "status": "superseded"},
                )
        else:
            UrnRegistry.objects.filter(urn__in=sources_list).update(status="superseded")

        # Record EventLog snapshot
        EventLog.objects.create(
            urn=generic_urn,
            event_type="absorbed" if is_absorption else "elevated",
            event_data={
                "job_type": "absorb" if is_absorption else "elevate",
                "job_id": job_id,
                "is_absorption": is_absorption,
                "resource_type": resource_type,
                "generic_urn": generic_urn,
                "target_urn": generic_urn,
                "source_urns": sources_list,
                "target_pre_snapshot": target_pre_snapshot,
                "target_reg_ext_attrs": target_reg_ext_attrs,
                "source_snapshots": source_snapshots,
                "repointed_references": repointed_references,
                "created_aliases": created_aliases,
                "created_rel_ids": created_rel_ids,
                "retire_sources": retire_sources,
                "update_references": update_references,
                "updated_references_summary": updated_references_summary,
            },
        )

    action_label = "Absorbed" if is_absorption else "Elevated"
    logger.info(
        "%s %d %s source(s) into %s (job_id: %s, aliases: %d)",
        action_label,
        len(sources_list),
        resource_type,
        generic_urn,
        job_id,
        len(created_aliases),
    )

    return {
        "job_id": job_id,
        "generic_urn": generic_urn,
        "target_urn": generic_urn,
        "resource_type": resource_type,
        "source_urns": sources_list,
        "is_absorption": is_absorption,
        "aliases_created": len(created_aliases),
        "semantic_links_created": len(created_rel_ids),
        "retired_sources": retire_sources,
        "updated_references": updated_references_summary,
    }


def absorb_resource(
    source_urns: list[str] | str,
    into_urn: str,
    resource_type: str | None = None,
    update_references: bool = True,
    retire_sources: bool = True,
    provenance_note: str = "",
) -> dict[str, Any]:
    """Absorb one or more study resources into an existing harmonized/elevated resource.

    Merges any new multilingual translations, instructions, or extended attributes into
    the existing target resource, recomputes content hashes, repoints foreign keys
    and junction tables across the DDI cascade, records canonical aliases in URNAlias,
    and retires superseded source records.

    Args:
        source_urns: One or more study-specific URNs to absorb.
        into_urn: Target canonical harmonized/elevated URN (must already exist).
        resource_type: Optional DDI Model name. Auto-inferred from into_urn if omitted.
        update_references: If True, updates foreign keys and junction tables.
        retire_sources: If True, retires source records from primary entity table.
        provenance_note: Audit note stored in URNAlias / EventLog.

    Returns:
        Summary dict containing job_id, target_urn, source_urns, and update statistics.
    """
    into_urn = into_urn.strip()
    return elevate_resource(
        source_urns=source_urns,
        generic_urn=into_urn,
        resource_type=resource_type,
        retire_sources=retire_sources,
        update_references=update_references,
        provenance_note=provenance_note,
        allow_existing=True,
        is_absorption=True,
    )


def migrate_urn(
    old_urn: str,
    new_urn: str,
    resource_type: str | None = None,
    provenance_note: str = "",
) -> dict[str, Any]:
    """Atomically rename a resource URN to a new canonical URN, updating all references."""
    from fairwddi.models import UrnRegistry

    old_urn = old_urn.strip()
    new_urn = new_urn.strip()

    if not resource_type:
        reg = UrnRegistry.objects.filter(urn=old_urn).first()
        if not reg:
            raise ValueError(f"Old URN '{old_urn}' not found in UrnRegistry.")
        resource_type = reg.resource_type

    logger.info("Migrating URN from '%s' to '%s' (%s)", old_urn, new_urn, resource_type)
    return elevate_resource(
        source_urns=[old_urn],
        generic_urn=new_urn,
        resource_type=resource_type,
        retire_sources=True,
        update_references=True,
        provenance_note=provenance_note or f"fairwddi.harmonize.migrate_urn:{old_urn}->{new_urn}",
    )
