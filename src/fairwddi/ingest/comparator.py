"""Stage 3a (Comparison & Discovery): Origin-aware cross-survey candidate discovery.

Evaluates ReQuest resources (Category, CodeList, QuestionItem, RepresentedVariable,
ConceptualVariable) with strict two-tier origin priority:

1. Tier 1 (`origin in ('generated', 'instantiated')`):
   Matches against already-harmonized or administrator-instantiated resources take top
   priority -> `link_existing` (links incoming `imported` resource via `prov:wasDerivedFrom`
   and enriches target metadata with alternate spellings / translations).
2. Tier 2 (`origin == 'imported'` not yet linked to a harmonized parent):
   Searched ONLY if Tier 1 finds no match -> `generate_harmonized` (creates a new
   `generated` resource combining the two `imported` resources with `prov:wasDerivedFrom`
   lineage links to both).
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
from fairwddi.utils.urn import generate_generic_urn

_normalizer = TextNormalizer()

HARMONIZABLE_RESOURCE_TYPES = (
    "Category",
    "CodeList",
    "QuestionItem",
    "RepresentedVariable",
    "ConceptualVariable",
)


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


def _load_resource_records(
    resource_type: str,
    query: str | None = None,
) -> list[dict[str, Any]]:
    """Load lightweight comparison records from the ReQuest database for a given resource type."""
    from fairwddi.models import (
        Category,
        CodeItem,
        CodeList,
        ConceptualVariable,
        QuestionItem,
        QuestionVariable,
        RepresentedVariable,
        SemanticRelationship,
        UrnRegistry,
    )

    origin_map = dict(UrnRegistry.objects.values_list("urn", "origin"))
    derived_from_map: dict[str, list[str]] = {}
    for obj_urn, subj_urn in SemanticRelationship.objects.filter(
        predicate="prov:wasDerivedFrom"
    ).values_list("object_urn", "subject_urn"):
        derived_from_map.setdefault(obj_urn, []).append(subj_urn)

    records: list[dict[str, Any]] = []
    q_low = query.lower() if query else None

    if resource_type == "Category":
        for cat in Category.objects.all().order_by("urn"):
            text_map = cat.label or {}
            text_dict = _raw_lang_dict(text_map)
            if (
                q_low
                and q_low not in cat.urn.lower()
                and not any(q_low in str(v).lower() for v in text_dict.values())
            ):
                continue
            records.append(
                {
                    "urn": cat.urn,
                    "resource_type": "Category",
                    "name": cat.name,
                    "text": text_map,
                    "content_hash": (cat.hashes or {}).get("content"),
                    "origin": origin_map.get(cat.urn, "instantiated"),
                    "harmonized_targets": derived_from_map.get(cat.urn, []),
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
                    "origin": origin_map.get(qi.urn, "instantiated"),
                    "harmonized_targets": derived_from_map.get(qi.urn, []),
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
            code_ml_pairs: list[tuple[str, dict[str, str], bool]] = []
            for ci in items:
                cat_lbl_dict = _norm_lang_dict(ci.category.label) if ci.category else {}
                cat_lbl = next(iter(cat_lbl_dict.values()), ci.category.urn if ci.category else "")
                code_pairs.append((str(ci.value).strip(), cat_lbl, bool(ci.is_missing)))
                code_ml_pairs.append((str(ci.value).strip(), cat_lbl_dict, bool(ci.is_missing)))
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
                    "codes_ml": code_ml_pairs,
                    "content_hash": (cl.hashes or {}).get("content"),
                    "origin": origin_map.get(cl.urn, "instantiated"),
                    "harmonized_targets": derived_from_map.get(cl.urn, []),
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
                    "origin": origin_map.get(rv.urn, "instantiated"),
                    "harmonized_targets": derived_from_map.get(rv.urn, []),
                }
            )

    elif resource_type == "ConceptualVariable":
        for cv in ConceptualVariable.objects.all().order_by("urn"):
            text_map = cv.label or {}
            text_dict = _raw_lang_dict(text_map)
            if (
                q_low
                and q_low not in cv.urn.lower()
                and not any(q_low in str(v).lower() for v in text_dict.values())
            ):
                continue
            records.append(
                {
                    "urn": cv.urn,
                    "resource_type": "ConceptualVariable",
                    "name": cv.name,
                    "text": text_map,
                    "content_hash": (cv.hashes or {}).get("content"),
                    "origin": origin_map.get(cv.urn, "instantiated"),
                    "harmonized_targets": derived_from_map.get(cv.urn, []),
                }
            )

    return records


def build_comparison_record(
    resource_type: str,
    urn: str,
    norm: dict[str, Any],
    origin: str = "imported",
    cat_labels: dict[str, Any] | None = None,
    codelist_hashes: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build an in-memory comparison record from normalized node data."""
    if resource_type == "QuestionItem":
        text_map = norm.get("question_text") or norm.get("label") or {}
    else:
        text_map = norm.get("label") or {}

    rec: dict[str, Any] = {
        "urn": urn,
        "resource_type": resource_type,
        "name": norm.get("name"),
        "text": text_map,
        "content_hash": (norm.get("hashes") or {}).get("content"),
        "origin": origin,
        "harmonized_targets": [],
    }

    if resource_type == "CodeList":
        code_pairs: list[tuple[str, str, bool]] = []
        code_ml_pairs: list[tuple[str, dict[str, str], bool]] = []
        lbl_map = cat_labels or {}
        for c in norm.get("codes", []):
            cat_u = c.get("category_urn") or ""
            raw_lbl = lbl_map.get(cat_u)
            cat_lbl_dict = _norm_lang_dict(raw_lbl) if raw_lbl else {}
            cat_lbl = next(iter(cat_lbl_dict.values()), cat_u)
            val_str = str(c.get("value", "")).strip()
            is_miss = bool(c.get("is_missing", False))
            code_pairs.append((val_str, cat_lbl, is_miss))
            code_ml_pairs.append((val_str, cat_lbl_dict, is_miss))
        rec["text"] = norm.get("description") or norm.get("label") or {}
        rec["codes"] = code_pairs
        rec["codes_ml"] = code_ml_pairs

    elif resource_type == "RepresentedVariable":
        cl_u = norm.get("codelist_urn")
        rec["codelist_urn"] = cl_u
        rec["codelist_hash"] = (codelist_hashes or {}).get(cl_u) if cl_u else None
        rec["question_urns"] = norm.get("question_urns") or []

    return rec


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
            lbl_dict = _norm_lang_dict(ci.category.label)
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
    lineage_map: dict[str, set[str]] | None = None,
) -> tuple[bool, str]:
    """Check if two CodeLists are identical, lineage-linked, content-equivalent, or divergent."""
    if not cl_a and not cl_b:
        return True, "both_uncoded"
    if bool(cl_a) != bool(cl_b):
        return False, "coded_vs_uncoded"
    if cl_a == cl_b:
        return True, "identical_urn"

    # Lineage / alias equivalence
    if lineage_map and cl_a and cl_b:
        parents_a = lineage_map.get(cl_a, set()) | {cl_a}
        parents_b = lineage_map.get(cl_b, set()) | {cl_b}
        if parents_a & parents_b:
            return True, "shared_harmonized_codelist"

    def _res(u: str) -> str:
        curr = u
        visited: set[str] = set()
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
    lineage_map: dict[str, set[str]] | None = None,
) -> dict[str, Any] | None:
    """Compare two resource records of the same type and return a candidate dict if >= threshold."""
    r_type = rec_a["resource_type"]
    urn_a = rec_a["urn"]
    urn_b = rec_b["urn"]
    if urn_a == urn_b:
        return None

    tgt_origin = rec_b.get("origin", "instantiated")
    tgt_is_harmonized = tgt_origin in ("generated", "instantiated")
    harmonizable_action = "link_existing" if tgt_is_harmonized else "generate_harmonized"

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
            lineage_map=lineage_map,
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
                    "target_origin": tgt_origin,
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
            "source_text": rec_a.get("text"),
            "target_text": rec_b.get("text"),
            "target_origin": tgt_origin,
        }
        if r_type == "RepresentedVariable":
            details["codelist_status"] = cl_status
            details["codelist_urn"] = rec_a.get("codelist_urn") or rec_b.get("codelist_urn")
        return {
            "resource_type": r_type,
            "source_urn": urn_a,
            "target_urn": urn_b,
            "match_type": MatchType.EXACT_IDENTICAL.value,
            "confidence": 1.0,
            "recommended_action": harmonizable_action,
            "requires_review": not tgt_is_harmonized,
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
                    "recommended_action": harmonizable_action,
                    "requires_review": not tgt_is_harmonized,
                    "details": {
                        "source_name": rec_a.get("name"),
                        "target_name": rec_b.get("name"),
                        "code_count": len(pairs_a),
                        "codes": [f"{v}: {lbl}" for v, lbl in pairs_a[:5]],
                        "target_origin": tgt_origin,
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
                        "target_origin": tgt_origin,
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
                        "target_origin": tgt_origin,
                        "shared_categories": sorted(cats_a),
                    },
                }

            # Check if code values are identical with complementary languages in labels
            vals_a = [v for v, _, _ in codes_a]
            vals_b = [v for v, _, _ in codes_b]
            langs_a = set(_raw_lang_dict(rec_a.get("text")).keys())
            langs_b = set(_raw_lang_dict(rec_b.get("text")).keys())
            codes_ml_a = rec_a.get("codes_ml") or []
            codes_ml_b = rec_b.get("codes_ml") or []
            if not langs_a and codes_ml_a:
                langs_a = {k for _, d, _ in codes_ml_a for k in d}
            if not langs_b and codes_ml_b:
                langs_b = {k for _, d, _ in codes_ml_b for k in d}
            if vals_a == vals_b and langs_a and langs_b and langs_a != langs_b:
                return {
                    "resource_type": "CodeList",
                    "source_urn": urn_a,
                    "target_urn": urn_b,
                    "match_type": MatchType.MULTILINGUAL_OVERLAP.value,
                    "confidence": 0.90,
                    "recommended_action": harmonizable_action,
                    "requires_review": True,
                    "details": {
                        "code_values": vals_a,
                        "source_languages": sorted(langs_a),
                        "target_languages": sorted(langs_b),
                        "target_origin": tgt_origin,
                    },
                }

        # CodeList identity is strictly structural; do not fall through to text/label comparison
        return None

    # 3. Text/Label comparison (Category, QuestionItem, RepresentedVariable, ConceptualVariable)
    m_type, conf, details = _compare_multilingual_texts(rec_a.get("text"), rec_b.get("text"))
    if m_type and conf >= threshold:
        if m_type in (MatchType.SHARED_STEM.value, "SHARED_STEM", "SHARED_STEM_GRID"):
            if r_type not in ("QuestionItem", "RepresentedVariable"):
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
        elif m_type in (
            MatchType.FACET_EXACT.value,
            MatchType.EXACT_IDENTICAL.value,
            MatchType.NORMALIZED_EXACT.value,
            MatchType.MULTILINGUAL_OVERLAP.value,
        ):
            rec_action = harmonizable_action
            req_rev = not tgt_is_harmonized
        elif m_type in (
            MatchType.NEAR_EXACT.value,
            MatchType.INCLUSIVE_WRITING_VARIANT.value,
            MatchType.PHRASING_VARIANT.value,
            MatchType.TYPOGRAPHICAL_VARIANT.value,
        ):
            rec_action = harmonizable_action
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
                "source_name": rec_a.get("name"),
                "target_name": rec_b.get("name"),
                "source_text": rec_a.get("text"),
                "target_text": rec_b.get("text"),
                "target_origin": tgt_origin,
                **details,
            },
        }

    return None


