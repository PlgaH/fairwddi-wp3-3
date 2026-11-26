"""Level 1 Syntactic & Textual comparator using `dartfx.ddi.harmonizer` and TokenBlocker."""

from __future__ import annotations

import difflib
from typing import Any

from dartfx.ddi.harmonizer import (
    MatchType,
    NearExactComparator,
    TextNormalizer,
    TextVariantComparator,
    TokenBlocker,
    compare_codelists,
    compare_multilingual_texts,
    detect_shared_stem,
)
from dartfx.ddi.harmonizer.domains.codes import Category as HCat
from dartfx.ddi.harmonizer.domains.codes import Code as HCode
from dartfx.ddi.harmonizer.domains.codes import CodeList as HCodeList
from pydantic import BaseModel

from fairwddi.compare.config import ResourceTypeComparisonRule
from fairwddi.compare.models import CorrespondenceLevel


class _BlockerItem(BaseModel):
    urn: str


def _detect_wording_or_typo(
    raw_a: str,
    raw_b: str,
    *,
    tvc_cmp: TextVariantComparator,
    nec_cmp: NearExactComparator,
    threshold: float,
) -> tuple[float, str, dict[str, Any]] | None:
    tvc = tvc_cmp.compare(raw_a, raw_b)
    if tvc is not None:
        return (
            float(tvc.score),
            str(tvc.match_type.value),
            {
                "variant_type": str(tvc.match_type.value).lower(),
                "rationale": tvc.rationale,
            },
        )

    nec = nec_cmp.compare(raw_a, raw_b)
    if nec.score >= threshold and nec.match_type != MatchType.DISTINCT:
        return (
            float(nec.score),
            str(nec.match_type.value),
            {"variant_type": str(nec.match_type.value).lower(), "rationale": nec.rationale},
        )
    return None


def _build_blocker_text(rec: dict[str, Any]) -> str:
    parts: list[str] = [str(rec.get("text") or ""), str(rec.get("name") or "")]
    for txt in (rec.get("ml_text") or {}).values():
        parts.append(str(txt))
    for _, lbl, is_miss in rec.get("codes") or []:
        if not is_miss and lbl:
            parts.append(lbl)
    return " ".join(p for p in parts if p).strip()


def compare_syntactic_sets(
    source_records: list[dict[str, Any]],
    target_records: list[dict[str, Any]],
    resource_type: str,
    rule: ResourceTypeComparisonRule,
    *,
    exclude_same_urn: bool = True,
    symmetric_sets: bool = False,
) -> list[dict[str, Any]]:
    """Run Level 1 syntactic/textual comparisons between source and target records."""
    syn_cfg = rule.syntactic
    if not syn_cfg.enabled or not source_records or not target_records:
        return []

    normalizer = TextNormalizer()
    blocker: TokenBlocker[_BlockerItem] | None = None
    target_by_urn = {r["urn"]: r for r in target_records}

    # Pre-cache CodeList models/signatures, normalized fallback text, and per-language comparators
    hcl_cache: dict[str, HCodeList] = {}
    cl_sig_cache: dict[str, tuple[tuple[str, str], ...]] = {}
    norm_text_cache: dict[str, str] = {}
    comparators_by_lang: dict[str, tuple[TextVariantComparator, NearExactComparator]] = {}

    if resource_type == "CodeList":
        for rec in (*source_records, *target_records):
            u = rec["urn"]
            if u in hcl_cache:
                continue
            sub = [c for c in (rec.get("codes") or []) if not c[2]]
            if not sub:
                continue
            norm_codes = [(v, normalizer.normalize(lbl).casefold()) for v, lbl, _ in sub]
            cl_sig_cache[u] = tuple(norm_codes)
            hcl_cache[u] = HCodeList(
                name=u,
                urn=u,
                codes=[HCode(value=v, category=HCat(label=nl)) for v, nl in norm_codes],
            )
    else:
        for rec in (*source_records, *target_records):
            u = rec["urn"]
            if u not in norm_text_cache and rec.get("text"):
                norm_text_cache[u] = normalizer.normalize(rec["text"]).casefold()

    use_blocker = (
        syn_cfg.enable_token_blocking and len(target_records) > 25 and resource_type != "CodeList"
    )
    if use_blocker:
        blocker = TokenBlocker[_BlockerItem](
            normalizer=normalizer,
            use_character_ngrams=syn_cfg.use_character_ngrams,
            ngram_size=3,
            min_token_length=2,
        )
        for tgt in target_records:
            blocker.add(_BlockerItem(urn=tgt["urn"]), text=_build_blocker_text(tgt))

    candidates: list[dict[str, Any]] = []
    seen_sym_pairs: set[tuple[str, str]] = set()

    for src in source_records:
        src_urn = src["urn"]
        if blocker is not None:
            blocked_items = blocker.get_candidates(
                _build_blocker_text(src),
                min_shared_tokens=syn_cfg.min_shared_tokens,
                top_k=50,
            )
            tgt_pool = [target_by_urn[it.urn] for it in blocked_items if it.urn in target_by_urn]
        else:
            tgt_pool = target_records

        for tgt in tgt_pool:
            tgt_urn = tgt["urn"]
            if exclude_same_urn and src_urn == tgt_urn:
                continue
            if symmetric_sets:
                pair_key = (min(src_urn, tgt_urn), max(src_urn, tgt_urn))
                if pair_key in seen_sym_pairs:
                    continue
                seen_sym_pairs.add(pair_key)

            res = _compare_pair_syntactic(
                src,
                tgt,
                resource_type,
                syn_cfg=syn_cfg,
                normalizer=normalizer,
                hcl_cache=hcl_cache,
                cl_sig_cache=cl_sig_cache,
                norm_text_cache=norm_text_cache,
                comparators_by_lang=comparators_by_lang,
            )
            if res is not None:
                candidates.append(res)

    return candidates


