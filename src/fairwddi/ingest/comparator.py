"""Stage 3a (Comparison & Discovery): Cross-survey candidate discovery and similarity comparison.

Evaluates ReQuest resources (Category, CodeList, QuestionItem, RepresentedVariable) across tiers
delegating string algorithms, stem detection, and variant classification to dartfx.ddi.harmonizer:
1. EXACT (1.00): Identical content hash.
2. FACET_EXACT (0.95): Identical normalized label or question_text hash across present languages.
3. MULTILINGUAL_OVERLAP (0.92): Exact match in at least one shared language with complementary
   translations, or complementary language labels on matching code structures.
4. NEAR_EXACT (0.96 - 0.98): Identical after loose punctuation normalization or >= 0.98 similarity.
5. INCLUSIVE_WRITING_VARIANT (0.98): Identical after stripping inclusive gender/plural markers.
6. TYPOGRAPHICAL_VARIANT (0.95): Single-word typographical or grammatical error variant.
7. PHRASING_VARIANT (0.92 - 0.94): Stylistic or pronominal phrasing variation.
8. SHARED_STEM / SHARED_STEM_GRID (0.88): Shared prompt or stem with distinct sub-items.
9. SAME_CONCEPT_DIVERGENT_DOMAIN / SAME_CONCEPT_DIFFERENT_SCALE (0.88): Equivalent concept/label
   with divergent CodeLists. Action downgraded to link_semantic.
10. SUBSTANTIVE_PERMUTATION (0.88): CodeLists sharing identical substantive categories.
11. CATEGORIES_EXACT_CODES_DIFFERENT (0.85): CodeLists with identical categories, different codes.
12. SYNTACTIC_SIMILAR (0.75 - 0.91): General normalized string similarity on label/question_text.
"""

from __future__ import annotations

import difflib
import uuid
from pathlib import Path
from typing import Any

from dartfx.ddi.harmonizer import (
    MatchType,
    TextNormalizer,
    TextVariantComparator,
    compare_multilingual_texts,
    detect_shared_stem,
)

from fairwddi.ingest.plan import IngestPlan, PlanActionItem, ReviewGate

_normalizer = TextNormalizer()


def _raw_lang_dict(d: Any) -> dict[str, str]:
    """Extract language-keyed dictionary preserving original casing (with whitespace normalized)."""
    return TextNormalizer.extract_multilingual_dict(d, lowercase=False)


def _norm_lang_dict(d: Any) -> dict[str, str]:
    return TextNormalizer.extract_multilingual_dict(d, lowercase=True)


def _normalize_text_loose(text: str) -> str:
    """Strip trailing/leading punctuation, quotes, and French punctuation spacing."""
    return _normalizer.normalize_loose(text, lang="fr")


def _strip_inclusive_markers(text: str) -> str:
    """Remove parenthetical or midpoint French inclusive gender/plural markers."""
    return _normalizer.strip_inclusive_markers(text, lang="fr")


def _has_inclusive_markers(text: str) -> bool:
    return _normalizer.has_inclusive_markers(text, lang="fr")


def _text_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return round(difflib.SequenceMatcher(None, a, b).ratio(), 4)


def _detect_shared_stem(
    raw_a: str,
    raw_b: str,
    min_stem_len: int = 20,
) -> dict[str, Any] | None:
    """Detect if two strings share a common question/category stem and distinct sub-items."""
    res = detect_shared_stem(
        raw_a,
        raw_b,
        min_stem_len=min_stem_len,
        context="question_grid",
        lang="fr",
    )
    return res.model_dump() if res is not None else None


def _detect_wording_or_typo_variant(
    raw_a: str,
    raw_b: str,
    lang: str,
    best_sim: float,
) -> tuple[str, float, dict[str, Any]] | None:
    """Classify stylistic/pronominal phrasing variants vs grammatical/typographical errors."""
    cmp = TextVariantComparator(normalizer=_normalizer, language=lang)
    res = cmp.compare(raw_a, raw_b)
    if res is not None:
        meta = dict(res.metadata)
        if "canonical_text" in meta and isinstance(meta["canonical_text"], str):
            meta["canonical_text"] = {lang: meta["canonical_text"]}
        return res.match_type.value, res.score, meta
    return None


