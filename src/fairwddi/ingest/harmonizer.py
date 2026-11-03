"""Stage 3b (Harmonization & Undo): Review-gated harmonization planning, execution, and rollback.

Supports:
- Multilingual label/question text merging (`merge_multilingual`)
- Canonical URN aliasing & cascade pointer consolidation (`alias` / `harmonize`)
- Semantic relationship linking (`link_semantic` -> skos:exactMatch / skos:closeMatch)
- Full transactional rollback (`undo_harmonization`) via EventLog snapshots
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from django.db import transaction

from fairwddi.ingest.comparator import discover_candidates
from fairwddi.ingest.loader import compute_resource_hashes
from fairwddi.ingest.plan import IngestPlan, PlanActionItem, ReviewGate


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
        CodeList,
        Concept,
        ConceptualVariable,
        QuestionItem,
        RepresentedVariable,
    )

    return {
        "Category": Category,
        "CodeList": CodeList,
        "QuestionItem": QuestionItem,
        "RepresentedVariable": RepresentedVariable,
        "Concept": Concept,
        "ConceptualVariable": ConceptualVariable,
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
    if isinstance(target_val, list):
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

    return {
        "job_id": plan.job_id,
        "merged_multilingual_count": merged_count,
        "aliased_count": aliased_count,
        "semantic_links_created": linked_count,
        "repointed_instance_variables": len(repointed_ivs),
    }


def undo_harmonization(job_id: str) -> dict[str, Any]:
    """Revert an applied Harmonization Job using its EventLog snapshot."""
    from fairwddi.models import (
        EventLog,
        InstanceVariable,
        QuestionVariable,
        SemanticRelationship,
        URNAlias,
    )

    ev = next(
        (
            e
            for e in EventLog.objects.filter(event_type="harmonized").order_by("-id")
            if isinstance(e.event_data, dict) and e.event_data.get("job_id") == job_id
        ),
        None,
    )
    if ev is None:
        raise ValueError(f"Harmonization job '{job_id}' not found in EventLog.")

    data = ev.event_data
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