def _compare_pair_syntactic(
    src: dict[str, Any],
    tgt: dict[str, Any],
    resource_type: str,
    *,
    syn_cfg: Any,
    normalizer: TextNormalizer,
    hcl_cache: dict[str, HCodeList] | None = None,
    cl_sig_cache: dict[str, tuple[tuple[str, str], ...]] | None = None,
    norm_text_cache: dict[str, str] | None = None,
    comparators_by_lang: dict[str, tuple[TextVariantComparator, NearExactComparator]] | None = None,
) -> dict[str, Any] | None:
    if resource_type == "CodeList":
        hcl_a = hcl_cache.get(src["urn"]) if hcl_cache is not None else None
        hcl_b = hcl_cache.get(tgt["urn"]) if hcl_cache is not None else None
        if hcl_a is None or hcl_b is None:
            sub_a = [c for c in (src.get("codes") or []) if not c[2]]
            sub_b = [c for c in (tgt.get("codes") or []) if not c[2]]
            if not sub_a or not sub_b:
                return None
            hcl_a = HCodeList(
                name=src["urn"],
                urn=src["urn"],
                codes=[
                    HCode(value=v, category=HCat(label=normalizer.normalize(lbl).casefold()))
                    for v, lbl, _ in sub_a
                ],
            )
            hcl_b = HCodeList(
                name=tgt["urn"],
                urn=tgt["urn"],
                codes=[
                    HCode(value=v, category=HCat(label=normalizer.normalize(lbl).casefold()))
                    for v, lbl, _ in sub_b
                ],
            )
        if cl_sig_cache is not None:
            sig_a = cl_sig_cache.get(src["urn"])
            sig_b = cl_sig_cache.get(tgt["urn"])
            if sig_a is not None and sig_a == sig_b:
                return {
                    "level": CorrespondenceLevel.SYNTACTIC,
                    "resource_type": resource_type,
                    "source_rec": src,
                    "target_rec": tgt,
                    "match_type": MatchType.EXACT_IDENTICAL.value,
                    "confidence": 1.0,
                    "requires_review": False,
                    "details": {"codelist_score": 1.0},
                }
        cl_res = compare_codelists(hcl_a, hcl_b, threshold=syn_cfg.threshold)
        if cl_res.score < syn_cfg.threshold:
            return None
        match_type = (
            MatchType.EXACT_IDENTICAL.value
            if cl_res.score >= 0.999
            else str(cl_res.match_type.value or MatchType.NEAR_EXACT.value)
        )
        return {
            "level": CorrespondenceLevel.SYNTACTIC,
            "resource_type": resource_type,
            "source_rec": src,
            "target_rec": tgt,
            "match_type": match_type,
            "confidence": round(float(cl_res.score), 4),
            "requires_review": cl_res.score < 0.999,
            "details": {"codelist_score": round(float(cl_res.score), 4)},
        }

    src_ml = src.get("ml_text") or {}
    tgt_ml = tgt.get("ml_text") or {}
    src_raw_ml = src.get("raw_ml") or src_ml
    tgt_raw_ml = tgt.get("raw_ml") or tgt_ml

    best_score = 0.0
    best_type: str | None = None
    best_details: dict[str, Any] = {}

    # 1. Cross-language or same-language multilingual check via dartfx-ddi
    if src_ml and tgt_ml:
        ml_res = compare_multilingual_texts(
            src_ml,
            tgt_ml,
            threshold=syn_cfg.multilingual_threshold,
            normalizer=normalizer,
        )
        if ml_res.score >= syn_cfg.threshold and ml_res.score > best_score:
            best_score = float(ml_res.score)
            best_type = str(ml_res.match_type.value)
            best_details["rationale"] = ml_res.rationale

    # 2. Same-language wording, punctuation, inclusive writing, and typo checks
    shared_langs = sorted(set(src_raw_ml.keys()) & set(tgt_raw_ml.keys()))
    for lang in shared_langs:
        raw_a = src_raw_ml[lang]
        raw_b = tgt_raw_ml[lang]
        if syn_cfg.detect_wording or syn_cfg.detect_typos or syn_cfg.detect_inclusive:
            cmp_pair = comparators_by_lang.get(lang) if comparators_by_lang is not None else None
            if cmp_pair is None:
                cmp_pair = (
                    TextVariantComparator(normalizer, language=lang),
                    NearExactComparator(
                        normalizer,
                        language=lang,
                        near_exact_threshold=syn_cfg.near_exact_threshold,
                        syntactic_threshold=syn_cfg.threshold,
                    ),
                )
                if comparators_by_lang is not None:
                    comparators_by_lang[lang] = cmp_pair
            var = _detect_wording_or_typo(
                raw_a,
                raw_b,
                tvc_cmp=cmp_pair[0],
                nec_cmp=cmp_pair[1],
                threshold=syn_cfg.threshold,
            )
            if var is not None and var[0] >= best_score:
                if var[1] == MatchType.TYPOGRAPHICAL_VARIANT.value and not syn_cfg.detect_typos:
                    pass
                elif (
                    var[1] == MatchType.INCLUSIVE_WRITING_VARIANT.value
                    and not syn_cfg.detect_inclusive
                ):
                    pass
                else:
                    best_score, best_type, extra = var
                    best_details.update(extra)

        # 3. Shared-stem question grid check
        if syn_cfg.detect_shared_stems and resource_type in ("QuestionItem", "RepresentedVariable"):
            stem_res = detect_shared_stem(
                raw_a,
                raw_b,
                min_stem_len=syn_cfg.min_stem_length,
                context="question_grid",
                normalizer=normalizer,
                lang=lang,
            )
            if stem_res is not None and stem_res.stem_similarity >= syn_cfg.threshold:
                if stem_res.stem_similarity > best_score or best_type is None:
                    best_score = float(stem_res.stem_similarity)
                    best_type = MatchType.SHARED_STEM.value
                    best_details["shared_stem"] = stem_res.shared_stem
                    best_details["sub_item_a"] = stem_res.sub_item_a
                    best_details["sub_item_b"] = stem_res.sub_item_b
                    best_details["group_type"] = stem_res.group_type

    # Fallback direct string comparison when ml dictionaries are absent
    if best_type is None and src.get("text") and tgt.get("text"):
        txt_a = (
            norm_text_cache.get(src["urn"])
            if norm_text_cache is not None
            else normalizer.normalize(src["text"]).casefold()
        ) or normalizer.normalize(src["text"]).casefold()
        txt_b = (
            norm_text_cache.get(tgt["urn"])
            if norm_text_cache is not None
            else normalizer.normalize(tgt["text"]).casefold()
        ) or normalizer.normalize(tgt["text"]).casefold()
        ratio = difflib.SequenceMatcher(None, txt_a, txt_b).ratio()
        if ratio >= syn_cfg.threshold:
            best_score = float(ratio)
            best_type = (
                MatchType.NEAR_EXACT.value
                if ratio >= syn_cfg.near_exact_threshold
                else MatchType.SYNTACTIC_SIMILAR.value
            )

    if best_type is None or best_score < syn_cfg.threshold:
        return None

    return {
        "level": CorrespondenceLevel.SYNTACTIC,
        "resource_type": resource_type,
        "source_rec": src,
        "target_rec": tgt,
        "match_type": best_type,
        "confidence": round(best_score, 4),
        "requires_review": best_type
        not in (MatchType.EXACT_IDENTICAL.value, MatchType.NORMALIZED_EXACT.value),
        "details": best_details,
    }