def _compare_multilingual_texts(
    ml_a: dict[str, str] | list[Any] | None,
    ml_b: dict[str, str] | list[Any] | None,
    threshold: float = 0.75,
) -> tuple[str | None, float, dict[str, Any]]:
    """Compare two multilingual text dictionaries and return (match_type, confidence, details)."""
    res = compare_multilingual_texts(ml_a, ml_b, threshold=threshold, normalizer=_normalizer)
    if res.match_type == MatchType.DISTINCT or res.score < threshold:
        return None, 0.0, {}
    return res.match_type.value, res.score, dict(res.metadata)


def _is_record_elevated(urn: str, ext_attrs: Any, elevated_urns: set[str]) -> bool:
    if urn in elevated_urns:
        return True
    if isinstance(ext_attrs, list):
        for item in ext_attrs:
            if isinstance(item, dict) and (
                item.get("is_elevated") is True or item.get("type") == "elevation"
            ):
                return True
    return False


def _load_resource_records(
    resource_type: str,
    query: str | None = None,
) -> list[dict[str, Any]]:
    """Load lightweight comparison records from the ReQuest database for a given resource type."""
    from fairwddi.models import (
        Category,
        CodeItem,
        CodeList,
        QuestionItem,
        QuestionVariable,
        RepresentedVariable,
        UrnRegistry,
    )

    elevated_urns = set(UrnRegistry.objects.filter(status="elevated").values_list("urn", flat=True))
    records: list[dict[str, Any]] = []
    q_low = query.lower() if query else None

    if resource_type == "Category":
        for cat in Category.objects.all().order_by("urn"):
            text_map = cat.label or {}
            if (
                q_low
                and q_low not in cat.urn.lower()
                and not any(q_low in str(v).lower() for v in text_map.values())
            ):
                continue
            records.append(
                {
                    "urn": cat.urn,
                    "resource_type": "Category",
                    "name": cat.name,
                    "text": text_map,
                    "content_hash": (cat.hashes or {}).get("content"),
                    "is_elevated": _is_record_elevated(
                        cat.urn, cat.extended_attributes, elevated_urns
                    ),
                }
            )

    elif resource_type == "QuestionItem":
        for qi in QuestionItem.objects.all().order_by("urn"):
            text_map = qi.question_text or qi.label or {}
            text_dict = _raw_lang_dict(text_map)
            if (
                q_low
                and q_low not in qi.urn.lower()
                and not any(q_low in str(v).lower() for v in text_dict.values())
            ):
                continue
            records.append(
                {
                    "urn": qi.urn,
                    "resource_type": "QuestionItem",
                    "name": qi.name,
                    "text": text_map,
                    "content_hash": (qi.hashes or {}).get("content"),
                    "is_elevated": _is_record_elevated(
                        qi.urn, qi.extended_attributes, elevated_urns
                    ),
                }
            )

    elif resource_type == "CodeList":
        for cl in CodeList.objects.all().order_by("urn"):
            items = list(
                CodeItem.objects.filter(code_list=cl)
                .select_related("category")
                .order_by("order", "code_value")
            )
            code_pairs: list[tuple[str, str, bool]] = []
            for ci in items:
                cat_lbl_dict = _norm_lang_dict(ci.category.label) if ci.category else {}
                cat_lbl = next(iter(cat_lbl_dict.values()), ci.category.urn if ci.category else "")
                code_pairs.append((str(ci.value).strip(), cat_lbl, bool(ci.is_missing)))
            if q_low and q_low not in cl.urn.lower() and q_low not in str(cl.name).lower():
                if not any(q_low in lbl for _, lbl, _ in code_pairs):
                    continue
            records.append(
                {
                    "urn": cl.urn,
                    "resource_type": "CodeList",
                    "name": cl.name,
                    "text": cl.label or {},
                    "codes": code_pairs,
                    "content_hash": (cl.hashes or {}).get("content"),
                    "is_elevated": _is_record_elevated(
                        cl.urn, cl.extended_attributes, elevated_urns
                    ),
                }
            )

    elif resource_type == "RepresentedVariable":
        for rv in RepresentedVariable.objects.select_related(
            "code_list", "conceptual_variable"
        ).order_by("urn"):
            q_urns = list(
                QuestionVariable.objects.filter(represented_variable=rv)
                .order_by("order")
                .values_list("question_item_id", flat=True)
            )
            text_map = rv.label or {}
            text_dict = _raw_lang_dict(text_map)
            if (
                q_low
                and q_low not in rv.urn.lower()
                and not any(q_low in str(v).lower() for v in text_dict.values())
            ):
                continue
            cl_hash = None
            if rv.code_list:
                cl_hashes = rv.code_list.hashes or {}
                cl_hash = cl_hashes.get("codes") or cl_hashes.get("content")
            records.append(
                {
                    "urn": rv.urn,
                    "resource_type": "RepresentedVariable",
                    "name": rv.name,
                    "text": text_map,
                    "codelist_urn": rv.code_list_id,
                    "codelist_hash": cl_hash,
                    "question_urns": q_urns,
                    "content_hash": (rv.hashes or {}).get("content"),
                    "is_elevated": _is_record_elevated(
                        rv.urn, rv.extended_attributes, elevated_urns
                    ),
                }
            )

    return records


