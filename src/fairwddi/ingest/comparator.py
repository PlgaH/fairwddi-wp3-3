"""Stage 3a (Comparison & Discovery): Cross-survey candidate discovery and similarity comparison.

Evaluates ReQuest resources (Category, CodeList, QuestionItem, RepresentedVariable) across tiers:
1. EXACT (1.00): Identical content hash.
2. FACET_EXACT (0.95): Identical normalized label or question_text hash across present languages.
3. MULTILINGUAL_OVERLAP (0.92): Exact match in at least one shared language with complementary
   translations, or complementary language labels on matching code structures.
4. NEAR_EXACT (0.96 - 0.98): Identical after loose punctuation normalization or >= 0.98 similarity.
5. INCLUSIVE_WRITING_VARIANT (0.98): Identical after stripping inclusive gender/plural markers.
6. TYPOGRAPHICAL_VARIANT (0.95): Single-word typographical or grammatical error variant.
7. PHRASING_VARIANT (0.92 - 0.94): Stylistic or pronominal phrasing variation.
8. SHARED_STEM_GRID (0.88): Shared question/category stem followed by distinct sub-items/choices.
9. SUBSTANTIVE_PERMUTATION (0.88): CodeLists sharing identical substantive categories.
10. CATEGORIES_EXACT_CODES_DIFFERENT (0.85): CodeLists with identical categories, different codes.
11. SYNTACTIC_SIMILAR (0.75 - 0.91): General normalized string similarity on label/question_text.
"""

from __future__ import annotations

import difflib
import os
import re
import uuid
from pathlib import Path
from typing import Any

from fairwddi.ingest.plan import IngestPlan, PlanActionItem, ReviewGate
from fairwddi.utils.normalize_string import normalize_string

_INCLUSIVE_PATTERN = re.compile(
    r"\(\s*(?:e|es|s|ne|nes|ve|ves|trice|trices|ère|ères|se|ses|x)\s*\)"
    r"|[\u00b7\u22c5\.]\s*(?:e|es|s|ne|nes)\b",
    re.IGNORECASE,
)

_LEADING_PRONOUN_PATTERN = re.compile(
    r"^(?:je\s+|j['’]\s*|moi\s*,?\s+|nous\s+|on\s+|i\s+|we\s+)",
    re.IGNORECASE,
)

_FEMININE_NOUNS_AFTER_MON = {
    "mère",
    "mere",
    "soeur",
    "sœur",
    "fille",
    "femme",
    "tante",
    "grand-mère",
    "grand-mere",
    "famille",
    "maison",
    "voiture",
    "santé",
    "sante",
    "vie",
}


def _raw_lang_dict(d: Any) -> dict[str, str]:
    """Extract language-keyed dictionary preserving original casing (with whitespace normalized)."""
    if not d:
        return {}
    if isinstance(d, list):
        res: dict[str, str] = {}
        for item in d:
            if isinstance(item, dict):
                lang = (
                    item.get("lang")
                    or item.get("@lang")
                    or item.get("language")
                    or item.get("@language")
                    or "en"
                )
                val = item.get("value") or item.get("@value") or item.get("text") or ""
                cleaned = normalize_string(str(val))
                if cleaned:
                    res[str(lang).lower()] = cleaned
        return res
    if isinstance(d, dict):
        return {
            str(k).lower(): normalize_string(str(v)) for k, v in d.items() if v and str(v).strip()
        }
    return {}


def _norm_lang_dict(d: Any) -> dict[str, str]:
    return {k: v.lower() for k, v in _raw_lang_dict(d).items()}


def _normalize_text_loose(text: str) -> str:
    """Strip trailing/leading punctuation, quotes, and French punctuation spacing."""
    cleaned = normalize_string(text, french_punctuation=False).lower()
    cleaned = re.sub(r"\s+([?!:;])", r"\1", cleaned)
    cleaned = re.sub(r"[\s\?\!\.\:\;\,\…\"\'\«\»]+$", "", cleaned)
    cleaned = re.sub(r"^[\s\?\!\.\:\;\,\…\"\'\«\»]+", "", cleaned)
    return " ".join(cleaned.split())


def _strip_inclusive_markers(text: str) -> str:
    """Remove parenthetical or midpoint French inclusive gender/plural markers."""
    cleaned = _INCLUSIVE_PATTERN.sub("", text)
    return " ".join(cleaned.split())


