"""Level 3 Conceptual & Controlled-Vocabulary Graph Discovery (`fairwddi.compare.conceptual`).

Performs read-only graph discovery over existing ``Concept`` anchors and SKOS/DDI
semantic relations (e.g. CESSDA ELSST / SKOS thesaurus hierarchies linked to
``ConceptualVariable`` or ``Category``). Defines a forward-compatible ``ConceptAssigner``
extension hook while raising ``NotImplementedError`` if ``auto_assign_concepts=True``
is requested without a registered automated indexer.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol

from fairwddi.compare.config import ResourceTypeComparisonRule
from fairwddi.compare.models import CorrespondenceLevel


class ConceptAssigner(Protocol):
    """Protocol for future automated thesaurus / LLM concept assignment plugins."""

    def assign_concepts(self, resources: Sequence[dict[str, Any]]) -> dict[str, list[str]]:
        """Return `{resource_urn: [concept_urn, ...]}` for unannotated resources."""
        ...


_CONCEPT_ASSIGNERS: dict[str, ConceptAssigner] = {}


def register_concept_assigner(name: str, assigner: ConceptAssigner) -> None:
    """Register a custom Level 3 `ConceptAssigner` implementation."""
    _CONCEPT_ASSIGNERS[name.strip().lower()] = assigner


def _load_concept_ancestors(
    concept_urns: set[str], max_hops: int
) -> dict[str, list[tuple[str, int]]]:
    """Return `{concept_urn: [(ancestor_urn, distance_hops), ...]}` up to `max_hops`."""
    from fairwddi.models import Concept

    if not concept_urns:
        return {}

    parent_by_urn: dict[str, str | None] = {}
    frontier = set(concept_urns)
    for _ in range(max_hops + 1):
        to_fetch = frontier - set(parent_by_urn.keys())
        if not to_fetch:
            break
        next_frontier: set[str] = set()
        for c_u, p_u in Concept.objects.filter(urn__in=to_fetch).values_list("urn", "parent_id"):
            parent_by_urn[c_u] = p_u
            if p_u:
                next_frontier.add(p_u)
        frontier = next_frontier

    result: dict[str, list[tuple[str, int]]] = {}
    for start_u in concept_urns:
        chain: list[tuple[str, int]] = [(start_u, 0)]
        curr = start_u
        seen = {start_u}
        for hop in range(1, max_hops + 1):
            par = parent_by_urn.get(curr)
            if not par or par in seen:
                break
            seen.add(par)
            chain.append((par, hop))
            curr = par
        result[start_u] = chain
    return result


def _direct_concepts_for_record(
    rec: dict[str, Any],
    vocabularies: set[str],
    allowed_concept_urns: set[str] | None,
) -> list[tuple[str, str]]:
    """Return `[(concept_urn, relation_kind), ...]` attached to a comparison record."""
    concepts: list[tuple[str, str]] = []
    if rec.get("concept_urn"):
        cu = str(rec["concept_urn"])
        if not allowed_concept_urns or cu in allowed_concept_urns:
            concepts.append((cu, "direct"))
    for link in rec.get("concept_links") or []:
        cu = str(link["concept_urn"])
        if not allowed_concept_urns or cu in allowed_concept_urns:
            concepts.append((cu, str(link["predicate"])))
    if rec.get("resource_type") == "Concept" and rec.get("urn"):
        cu = str(rec["urn"])
        if not vocabularies or not allowed_concept_urns or cu in allowed_concept_urns:
            concepts.append((cu, "self"))
    return concepts


def compare_conceptual_sets(
    source_records: list[dict[str, Any]],
    target_records: list[dict[str, Any]],
    resource_type: str,
    rule: ResourceTypeComparisonRule,
    *,
    exclude_same_urn: bool = True,
    symmetric_sets: bool = False,
) -> list[dict[str, Any]]:
    """Discover Level 3 correspondences sharing Concepts or SKOS/ELSST ancestors."""
    con_cfg = rule.conceptual
    if not con_cfg.enabled or not source_records or not target_records:
        return []

    if con_cfg.auto_assign_concepts:
        if not _CONCEPT_ASSIGNERS:
            raise NotImplementedError(
                "Automated Concept assignment (`auto_assign_concepts=True`) is a future "
                "capability scaffold in fairwddi.compare.conceptual and is not implemented. "
                "Disable `auto_assign_concepts` or register a custom ConceptAssigner."
            )
        assigner = next(iter(_CONCEPT_ASSIGNERS.values()))
        assigned_src = assigner.assign_concepts(source_records)
        assigned_tgt = assigner.assign_concepts(target_records)
        for rec in source_records:
            for cu in assigned_src.get(rec["urn"], []):
                rec.setdefault("concept_links", []).append(
                    {"predicate": "dcterms:subject", "concept_urn": cu}
                )
        for rec in target_records:
            for cu in assigned_tgt.get(rec["urn"], []):
                rec.setdefault("concept_links", []).append(
                    {"predicate": "dcterms:subject", "concept_urn": cu}
                )

    from fairwddi.models import Concept

    vocab_filter = {v.strip() for v in con_cfg.vocabularies if v.strip()}
    allowed_concepts: set[str] | None = None
    if vocab_filter:
        allowed_concepts = set(
            Concept.objects.filter(vocabulary__in=vocab_filter).values_list("urn", flat=True)
        )

    src_concepts: dict[str, list[tuple[str, str]]] = {}
    tgt_concepts: dict[str, list[tuple[str, str]]] = {}
    all_seed_concepts: set[str] = set()

    for r in source_records:
        c_list = _direct_concepts_for_record(r, vocab_filter, allowed_concepts)
        if c_list:
            src_concepts[r["urn"]] = c_list
            all_seed_concepts.update(cu for cu, _ in c_list)
    for r in target_records:
        c_list = _direct_concepts_for_record(r, vocab_filter, allowed_concepts)
        if c_list:
            tgt_concepts[r["urn"]] = c_list
            all_seed_concepts.update(cu for cu, _ in c_list)

    if not src_concepts or not tgt_concepts:
        return []

    hops = con_cfg.max_hierarchy_hops if con_cfg.allow_hierarchy_ancestors else 0
    ancestors = _load_concept_ancestors(all_seed_concepts, hops)

    # Index target records by ancestor concept URN for sub-quadratic lookup
    concept_to_targets: dict[str, list[tuple[dict[str, Any], int, str]]] = {}
    for tgt in target_records:
        t_list = tgt_concepts.get(tgt["urn"], [])
        for c_u, rel_kind in t_list:
            for anc_u, dist in ancestors.get(c_u, [(c_u, 0)]):
                concept_to_targets.setdefault(anc_u, []).append((tgt, dist, rel_kind))

    candidates: list[dict[str, Any]] = []
    seen_sym_pairs: set[tuple[str, str]] = set()
    best_by_pair: dict[tuple[str, str], dict[str, Any]] = {}

    for src in source_records:
        s_list = src_concepts.get(src["urn"], [])
        if not s_list:
            continue

        for s_cu, s_rel in s_list:
            for s_anc_u, s_dist in ancestors.get(s_cu, [(s_cu, 0)]):
                for tgt, t_dist, t_rel in concept_to_targets.get(s_anc_u, []):
                    if exclude_same_urn and src["urn"] == tgt["urn"]:
                        continue
                    if symmetric_sets:
                        sym_k = (min(src["urn"], tgt["urn"]), max(src["urn"], tgt["urn"]))
                        if sym_k in seen_sym_pairs:
                            continue

                    total_hops = s_dist + t_dist
                    if (
                        total_hops == 0
                        and s_rel in ("direct", "self", "skos:exactMatch")
                        and t_rel in ("direct", "self", "skos:exactMatch")
                    ):
                        conf = 1.0
                        m_type = "CONCEPT_EXACT"
                    elif total_hops == 0:
                        conf = 0.90
                        m_type = "CONCEPT_RELATION"
                    else:
                        conf = max(0.60, round(1.0 - 0.10 * total_hops, 4))
                        m_type = "CONCEPT_ANCESTOR"

                    if conf < con_cfg.threshold:
                        continue

                    pair_k = (src["urn"], tgt["urn"])
                    existing = best_by_pair.get(pair_k)
                    if existing is None or conf > existing["confidence"]:
                        best_by_pair[pair_k] = {
                            "level": CorrespondenceLevel.CONCEPTUAL,
                            "resource_type": resource_type,
                            "source_rec": src,
                            "target_rec": tgt,
                            "match_type": m_type,
                            "confidence": conf,
                            "requires_review": conf < 0.99 or total_hops > 0,
                            "details": {
                                "shared_concept_urn": s_anc_u,
                                "source_concept_urn": s_cu,
                                "target_concept_urn": tgt_concepts[tgt["urn"]][0][0],
                                "hierarchy_hops": total_hops,
                            },
                        }

    for cand in best_by_pair.values():
        if symmetric_sets:
            sym_k = (
                min(cand["source_rec"]["urn"], cand["target_rec"]["urn"]),
                max(cand["source_rec"]["urn"], cand["target_rec"]["urn"]),
            )
            if sym_k in seen_sym_pairs:
                continue
            seen_sym_pairs.add(sym_k)
        candidates.append(cand)

    return candidates