def _get_codelist_code_pairs(
    cl_urn: str, cache: dict[str, list[tuple[str, str]]]
) -> list[tuple[str, str]]:
    """Retrieve normalized (code_value, category_label) pairs for a CodeList URN."""
    if cl_urn in cache:
        return cache[cl_urn]
    from fairwddi.models import CodeItem

    items = list(
        CodeItem.objects.filter(code_list_id=cl_urn)
        .select_related("category")
        .order_by("order", "code_value")
    )
    pairs: list[tuple[str, str]] = []
    for ci in items:
        lbl = ""
        if ci.category:
            lbl_dict = _raw_lang_dict(ci.category.label)
            lbl = next(iter(lbl_dict.values()), ci.category.urn if ci.category else "")
        pairs.append((str(ci.code_value).strip(), str(lbl).strip().lower()))
    cache[cl_urn] = pairs
    return pairs


def _check_codelist_compatibility(
    cl_a: str | None,
    cl_b: str | None,
    cl_hash_a: str | None = None,
    cl_hash_b: str | None = None,
    alias_map: dict[str, str] | None = None,
    codes_cache: dict[str, list[tuple[str, str]]] | None = None,
) -> tuple[bool, str]:
    """Check if two CodeLists are identical, aliased, content-equivalent, or divergent."""
    if not cl_a and not cl_b:
        return True, "both_uncoded"
    if bool(cl_a) != bool(cl_b):
        return False, "coded_vs_uncoded"
    if cl_a == cl_b:
        return True, "identical_urn"

    # Aliased through URNAlias
    def _res(u: str) -> str:
        curr = u
        visited = set()
        while curr not in visited:
            visited.add(curr)
            if alias_map is not None:
                if curr not in alias_map:
                    break
                curr = alias_map[curr]
            else:
                from fairwddi.models import URNAlias

                al = URNAlias.objects.filter(alias_urn=curr).first()
                if not al:
                    break
                curr = al.canonical_urn
        return curr

    canon_a = _res(cl_a)  # type: ignore[arg-type]
    canon_b = _res(cl_b)  # type: ignore[arg-type]
    if canon_a and canon_b and canon_a == canon_b:
        return True, "aliased"

    if cl_hash_a and cl_hash_b and cl_hash_a == cl_hash_b:
        return True, "identical_codes_hash"

    cache = codes_cache if codes_cache is not None else {}
    if cl_a and cl_b:
        pairs_a = _get_codelist_code_pairs(cl_a, cache)
        pairs_b = _get_codelist_code_pairs(cl_b, cache)
        if pairs_a and pairs_b and pairs_a == pairs_b:
            return True, "identical_code_items"

    return False, "divergent"