def _derive_slug_seed(rec_a: dict[str, Any], rec_b: dict[str, Any]) -> str | None:
    """Derive a clean human-readable seed string for generating a generic URN."""
    for rec in (rec_b, rec_a):
        text_dict = _raw_lang_dict(rec.get("text"))
        if text_dict:
            return text_dict.get("fr") or text_dict.get("en") or next(iter(text_dict.values()))
        name_val = rec.get("name")
        if isinstance(name_val, str) and name_val:
            return name_val
        if isinstance(name_val, list) and name_val and isinstance(name_val[0], dict):
            val = name_val[0].get("value")
            if val:
                return str(val)
    return None


def find_best_match_for_incoming(
    incoming_rec: dict[str, Any],
    bank_records: list[dict[str, Any]],
    threshold: float = 0.75,
    alias_map: dict[str, str] | None = None,
    codes_cache: dict[str, list[tuple[str, str]]] | None = None,
    lineage_map: dict[str, set[str]] | None = None,
    agency: str | None = None,
) -> dict[str, Any] | None:
    """Find the highest-priority harmonization match for an incoming resource record.

    Priority rules:

    1. Tier 1 (``origin in ('generated', 'instantiated')``):
       Always evaluated first. If any match qualifies for ``link_existing``, return the
       highest-confidence match immediately without evaluating Tier 2.
    2. Tier 2 (``origin == 'imported'`` with empty ``harmonized_targets``):
       Evaluated ONLY if Tier 1 yields no match. If matched, returns a ``generate_harmonized``
       candidate proposing a new ``generated`` URN that unites both ``imported`` resources.
    """
    r_type = incoming_rec["resource_type"]
    inc_urn = incoming_rec["urn"]

    # Tier 1: Search generated / instantiated resources first
    tier1_candidates: list[dict[str, Any]] = []
    for rec in bank_records:
        if rec["urn"] == inc_urn:
            continue
        if rec.get("origin") not in ("generated", "instantiated"):
            continue
        cand = _compare_pair(
            incoming_rec,
            rec,
            threshold=threshold,
            alias_map=alias_map,
            codes_cache=codes_cache,
            lineage_map=lineage_map,
        )
        if cand and cand["recommended_action"] == "link_existing":
            tier1_candidates.append(cand)

    if tier1_candidates:
        tier1_candidates.sort(
            key=lambda c: (
                -c["confidence"],
                0 if c["details"].get("target_origin") == "instantiated" else 1,
                c["target_urn"],
            )
        )
        return tier1_candidates[0]

    # Tier 2: Search unharmonized imported resources ONLY if Tier 1 found nothing
    tier2_candidates: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for rec in bank_records:
        if rec["urn"] == inc_urn:
            continue
        if rec.get("origin") != "imported":
            continue
        if rec.get("harmonized_targets"):
            continue
        cand = _compare_pair(
            incoming_rec,
            rec,
            threshold=threshold,
            alias_map=alias_map,
            codes_cache=codes_cache,
            lineage_map=lineage_map,
        )
        if cand and cand["recommended_action"] == "generate_harmonized":
            tier2_candidates.append((cand, rec))

    if tier2_candidates:
        tier2_candidates.sort(
            key=lambda pair: (-pair[0]["confidence"], pair[0]["target_urn"]),
        )
        best_cand, matched_rec = tier2_candidates[0]
        slug_seed = _derive_slug_seed(incoming_rec, matched_rec)
        gen_urn = generate_generic_urn(
            resource_type=r_type,
            name_or_text=slug_seed,
            agency=agency,
        )
        best_cand["details"]["generated_urn"] = gen_urn
        best_cand["details"]["matched_imported_urn"] = matched_rec["urn"]
        return best_cand

    return None