def _has_inclusive_markers(text: str) -> bool:
    return bool(_INCLUSIVE_PATTERN.search(text))


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
    if not raw_a or not raw_b:
        return None

    # 1. Explicit delimiter split (e.g. "... concernant votre quartier ? Manque d'espaces verts")
    delim_re = re.compile(r"^(.{20,}?[\?\:\;\—\–])\s+(.+)$")
    ma = delim_re.match(raw_a.strip())
    mb = delim_re.match(raw_b.strip())
    if ma and mb:
        stem_a, sub_a = ma.group(1).strip(), ma.group(2).strip()
        stem_b, sub_b = mb.group(1).strip(), mb.group(2).strip()
        stem_sim = _text_similarity(
            _strip_inclusive_markers(_normalize_text_loose(stem_a)),
            _strip_inclusive_markers(_normalize_text_loose(stem_b)),
        )
        sub_sim = _text_similarity(
            _normalize_text_loose(sub_a),
            _normalize_text_loose(sub_b),
        )
        if stem_sim >= 0.90 and sub_a and sub_b and sub_sim < 0.80:
            canonical_stem = stem_a if len(stem_a) >= len(stem_b) else stem_b
            return {
                "group_type": "question_grid",
                "shared_stem": canonical_stem,
                "sub_item_a": sub_a,
                "sub_item_b": sub_b,
                "stem_similarity": stem_sim,
                "stem_ratio": round(len(canonical_stem) / max(len(raw_a), len(raw_b)), 4),
            }

    # 2. Common prefix on word boundaries without shared trailing suffix
    norm_a = raw_a.strip()
    norm_b = raw_b.strip()
    common_pref = os.path.commonprefix([norm_a.lower(), norm_b.lower()])
    if len(common_pref) >= max(35, min_stem_len):
        # Snap back to last whitespace or punctuation boundary
        boundary = re.search(r"^(.*[\s\?\:\;\-\—\–])", common_pref)
        if boundary:
            cut = len(boundary.group(1))
            stem = norm_a[:cut].strip()
            sub_a = norm_a[cut:].strip()
            sub_b = norm_b[cut:].strip()
            common_suff = os.path.commonprefix([sub_a.lower()[::-1], sub_b.lower()[::-1]])
            if (
                len(stem) >= 30
                and sub_a
                and sub_b
                and len(common_suff) < 5
                and len(stem) / max(len(norm_a), len(norm_b)) >= 0.55
                and _text_similarity(_normalize_text_loose(sub_a), _normalize_text_loose(sub_b))
                < 0.80
            ):
                return {
                    "group_type": "question_grid",
                    "shared_stem": stem,
                    "sub_item_a": sub_a,
                    "sub_item_b": sub_b,
                    "stem_similarity": 1.0,
                    "stem_ratio": round(len(stem) / max(len(norm_a), len(norm_b)), 4),
                }

    return None


def _detect_wording_or_typo_variant(
    raw_a: str,
    raw_b: str,
    lang: str,
    best_sim: float,
) -> tuple[str, float, dict[str, Any]] | None:
    """Classify stylistic/pronominal phrasing variants vs grammatical/typographical errors."""
    loose_a = _normalize_text_loose(raw_a)
    loose_b = _normalize_text_loose(raw_b)

    # 1. Leading pronoun / stylistic shift (e.g., "Je refuse de répondre" vs "Refuse de répondre")
    stripped_pro_a = _LEADING_PRONOUN_PATTERN.sub("", loose_a).strip()
    stripped_pro_b = _LEADING_PRONOUN_PATTERN.sub("", loose_b).strip()
    if stripped_pro_a == stripped_pro_b and stripped_pro_a:
        canonical = raw_a if len(raw_a) >= len(raw_b) else raw_b
        variant = raw_b if canonical == raw_a else raw_a
        return (
            "PHRASING_VARIANT",
            0.94,
            {
                "variant_type": "stylistic",
                "canonical_text": {lang: canonical},
                "preserved_variants": [variant],
                "discarded_variants": [],
            },
        )

    # 2. Single-token typo or grammatical error in multi-word text
    #    e.g., "Ma mère était déjà décédée à l'époque" vs "Mon mère était déjà décédée à l'époque"
    words_a = loose_a.split()
    words_b = loose_b.split()
    if len(words_a) == len(words_b) and len(words_a) >= 4:
        diffs = [
            (idx, wa, wb)
            for idx, (wa, wb) in enumerate(zip(words_a, words_b, strict=False))
            if wa != wb
        ]
        if len(diffs) == 1:
            idx, wa, wb = diffs[0]
            # Exclude single-letter codes/grades (e.g. "catégorie c" vs "catégorie b") or numbers
            if len(wa) >= 2 and len(wb) >= 2 and not wa.isdigit() and not wb.isdigit():
                word_sim = _text_similarity(wa, wb)
                # Either high word similarity (typo like vancances/vacances) or grammar (ma/mon)
                is_possessive_pair = {wa, wb} <= {"ma", "mon", "mes", "ta", "ton", "sa", "son"}
                if word_sim >= 0.65 or is_possessive_pair:
                    next_word = words_a[idx + 1] if idx + 1 < len(words_a) else ""
                    # Determine which one is the grammatical error vs canonical
                    if is_possessive_pair and next_word in _FEMININE_NOUNS_AFTER_MON:
                        bad_is_a = wa in ("mon", "ton", "son")
                    else:
                        # Default: target (raw_b) is canonical unless raw_a is known clean
                        bad_is_a = True
                    canonical = raw_b if bad_is_a else raw_a
                    discarded = raw_a if bad_is_a else raw_b
                    return (
                        "TYPOGRAPHICAL_VARIANT",
                        0.96,
                        {
                            "variant_type": "typographical_or_grammar",
                            "divergence": [wa, wb],
                            "canonical_text": {lang: canonical},
                            "preserved_variants": [],
                            "discarded_variants": [discarded],
                        },
                    )

    return None