def _compare_pair(
    rec_a: dict[str, Any],
    rec_b: dict[str, Any],
    threshold: float = 0.75,
    alias_map: dict[str, str] | None = None,
    codes_cache: dict[str, list[tuple[str, str]]] | None = None,
) -> dict[str, Any] | None:
    """Compare two resource records of the same type and return a candidate dict if >= threshold."""
    r_type = rec_a["resource_type"]
    urn_a = rec_a["urn"]
    urn_b = rec_b["urn"]
    if urn_a == urn_b:
        return None

    is_tgt_elevated = bool(rec_b.get("is_elevated"))

    # For RepresentedVariable, assess CodeList compatibility upfront
    cl_compat = True
    cl_status = "not_applicable"
    if r_type == "RepresentedVariable":
        cl_a = rec_a.get("codelist_urn")
        cl_b = rec_b.get("codelist_urn")
        cl_compat, cl_status = _check_codelist_compatibility(
            cl_a,
            cl_b,
            cl_hash_a=rec_a.get("codelist_hash"),
            cl_hash_b=rec_b.get("codelist_hash"),
            alias_map=alias_map,
            codes_cache=codes_cache,
        )

    # 1. Exact content hash match
    if rec_a.get("content_hash") and rec_a.get("content_hash") == rec_b.get("content_hash"):
        if r_type == "RepresentedVariable" and not cl_compat:
            return {
                "resource_type": r_type,
                "source_urn": urn_a,
                "target_urn": urn_b,
                "match_type": MatchType.SAME_CONCEPT_DIVERGENT_DOMAIN.value,
                "confidence": 0.88,
                "recommended_action": "link_semantic",
                "requires_review": True,
                "details": {
                    "source_name": rec_a["name"],
                    "target_name": rec_b["name"],
                    "target_is_elevated": is_tgt_elevated,
                    "codelist_status": cl_status,
                    "source_codelist_urn": rec_a.get("codelist_urn"),
                    "target_codelist_urn": rec_b.get("codelist_urn"),
                    "note": (
                        "RepresentedVariables share content hash but use divergent response "
                        "scales (CodeLists). Action downgraded to link_semantic."
                    ),
                },
            }
        details: dict[str, Any] = {
            "source_name": rec_a["name"],
            "target_name": rec_b["name"],
            "target_is_elevated": is_tgt_elevated,
        }
        if r_type == "RepresentedVariable":
            details["codelist_status"] = cl_status
            details["codelist_urn"] = rec_a.get("codelist_urn") or rec_b.get("codelist_urn")
        return {
            "resource_type": r_type,
            "source_urn": urn_a,
            "target_urn": urn_b,
            "match_type": MatchType.EXACT.value,
            "confidence": 1.0,
            "recommended_action": "absorb" if is_tgt_elevated else "alias",
            "requires_review": False,
            "details": details,
        }

    # 2. CodeList structural comparison
    if r_type == "CodeList":
        codes_a: list[tuple[str, str, bool]] = rec_a.get("codes", [])
        codes_b: list[tuple[str, str, bool]] = rec_b.get("codes", [])
        if codes_a and codes_b:
            pairs_a = [(v, lbl) for v, lbl, _ in codes_a]
            pairs_b = [(v, lbl) for v, lbl, _ in codes_b]
            if pairs_a == pairs_b:
                return {
                    "resource_type": "CodeList",
                    "source_urn": urn_a,
                    "target_urn": urn_b,
                    "match_type": MatchType.FACET_EXACT.value,
                    "confidence": 0.95,
                    "recommended_action": "absorb" if is_tgt_elevated else "alias",
                    "requires_review": False,
                    "details": {
                        "source_name": rec_a.get("name"),
                        "target_name": rec_b.get("name"),
                        "code_count": len(pairs_a),
                        "codes": [f"{v}: {lbl}" for v, lbl in pairs_a[:5]],
                        "target_is_elevated": is_tgt_elevated,
                    },
                }

            subst_a = {(v, lbl) for v, lbl, miss in codes_a if not miss and lbl}
            subst_b = {(v, lbl) for v, lbl, miss in codes_b if not miss and lbl}
            if subst_a and subst_a == subst_b:
                return {
                    "resource_type": "CodeList",
                    "source_urn": urn_a,
                    "target_urn": urn_b,
                    "match_type": MatchType.SUBSTANTIVE_PERMUTATION.value,
                    "confidence": 0.88,
                    "recommended_action": "link_semantic",
                    "requires_review": True,
                    "details": {
                        "source_name": rec_a.get("name"),
                        "target_name": rec_b.get("name"),
                        "substantive_codes": len(subst_a),
                        "codes": [f"{v}: {lbl}" for v, lbl in sorted(subst_a)[:5]],
                    },
                }

            cats_a = {lbl for _, lbl, miss in codes_a if not miss and lbl}
            cats_b = {lbl for _, lbl, miss in codes_b if not miss and lbl}
            if cats_a and cats_a == cats_b:
                return {
                    "resource_type": "CodeList",
                    "source_urn": urn_a,
                    "target_urn": urn_b,
                    "match_type": MatchType.CATEGORIES_EXACT_CODES_DIFFERENT.value,
                    "confidence": 0.85,
                    "recommended_action": "link_semantic",
                    "requires_review": True,
                    "details": {
                        "source_name": rec_a.get("name"),
                        "target_name": rec_b.get("name"),
                        "shared_categories": sorted(cats_a),
                    },
                }

            # Check if code values are identical with complementary languages in labels
            vals_a = [v for v, _, _ in codes_a]
            vals_b = [v for v, _, _ in codes_b]
            text_a = rec_a.get("text")
            text_b = rec_b.get("text")
            langs_a = set(_raw_lang_dict(text_a).keys())
            langs_b = set(_raw_lang_dict(text_b).keys())
            if vals_a == vals_b and langs_a and langs_b and langs_a != langs_b:
                return {
                    "resource_type": "CodeList",
                    "source_urn": urn_a,
                    "target_urn": urn_b,
                    "match_type": MatchType.MULTILINGUAL_OVERLAP.value,
                    "confidence": 0.90,
                    "recommended_action": "absorb" if is_tgt_elevated else "merge_multilingual",
                    "requires_review": True,
                    "details": {
                        "code_values": vals_a,
                        "source_languages": sorted(langs_a),
                        "target_languages": sorted(langs_b),
                        "target_is_elevated": is_tgt_elevated,
                    },
                }

        # CodeList identity is strictly structural; do not fall through to text/label comparison
        return None

    # 3. Text/Label comparison (Category, QuestionItem, RepresentedVariable)
    m_type, conf, details = _compare_multilingual_texts(rec_a.get("text"), rec_b.get("text"))
    if m_type and conf >= threshold:
        if m_type in (MatchType.SHARED_STEM.value, "SHARED_STEM", "SHARED_STEM_GRID"):
            if r_type not in ("QuestionItem", "RepresentedVariable"):
                # Categories do not form question grids; fall back to syntactic similarity
                m_type = MatchType.SYNTACTIC_SIMILAR.value
                rec_action = "link_semantic"
                req_rev = True
            else:
                rec_action = "group"
                req_rev = True
                if r_type == "RepresentedVariable":
                    details["codelist_status"] = cl_status
                    details["source_codelist_urn"] = rec_a.get("codelist_urn")
                    details["target_codelist_urn"] = rec_b.get("codelist_urn")
        elif r_type == "RepresentedVariable" and not cl_compat:
            m_type = MatchType.SAME_CONCEPT_DIVERGENT_DOMAIN.value
            rec_action = "link_semantic"
            req_rev = True
            conf = round(min(conf, 0.88), 4)
            details["codelist_status"] = cl_status
            details["source_codelist_urn"] = rec_a.get("codelist_urn")
            details["target_codelist_urn"] = rec_b.get("codelist_urn")
            details["note"] = (
                "RepresentedVariables share label semantics but use divergent response scales "
                "(CodeLists). Action downgraded to link_semantic to preserve value domain "
                "integrity."
            )
        elif m_type == MatchType.MULTILINGUAL_OVERLAP.value:
            rec_action = "absorb" if is_tgt_elevated else "merge_multilingual"
            req_rev = False
        elif m_type in (
            MatchType.FACET_EXACT.value,
            MatchType.EXACT_IDENTICAL.value,
            MatchType.NORMALIZED_EXACT.value,
        ):
            rec_action = "absorb" if is_tgt_elevated else "alias"
            req_rev = False
        elif m_type == MatchType.NEAR_EXACT.value:
            rec_action = "absorb" if is_tgt_elevated else "alias"
            req_rev = True
        elif m_type in (
            MatchType.INCLUSIVE_WRITING_VARIANT.value,
            MatchType.PHRASING_VARIANT.value,
            MatchType.TYPOGRAPHICAL_VARIANT.value,
        ):
            rec_action = "absorb" if is_tgt_elevated else "elevate"
            req_rev = True
        else:
            rec_action = "link_semantic"
            req_rev = True

        if (
            r_type == "RepresentedVariable"
            and cl_compat
            and m_type
            not in (
                MatchType.SHARED_STEM.value,
                "SHARED_STEM",
                "SHARED_STEM_GRID",
            )
        ):
            details["codelist_status"] = cl_status
            details["codelist_urn"] = rec_a.get("codelist_urn") or rec_b.get("codelist_urn")

        return {
            "resource_type": r_type,
            "source_urn": urn_a,
            "target_urn": urn_b,
            "match_type": m_type,
            "confidence": conf,
            "recommended_action": rec_action,
            "requires_review": req_rev,
            "details": {
                "source_text": rec_a.get("text"),
                "target_text": rec_b.get("text"),
                "target_is_elevated": is_tgt_elevated,
                **details,
            },
        }

    return None