def discover_candidates(
    resource_type: str | None = None,
    study_urn: str | None = None,
    batch_id: int | None = None,
    query: str | None = None,
    threshold: float = 0.75,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Discover harmonization candidate pairs across the ReQuest database."""
    from fairwddi.models import IngestBatch, InstanceVariable, SemanticRelationship, URNAlias

    target_types = [resource_type] if resource_type else list(HARMONIZABLE_RESOURCE_TYPES[:4])

    alias_map = dict(URNAlias.objects.values_list("alias_urn", "canonical_urn"))
    lineage_map: dict[str, set[str]] = {}
    for subj_u, obj_u in SemanticRelationship.objects.filter(
        predicate="prov:wasDerivedFrom"
    ).values_list("subject_urn", "object_urn"):
        lineage_map.setdefault(obj_u, set()).add(subj_u)

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
                    if item_b["urn"] in scoped_urns and item_a["urn"] not in scoped_urns:
                        src_item, tgt_item = item_b, item_a
                    else:
                        src_item, tgt_item = item_a, item_b
                else:
                    src_item, tgt_item = item_a, item_b

                src_is_harm = src_item.get("origin") in ("generated", "instantiated")
                tgt_is_harm = tgt_item.get("origin") in ("generated", "instantiated")

                # Orient so imported source links into generated/instantiated target
                if src_is_harm and not tgt_is_harm:
                    src_item, tgt_item = tgt_item, src_item
                    src_is_harm, tgt_is_harm = tgt_is_harm, src_is_harm

                # Skip already-linked provenance pair
                if tgt_item["urn"] in (src_item.get("harmonized_targets") or []):
                    continue

                # If source is already harmonized into a target, skip imported-to-imported pairing
                if not tgt_is_harm and (
                    src_item.get("harmonized_targets") or tgt_item.get("harmonized_targets")
                ):
                    continue

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
                    lineage_map=lineage_map,
                )
                if cand is not None:
                    candidates.append(cand)

    # Sort Tier 1 (`link_existing`) ahead of Tier 2 (`generate_harmonized`), then by confidence
    candidates.sort(
        key=lambda c: (
            0 if c["recommended_action"] == "link_existing" else 1,
            -c["confidence"],
            c["resource_type"],
            c["source_urn"],
        )
    )
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