def _compare_multilingual_texts(
    ml_a: dict[str, str] | list[Any] | None,
    ml_b: dict[str, str] | list[Any] | None,
) -> tuple[str | None, float, dict[str, Any]]:
    """Compare two multilingual text dictionaries and return (match_type, confidence, details)."""
    raw_a = _raw_lang_dict(ml_a)
    raw_b = _raw_lang_dict(ml_b)
    na = {k: v.lower() for k, v in raw_a.items()}
    nb = {k: v.lower() for k, v in raw_b.items()}
    if not na or not nb:
        return None, 0.0, {}

    if na == nb:
        return "FACET_EXACT", 0.95, {"languages": list(na.keys())}

    shared_langs = sorted(set(na.keys()) & set(nb.keys()))
    if shared_langs:
        exact_shared = [lng for lng in shared_langs if na[lng] == nb[lng]]
        if exact_shared:
            new_langs_in_a = sorted(set(na.keys()) - set(nb.keys()))
            new_langs_in_b = sorted(set(nb.keys()) - set(na.keys()))
            return (
                "MULTILINGUAL_OVERLAP",
                0.92,
                {
                    "matched_languages": exact_shared,
                    "source_extra_languages": new_langs_in_a,
                    "target_extra_languages": new_langs_in_b,
                },
            )

        best_lang = max(shared_langs, key=lambda lng: _text_similarity(na[lng], nb[lng]))
        best_sim = _text_similarity(na[best_lang], nb[best_lang])
        ra = raw_a[best_lang]
        rb = raw_b[best_lang]

        # 1. Loose punctuation equivalence (e.g., trailing '?' or French spacing before '?')
        loose_a = _normalize_text_loose(ra)
        loose_b = _normalize_text_loose(rb)
        if loose_a and loose_a == loose_b:
            # Prefer version without stray trailing '?' if one has it and the other doesn't,
            # or keep target by default
            canonical = ra if rb.endswith("?") and not ra.endswith("?") else rb
            discarded = rb if canonical == ra else ra
            return (
                "NEAR_EXACT",
                0.98,
                {
                    "shared_languages": shared_langs,
                    "similarity": best_sim,
                    "variant_type": "punctuation",
                    "punctuation_variant": True,
                    "canonical_text": {best_lang: canonical},
                    "preserved_variants": [],
                    "discarded_variants": [discarded],
                },
            )

        # 2. Inclusive writing variant (e.g., "confronté(e)" vs "confronté")
        inc_a = _strip_inclusive_markers(loose_a)
        inc_b = _strip_inclusive_markers(loose_b)
        if inc_a and inc_a == inc_b:
            canonical = ra if _has_inclusive_markers(ra) else rb
            variant = rb if canonical == ra else ra
            return (
                "INCLUSIVE_WRITING_VARIANT",
                0.98,
                {
                    "shared_languages": shared_langs,
                    "similarity": best_sim,
                    "variant_type": "inclusive_writing",
                    "canonical_text": {best_lang: canonical},
                    "preserved_variants": [variant],
                    "discarded_variants": [],
                },
            )

        # 3. Shared-stem question grid / battery detection
        stem_info = _detect_shared_stem(ra, rb)
        if stem_info is not None:
            return (
                "SHARED_STEM_GRID",
                0.88,
                {
                    "shared_languages": shared_langs,
                    "similarity": best_sim,
                    **stem_info,
                },
            )

        # 4. Stylistic phrasing variant or single-word grammatical/typo error
        variant_match = _detect_wording_or_typo_variant(ra, rb, best_lang, best_sim)
        if variant_match is not None:
            v_type, v_conf, v_details = variant_match
            return (
                v_type,
                v_conf,
                {
                    "shared_languages": shared_langs,
                    "similarity": best_sim,
                    **v_details,
                },
            )

        # 5. High-similarity NEAR_EXACT (>= 0.98)
        if best_sim >= 0.98:
            return (
                "NEAR_EXACT",
                round(max(0.96, best_sim), 4),
                {
                    "shared_languages": shared_langs,
                    "similarity": best_sim,
                    "variant_type": "near_exact",
                    "canonical_text": {best_lang: rb},
                    "preserved_variants": [],
                    "discarded_variants": [ra],
                },
            )

        # 6. General SYNTACTIC_SIMILAR (0.75 <= best_sim < 0.98)
        if best_sim >= 0.75:
            return (
                "SYNTACTIC_SIMILAR",
                round(min(0.91, best_sim), 4),
                {"shared_languages": shared_langs, "similarity": best_sim},
            )

    return None, 0.0, {}


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
            records.append(
                {
                    "urn": rv.urn,
                    "resource_type": "RepresentedVariable",
                    "name": rv.name,
                    "text": text_map,
                    "codelist_urn": rv.code_list_id,
                    "question_urns": q_urns,
                    "content_hash": (rv.hashes or {}).get("content"),
                    "is_elevated": _is_record_elevated(
                        rv.urn, rv.extended_attributes, elevated_urns
                    ),
                }
            )

    return records


