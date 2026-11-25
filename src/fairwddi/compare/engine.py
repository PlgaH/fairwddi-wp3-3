"""Two-set, three-layer read-only comparison orchestrator (`fairwddi.compare.engine`)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal

from dartfx.ddi.harmonizer import MatchType

from fairwddi.compare.conceptual import compare_conceptual_sets
from fairwddi.compare.config import ComparisonConfig, load_comparison_config
from fairwddi.compare.models import (
    CandidateCorrespondence,
    CodeListQualification,
    ComparisonResultSet,
    CorrespondenceLevel,
)
from fairwddi.compare.qualifier import evaluate_qualification
from fairwddi.compare.records import load_records_for_urns
from fairwddi.compare.semantic import compare_semantic_sets
from fairwddi.compare.syntactic import compare_syntactic_sets
from fairwddi.groups.resolver import resolve_resource_set


def _normalize_levels(
    levels: Sequence[CorrespondenceLevel | str] | None,
    config: ComparisonConfig,
) -> list[CorrespondenceLevel]:
    if not levels:
        return list(config.levels)
    expanded: list[CorrespondenceLevel] = []
    seen: set[CorrespondenceLevel] = set()
    for raw in levels:
        token = str(raw).strip().lower()
        if token == "all":
            items = [
                CorrespondenceLevel.SYNTACTIC,
                CorrespondenceLevel.SEMANTIC,
                CorrespondenceLevel.CONCEPTUAL,
            ]
        else:
            items = [CorrespondenceLevel(token)]
        for lvl in items:
            if lvl not in seen:
                seen.add(lvl)
                expanded.append(lvl)
    return expanded


def _normalize_types(
    resource_types: Sequence[str] | None,
    config: ComparisonConfig,
) -> list[str]:
    if not resource_types:
        return list(config.resource_types)
    out: list[str] = []
    seen: set[str] = set()
    for item in resource_types:
        for tok in str(item).split(","):
            t = tok.strip()
            if t and t not in seen:
                seen.add(t)
                out.append(t)
    return out


def _determine_recommended_action(
    level: CorrespondenceLevel,
    match_type: str,
    src_origin: str,
    tgt_origin: str,
    qual_code: CodeListQualification,
) -> tuple[
    Literal["link_existing", "generate_harmonized", "link_semantic", "group", "review"], bool
]:
    if match_type in (MatchType.SHARED_STEM.value, "SHARED_STEM", "SHARED_STEM_GRID"):
        return "group", True

    if qual_code in (
        CodeListQualification.SCALE_CARDINALITY_DIFF,
        CodeListQualification.DIMENSION_MISMATCH_SUSPECTED,
        CodeListQualification.UNCOMPARABLE_OR_UNCODED,
    ):
        return "link_semantic", True

    if level == CorrespondenceLevel.CONCEPTUAL:
        return "link_semantic", True

    if level == CorrespondenceLevel.SEMANTIC:
        # Semantic vector candidates always require human review before merge or semantic linking
        if tgt_origin in ("generated", "instantiated") and qual_code in (
            CodeListQualification.IDENTICAL,
            CodeListQualification.MISSING_VALUES_ONLY,
            CodeListQualification.NOT_APPLICABLE,
        ):
            return "link_existing", True
        return "link_semantic", True

    # Syntactic Level 1 with compatible CodeList
    exact_types = {MatchType.EXACT_IDENTICAL.value, MatchType.NORMALIZED_EXACT.value}
    if tgt_origin in ("generated", "instantiated") and src_origin == "imported":
        return "link_existing", (match_type not in exact_types)
    if src_origin == "imported" and tgt_origin == "imported":
        return "generate_harmonized", (match_type not in exact_types)
    return "review", True


def run_comparison(
    source: str,
    target: str,
    *,
    config: str | Path | ComparisonConfig | None = None,
    levels: Sequence[CorrespondenceLevel | str] | None = None,
    resource_types: Sequence[str] | None = None,
    output_dir: str | Path | None = None,
    output_format: Literal["yaml", "json"] = "yaml",
) -> ComparisonResultSet:
    """Compare two resolved DDI resource sets across configured comparison levels (read-only).

    Creates ZERO database writes. Returns a serialized :class:`ComparisonResultSet`
    ready for human inspection or downstream ``harmonize plan``.
    """
    cfg = config if isinstance(config, ComparisonConfig) else load_comparison_config(config)
    eff_levels = _normalize_levels(levels, cfg)
    eff_types = _normalize_types(resource_types, cfg)

    src_set = resolve_resource_set(source, resource_types=eff_types)
    tgt_set = resolve_resource_set(target, resource_types=eff_types)
    symmetric_sets = source.strip() == target.strip()

    all_candidates: list[CandidateCorrespondence] = []
    counts_by_level: dict[str, int] = {lvl.value: 0 for lvl in eff_levels}
    counts_by_type: dict[str, int] = {}
    counts_by_qual: dict[str, int] = {}

    cand_seq = 0
    for r_type in eff_types:
        rule = cfg.rule_for(r_type)
        if not rule.enabled:
            continue

        src_urns = src_set.urns_for(r_type)
        tgt_urns = tgt_set.urns_for(r_type)
        if not src_urns or not tgt_urns:
            continue

        src_records = load_records_for_urns(r_type, src_urns, fields=rule.fields)
        tgt_records = load_records_for_urns(r_type, tgt_urns, fields=rule.fields)
        if not src_records or not tgt_records:
            continue

        raw_hits: list[dict[str, Any]] = []
        if CorrespondenceLevel.SYNTACTIC in eff_levels:
            syn_rule = rule.model_copy(
                update={"syntactic": rule.syntactic.model_copy(update={"enabled": True})}
            )
            raw_hits.extend(
                compare_syntactic_sets(
                    src_records,
                    tgt_records,
                    r_type,
                    syn_rule,
                    exclude_same_urn=cfg.exclude_same_urn,
                    symmetric_sets=symmetric_sets,
                )
            )
        if CorrespondenceLevel.SEMANTIC in eff_levels:
            sem_rule = rule.model_copy(
                update={"semantic": rule.semantic.model_copy(update={"enabled": True})}
            )
            raw_hits.extend(
                compare_semantic_sets(
                    src_records,
                    tgt_records,
                    r_type,
                    sem_rule,
                    exclude_same_urn=cfg.exclude_same_urn,
                    symmetric_sets=symmetric_sets,
                )
            )
        if CorrespondenceLevel.CONCEPTUAL in eff_levels:
            con_rule = rule.model_copy(
                update={"conceptual": rule.conceptual.model_copy(update={"enabled": True})}
            )
            raw_hits.extend(
                compare_conceptual_sets(
                    src_records,
                    tgt_records,
                    r_type,
                    con_rule,
                    exclude_same_urn=cfg.exclude_same_urn,
                    symmetric_sets=symmetric_sets,
                )
            )

        # Deduplicate per (source_urn, target_urn, level), keeping highest confidence
        deduped: dict[tuple[str, str, CorrespondenceLevel], dict[str, Any]] = {}
        for hit in raw_hits:
            s_u = hit["source_rec"]["urn"]
            t_u = hit["target_rec"]["urn"]
            lvl = hit["level"]
            key = (s_u, t_u, lvl)
            prev = deduped.get(key)
            if prev is None or hit["confidence"] > prev["confidence"]:
                deduped[key] = hit

        # Sort per source and cap at max_candidates_per_source (across all levels)
        by_source: dict[str, list[dict[str, Any]]] = {}
        for hit in deduped.values():
            by_source.setdefault(hit["source_rec"]["urn"], []).append(hit)

        level_priority = {
            CorrespondenceLevel.SYNTACTIC: 0,
            CorrespondenceLevel.SEMANTIC: 1,
            CorrespondenceLevel.CONCEPTUAL: 2,
        }
        for s_u in sorted(by_source.keys()):
            hits_for_src = sorted(
                by_source[s_u],
                key=lambda h: (
                    -h["confidence"],
                    level_priority.get(h["level"], 9),
                    h["target_rec"]["urn"],
                ),
            )[: cfg.max_candidates_per_source]

            for hit in hits_for_src:
                src_rec = hit["source_rec"]
                tgt_rec = hit["target_rec"]
                qual = evaluate_qualification(src_rec, tgt_rec, r_type, rule.qualification)
                rec_act, req_rev = _determine_recommended_action(
                    hit["level"],
                    hit["match_type"],
                    src_rec["origin"],
                    tgt_rec["origin"],
                    qual.codelist_qualification,
                )
                req_rev = bool(
                    hit.get("requires_review", True) or req_rev or not qual.compatible_for_merge
                )
                cand_seq += 1
                cand = CandidateCorrespondence(
                    id=f"cmp-{cand_seq:04d}",
                    level=hit["level"],
                    resource_type=r_type,
                    source_urn=src_rec["urn"],
                    target_urn=tgt_rec["urn"],
                    source_origin=src_rec["origin"],
                    target_origin=tgt_rec["origin"],
                    match_type=hit["match_type"],
                    confidence=hit["confidence"],
                    recommended_action=rec_act,
                    requires_review=req_rev,
                    source_text=dict(src_rec.get("raw_ml") or src_rec.get("ml_text") or {}),
                    target_text=dict(tgt_rec.get("raw_ml") or tgt_rec.get("ml_text") or {}),
                    qualification=qual,
                    details=hit.get("details", {}),
                )
                all_candidates.append(cand)
                counts_by_level[cand.level.value] = counts_by_level.get(cand.level.value, 0) + 1
                counts_by_type[r_type] = counts_by_type.get(r_type, 0) + 1
                q_val = qual.codelist_qualification.value
                counts_by_qual[q_val] = counts_by_qual.get(q_val, 0) + 1

    job_id = f"compare-{uuid.uuid4().hex[:8]}"
    result = ComparisonResultSet(
        job_id=job_id,
        source_spec=source,
        target_spec=target,
        config_name=cfg.name,
        levels=eff_levels,
        resource_types=eff_types,
        summary={
            "source_total_resources": src_set.total_count,
            "target_total_resources": tgt_set.total_count,
            "candidate_count": len(all_candidates),
            "by_level": counts_by_level,
            "by_type": counts_by_type,
            "by_qualification": counts_by_qual,
        },
        candidates=all_candidates,
    )

    if output_dir is not None:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        if output_format == "json":
            result.to_json(out_dir / f"{job_id}.comparison.json")
        else:
            result.to_yaml(out_dir / f"{job_id}.comparison.yaml")
        result.to_markdown(out_dir / f"{job_id}.comparison.report.md")

    return result