def discover_candidates(
    resource_type: str | None = None,
    study_urn: str | None = None,
    batch_id: int | None = None,
    query: str | None = None,
    threshold: float = 0.75,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Discover harmonization candidate pairs across the ReQuest database.

    Args:
        resource_type: Optional filter ('Category', 'CodeList', 'QuestionItem',
                       'RepresentedVariable'). If None, searches across all 4 core types.
        study_urn: Optional StudyUnit URN to scope source candidates to.
        batch_id: Optional IngestBatch ID to scope source candidates to.
        query: Optional substring filter on URN or text/label.
        threshold: Minimum similarity confidence score (0.0 to 1.0, default 0.75).
        limit: Maximum number of ranked candidate pairs to return.
    """
    from fairwddi.models import IngestBatch, InstanceVariable, URNAlias

    target_types = (
        [resource_type]
        if resource_type
        else ["Category", "CodeList", "QuestionItem", "RepresentedVariable"]
    )

    alias_map = dict(URNAlias.objects.values_list("alias_urn", "canonical_urn"))
    codes_cache: dict[str, list[tuple[str, str]]] = {}

    scoped_urns: set[str] | None = None
    if batch_id is not None:
        batch = IngestBatch.objects.filter(id=batch_id).first()
        if not batch:
            raise ValueError(f"IngestBatch #{batch_id} does not exist.")
        scoped_urns = set(batch.created_urns or []) | set(batch.reused_urns or [])
    elif study_urn is not None:
        iv_rvs = set(
            InstanceVariable.objects.filter(datafiles__study_unit_id=study_urn)
            .exclude(represented_variable__isnull=True)
            .values_list("represented_variable_id", flat=True)
        )
        scoped_urns = iv_rvs

    candidates: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str]] = set()

    for r_type in target_types:
        records = _load_resource_records(r_type, query=query)
        n = len(records)
        for i in range(n):
            for j in range(i + 1, n):
                item_a = records[i]
                item_b = records[j]
                if scoped_urns is not None:
                    if item_a["urn"] not in scoped_urns and item_b["urn"] not in scoped_urns:
                        continue
                    # Ensure source_urn is the one from the scoped batch/study
                    if item_b["urn"] in scoped_urns and item_a["urn"] not in scoped_urns:
                        src_item, tgt_item = item_b, item_a
                    else:
                        src_item, tgt_item = item_a, item_b
                else:
                    src_item, tgt_item = item_a, item_b

                # If src_item is already elevated and tgt_item is study-specific,
                # orient so study-specific is absorbed into elevated target
                if src_item.get("is_elevated") and not tgt_item.get("is_elevated"):
                    src_item, tgt_item = tgt_item, src_item

                pair_key = (src_item["urn"], tgt_item["urn"])
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                cand = _compare_pair(
                    src_item,
                    tgt_item,
                    threshold=threshold,
                    alias_map=alias_map,
                    codes_cache=codes_cache,
                )
                if cand is not None:
                    candidates.append(cand)

    candidates.sort(key=lambda c: (-c["confidence"], c["resource_type"], c["source_urn"]))
    return candidates[:limit]


def compare_batch(
    batch_id: int,
    threshold: float = 0.75,
    output_dir: str | Path | None = None,
    limit: int = 1000,
    resource_type: str | None = None,
) -> IngestPlan:
    """Compare resources from an IngestBatch against the bank and return a Compare Plan."""
    from fairwddi.models import IngestBatch

    batch = IngestBatch.objects.filter(id=batch_id).first()
    if not batch:
        raise ValueError(f"IngestBatch #{batch_id} does not exist.")

    candidates = discover_candidates(
        resource_type=resource_type,
        batch_id=batch_id,
        threshold=threshold,
        limit=limit,
    )
    actions: list[PlanActionItem] = []
    by_match_type: dict[str, int] = {}
    by_resource_type: dict[str, int] = {}

    for idx, cand in enumerate(candidates, start=1):
        m_type = cand["match_type"]
        r_type = cand["resource_type"]
        by_match_type[m_type] = by_match_type.get(m_type, 0) + 1
        by_resource_type[r_type] = by_resource_type.get(r_type, 0) + 1
        actions.append(
            PlanActionItem(
                id=f"cmp-{idx:04d}",
                stage="compare",
                action=cand["recommended_action"],
                resource_type=cand["resource_type"],
                source_urn=cand["source_urn"],
                target_urn=cand["target_urn"],
                confidence=cand["confidence"],
                match_type=m_type,
                requires_review=cand["requires_review"],
                details=cand["details"],
                notes=f"{m_type} match (confidence={cand['confidence']:.2f})",
            )
        )

    job_id = f"compare-batch-{batch_id}-{uuid.uuid4().hex[:6]}"
    plan = IngestPlan(
        stage="compare",
        job_id=job_id,
        source_file=batch.file_name,
        source_format=batch.source_format,
        batch_id=batch_id,
        summary={
            "total_candidates": len(candidates),
            "threshold": threshold,
            "by_match_type": by_match_type,
            "by_resource_type": by_resource_type,
        },
        actions=actions,
        review_gate=ReviewGate(approved=(len(candidates) == 0)),
    )

    if output_dir is not None:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        stem = Path(batch.file_name).stem
        plan.to_yaml(out_dir / f"{stem}.batch{batch_id}.compare.plan.yaml")
        plan.to_markdown(out_dir / f"{stem}.batch{batch_id}.compare.report.md")

    return plan