def _compare_pair(
    rec_a: dict[str, Any],
    rec_b: dict[str, Any],
    threshold: float = 0.75,
) -> dict[str, Any] | None:
    """Compare two resource records of the same type and return a candidate dict if >= threshold."""
    r_type = rec_a["resource_type"]
    urn_a = rec_a["urn"]
    urn_b = rec_b["urn"]
    if urn_a == urn_b:
        return None

    is_tgt_elevated = bool(rec_b.get("is_elevated"))

    # 1. Exact content hash match
    if rec_a.get("content_hash") and rec_a.get("content_hash") == rec_b.get("content_hash"):
        return {
            "resource_type": r_type,
            "source_urn": urn_a,
            "target_urn": urn_b,
            "match_type": "EXACT",
            "confidence": 1.0,
            "recommended_action": "absorb" if is_tgt_elevated else "alias",
            "requires_review": False,
            "details": {
                "source_name": rec_a["name"],
                "target_name": rec_b["name"],
                "target_is_elevated": is_tgt_elevated,
            },
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
                    "match_type": "FACET_EXACT",
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
                    "match_type": "SUBSTANTIVE_PERMUTATION",
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
                    "match_type": "CATEGORIES_EXACT_CODES_DIFFERENT",
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
            langs_a = (
                set(text_a.keys())
                if isinstance(text_a, dict)
                else {item["lang"] for item in text_a if isinstance(item, dict) and "lang" in item}
                if isinstance(text_a, list)
                else set()
            )
            langs_b = (
                set(text_b.keys())
                if isinstance(text_b, dict)
                else {item["lang"] for item in text_b if isinstance(item, dict) and "lang" in item}
                if isinstance(text_b, list)
                else set()
            )
            if vals_a == vals_b and langs_a and langs_b and langs_a != langs_b:
                return {
                    "resource_type": "CodeList",
                    "source_urn": urn_a,
                    "target_urn": urn_b,
                    "match_type": "MULTILINGUAL_OVERLAP",
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
        if m_type == "SHARED_STEM_GRID":
            rec_action = "group"
            req_rev = True
        elif m_type == "MULTILINGUAL_OVERLAP":
            rec_action = "absorb" if is_tgt_elevated else "merge_multilingual"
            req_rev = False
        elif m_type == "FACET_EXACT":
            rec_action = "absorb" if is_tgt_elevated else "alias"
            req_rev = False
        elif m_type == "NEAR_EXACT":
            rec_action = "absorb" if is_tgt_elevated else "alias"
            req_rev = True
        elif m_type in (
            "INCLUSIVE_WRITING_VARIANT",
            "PHRASING_VARIANT",
            "TYPOGRAPHICAL_VARIANT",
        ):
            rec_action = "absorb" if is_tgt_elevated else "elevate"
            req_rev = True
        else:
            rec_action = "link_semantic"
            req_rev = True

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
    from fairwddi.models import IngestBatch, InstanceVariable

    target_types = (
        [resource_type]
        if resource_type
        else ["Category", "CodeList", "QuestionItem", "RepresentedVariable"]
    )

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

                cand = _compare_pair(src_item, tgt_item, threshold=threshold)
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
