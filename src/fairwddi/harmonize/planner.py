"""Comparison-driven Harmonization Planner (`fairwddi.harmonize.planner`).

Consumes a :class:`ComparisonResultSet` (or ``*.comparison.yaml/.json``) and applies
a :class:`HarmonizationPolicy` to emit a review-gated :class:`HarmonizationPlan`.
Supports ``--approve-high`` / ``approve_high=True`` using explicit thresholds and
allowlists defined in ``HarmonizationPolicy.auto_approve_high``.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fairwddi.compare.models import (
    CandidateCorrespondence,
    CodeListQualification,
    ComparisonResultSet,
    CorrespondenceLevel,
)
from fairwddi.harmonize.plan import (
    HarmonizationActionItem,
    HarmonizationPlan,
    HarmonizationPolicy,
    load_harmonization_policy,
)
from fairwddi.importer.plan import ReviewGate
from fairwddi.utils.urn import generate_generic_urn

_LEVEL_PRIORITY: dict[CorrespondenceLevel, int] = {
    CorrespondenceLevel.SYNTACTIC: 0,
    CorrespondenceLevel.SEMANTIC: 1,
    CorrespondenceLevel.CONCEPTUAL: 2,
}


def _select_seed_text(cand: CandidateCorrespondence) -> str | None:
    for d in (cand.target_text, cand.source_text):
        if isinstance(d, dict) and d:
            for lang in ("fr", "en"):
                if lang in d and d[lang].strip():
                    return d[lang].strip()
            val = next(iter(d.values()), "")
            if val.strip():
                return val.strip()
    return None


def _determine_action(
    cand: CandidateCorrespondence,
    policy: HarmonizationPolicy,
) -> tuple[str, str | None, dict[str, Any], str]:
    details = dict(cand.details)
    qual = cand.qualification.codelist_qualification
    guard = policy.guardrails

    if guard.group_shared_stem_grids and (
        cand.match_type in ("SHARED_STEM", "SHARED_STEM_GRID") or cand.recommended_action == "group"
    ):
        return (
            "group",
            None,
            details,
            f"Shared-stem question/category grid ({cand.confidence:.2f}) -> group",
        )

    if guard.downgrade_scale_cardinality_diff_to_semantic_link and (
        qual == CodeListQualification.SCALE_CARDINALITY_DIFF
    ):
        details["downgraded_reason"] = qual.value
        return (
            "link_semantic",
            None,
            details,
            f"Downgraded from merge to 'link_semantic' due to CodeList '{qual.value}'.",
        )

    if guard.downgrade_dimension_mismatch_to_semantic_link and (
        qual == CodeListQualification.DIMENSION_MISMATCH_SUSPECTED
    ):
        details["downgraded_reason"] = qual.value
        return (
            "link_semantic",
            None,
            details,
            f"Downgraded from merge to 'link_semantic' due to CodeList '{qual.value}'.",
        )

    if (
        guard.downgrade_uncoded_to_semantic_link
        and qual == CodeListQualification.UNCOMPARABLE_OR_UNCODED
    ):
        details["downgraded_reason"] = qual.value
        return (
            "link_semantic",
            None,
            details,
            f"Downgraded to 'link_semantic' due to CodeList '{qual.value}'.",
        )

    if cand.level == CorrespondenceLevel.SYNTACTIC:
        if cand.target_origin in ("generated", "instantiated"):
            return (
                "link_existing",
                None,
                details,
                (
                    f"Syntactic {cand.match_type} ({cand.confidence:.2f}) -> "
                    f"link to {cand.target_origin} target"
                ),
            )
        gen_urn = generate_generic_urn(
            resource_type=cand.resource_type,
            name_or_text=_select_seed_text(cand),
        )
        details.setdefault("generated_urn", gen_urn)
        return (
            "generate_harmonized",
            gen_urn,
            details,
            f"Syntactic {cand.match_type} ({cand.confidence:.2f}) -> generate_harmonized",
        )

    if cand.level == CorrespondenceLevel.SEMANTIC:
        return (
            "link_semantic",
            None,
            details,
            f"Semantic {cand.match_type} ({cand.confidence:.2f}) -> semantic link",
        )

    return (
        "link_semantic",
        None,
        details,
        f"Conceptual {cand.match_type} ({cand.confidence:.2f}) -> conceptual link",
    )


def plan_harmonization(
    comparison: ComparisonResultSet | Path | str,
    policy: str | Path | HarmonizationPolicy | None = None,
    *,
    approve_high: bool = False,
    high_threshold: float | None = None,
    keep_pending: bool = False,
    output_dir: str | Path | None = None,
) -> HarmonizationPlan:
    """Translate a comparison result set into a review-gated :class:`HarmonizationPlan`.

    Args:
        comparison: In-memory :class:`ComparisonResultSet` or path to `*.comparison.yaml/.json`.
        policy: :class:`HarmonizationPolicy`, preset name (`default`), or YAML file path.
        approve_high: When True (and `keep_pending` is False), immediately approve actions
            satisfying `policy.auto_approve_high` criteria.
        high_threshold: Optional override for `policy.auto_approve_high.min_confidence`.
        keep_pending: Explicitly suppress auto-approval so all actions remain pending review.
        output_dir: Optional directory to write `*.harmonize.plan.yaml` and `.report.md`.
    """
    comp_set = (
        comparison
        if isinstance(comparison, ComparisonResultSet)
        else ComparisonResultSet.load(comparison)
    )
    pol = policy if isinstance(policy, HarmonizationPolicy) else load_harmonization_policy(policy)

    # Deduplicate (resource_type, source_urn, target_urn) keeping highest priority / confidence
    best_by_pair: dict[tuple[str, str, str], CandidateCorrespondence] = {}
    for cand in comp_set.candidates:
        key = (cand.resource_type, cand.source_urn, cand.target_urn)
        prev = best_by_pair.get(key)
        if prev is None:
            best_by_pair[key] = cand
            continue
        c_prio = (_LEVEL_PRIORITY.get(cand.level, 9), -cand.confidence)
        p_prio = (_LEVEL_PRIORITY.get(prev.level, 9), -prev.confidence)
        if c_prio < p_prio:
            best_by_pair[key] = cand

    actions: list[HarmonizationActionItem] = []
    by_action_counts: dict[str, int] = {}
    effective_approve_high = bool(approve_high and not keep_pending)

    for idx, cand in enumerate(
        sorted(
            best_by_pair.values(),
            key=lambda c: (_LEVEL_PRIORITY.get(c.level, 9), -c.confidence, c.id),
        ),
        start=1,
    ):
        act_type, gen_urn, details, note = _determine_action(cand, pol)
        details.setdefault("correspondence_level", cand.level.value)
        details.setdefault(
            "codelist_qualification", cand.qualification.codelist_qualification.value
        )
        if cand.source_text:
            details.setdefault("source_text", cand.source_text)
        if cand.target_text:
            details.setdefault("target_text", cand.target_text)
        if cand.qualification.administration_context_caveat:
            details.setdefault(
                "administration_context_caveat",
                cand.qualification.administration_context_caveat,
            )

        draft = HarmonizationActionItem(
            id=f"harm-{idx:04d}",
            candidate_id=cand.id,
            action=act_type,  # type: ignore[arg-type]
            resource_type=cand.resource_type,
            source_urn=cand.source_urn,
            target_urn=cand.target_urn,
            generated_urn=gen_urn,
            level=cand.level,
            match_type=cand.match_type,
            confidence=cand.confidence,
            codelist_qualification=cand.qualification.codelist_qualification,
            details=details,
            notes=note,
        )
        is_high = pol.qualifies_as_high(draft, high_threshold_override=high_threshold)
        draft.approval_tier = "high" if is_high else "review_required"

        if effective_approve_high and is_high:
            draft.approved = True
            draft.requires_review = False
        elif not is_high and pol.auto_approve_high.non_high_behavior == "skip":
            draft.action = "skip"
            draft.approved = False
            draft.requires_review = False
        else:
            draft.approved = False
            draft.requires_review = True

        by_action_counts[draft.action] = by_action_counts.get(draft.action, 0) + 1
        actions.append(draft)

    job_id = f"harmonize-{uuid.uuid4().hex[:8]}"
    high_count = sum(1 for a in actions if a.approval_tier == "high")
    approved_now = sum(1 for a in actions if a.approved and a.action != "skip")

    gate = ReviewGate(approved=False)
    if effective_approve_high and approved_now > 0:
        gate.approved = True
        gate.reviewer = f"policy:{pol.name}:auto_approve_high"
        gate.reviewed_at = datetime.now(UTC).isoformat()
        gate.comments = (
            f"Auto-approved {approved_now} high-confidence action(s) per policy "
            f"(non-high kept pending)."
        )

    plan = HarmonizationPlan(
        job_id=job_id,
        comparison_job_id=comp_set.job_id,
        source_spec=comp_set.source_spec,
        target_spec=comp_set.target_spec,
        policy_name=pol.name,
        approve_high_applied=effective_approve_high,
        review_gate=gate,
        summary={
            "comparison_candidates": len(comp_set.candidates),
            "deduplicated_actions": len(actions),
            "high_confidence_matches": high_count,
            "auto_approve_high_applied": effective_approve_high,
            "by_action": by_action_counts,
        },
        actions=actions,
    )

    if output_dir is not None:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        plan.to_yaml(out_dir / f"{job_id}.harmonize.plan.yaml")
        plan.to_markdown(out_dir / f"{job_id}.harmonize.report.md")

    return plan


def approve_high_actions(
    plan_or_path: HarmonizationPlan | Path | str,
    *,
    policy: str | Path | HarmonizationPolicy | None = None,
    high_threshold: float | None = None,
    output_path: Path | str | None = None,
) -> HarmonizationPlan:
    """Retroactively mark eligible high-confidence actions as approved on an existing plan."""
    plan = (
        plan_or_path
        if isinstance(plan_or_path, HarmonizationPlan)
        else HarmonizationPlan.from_yaml(plan_or_path)
    )
    pol = (
        policy
        if isinstance(policy, HarmonizationPolicy)
        else load_harmonization_policy(policy or plan.policy_name)
    )

    updated: list[HarmonizationActionItem] = []
    for act in plan.actions:
        if act.action == "skip":
            updated.append(act)
            continue
        is_high = pol.qualifies_as_high(act, high_threshold_override=high_threshold)
        act_copy = act.model_copy(
            update={
                "approval_tier": "high" if is_high else "review_required",
                "approved": True if is_high else act.approved,
                "requires_review": False if is_high else act.requires_review,
            }
        )
        updated.append(act_copy)

    new_plan = plan.model_copy(
        update={
            "actions": updated,
            "approve_high_applied": True,
            "summary": {
                **plan.summary,
                "auto_approve_high_applied": True,
                "high_confidence_matches": sum(1 for a in updated if a.approval_tier == "high"),
            },
        }
    )
    if new_plan.approved_count > 0:
        new_plan.review_gate.approved = True
        new_plan.review_gate.reviewer = f"policy:{pol.name}:auto_approve_high"
        new_plan.review_gate.reviewed_at = datetime.now(UTC).isoformat()

    target_write = (
        Path(output_path)
        if output_path is not None
        else (
            Path(plan_or_path)
            if isinstance(plan_or_path, (Path, str)) and Path(plan_or_path).exists()
            else None
        )
    )
    if target_write is not None:
        new_plan.to_yaml(target_write)

    return new_plan
