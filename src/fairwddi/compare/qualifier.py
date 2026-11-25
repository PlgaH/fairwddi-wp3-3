"""Independent CodeList & context qualification engine (`fairwddi.compare.qualifier`).

Implements CDSP ReQuest safeguards:
- Isolates missing/sentinel codes (DDI-C `=missingvalue`, `is_missing=True`) from
  substantive response categories before comparing scales.
- Evaluates response-domain similarity independently of question/variable wording,
  flagging scale cardinality mismatches (e.g. 4 vs 5, 5 vs 7) and suspected dimension
  shifts (e.g. intensity vs frequency, `peu` vs `un peu`) so they are never silently merged.
- Attaches administration-context caveats reminding analysts that routing, filters,
  and survey mode (PAPI/CAPI/CAWI) sit outside automated wording comparisons.
"""

from __future__ import annotations

import difflib
from typing import Any

from dartfx.ddi.harmonizer import TextNormalizer, compare_codelists
from dartfx.ddi.harmonizer.domains.codes import Category as HCat
from dartfx.ddi.harmonizer.domains.codes import Code as HCode
from dartfx.ddi.harmonizer.domains.codes import CodeList as HCodeList

from fairwddi.compare.config import QualificationRuleConfig
from fairwddi.compare.models import CodeListQualification, QualificationReport

FREQUENCY_CUES: set[str] = {
    "toujours",
    "souvent",
    "parfois",
    "quelquefois",
    "rarement",
    "jamais",
    "always",
    "often",
    "sometimes",
    "rarely",
    "never",
}
INTENSITY_CUES: set[str] = {
    "beaucoup",
    "assez",
    "tres",
    "très",
    "peu",
    "pas du tout",
    "tout a fait",
    "tout à fait",
    "plutot",
    "plutôt",
    "very",
    "somewhat",
    "not at all",
    "a lot",
    "little",
}
ADMIN_CONTEXT_CAVEAT = (
    "Textual/semantic score excludes filter/routing conditions, interviewer mode "
    "(CAPI/PAPI/CAWI), and questionnaire wave context; verify administration equivalence manually."
)


def _norm_label(text: str, normalizer: TextNormalizer) -> str:
    return normalizer.normalize(text or "").casefold()


def _detect_dimension_cue(labels_a: list[str], labels_b: list[str]) -> str | None:
    joined_a = " ".join(labels_a).casefold()
    joined_b = " ".join(labels_b).casefold()
    a_freq = any(cue in joined_a for cue in FREQUENCY_CUES)
    b_freq = any(cue in joined_b for cue in FREQUENCY_CUES)
    a_int = any(cue in joined_a for cue in INTENSITY_CUES)
    b_int = any(cue in joined_b for cue in INTENSITY_CUES)
    if (a_freq and b_int and not b_freq) or (b_freq and a_int and not a_freq):
        return "Response labels appear to mix frequency vs. intensity scales."
    return None


def _build_hcodelist(
    urn: str,
    codes: list[tuple[str, str, bool]],
    normalizer: TextNormalizer,
) -> HCodeList:
    items = [
        HCode(
            value=val,
            category=HCat(label=_norm_label(lbl, normalizer), is_missing=is_miss),
            is_missing_override=is_miss,
        )
        for val, lbl, is_miss in codes
    ]
    return HCodeList(name=urn, urn=urn, codes=items)


def _split_codes(
    codes: list[tuple[str, str, bool]],
    exclude_missing: bool,
) -> tuple[list[tuple[str, str, bool]], list[tuple[str, str, bool]]]:
    if not exclude_missing:
        return list(codes), []
    substantive = [c for c in codes if not c[2]]
    missing = [c for c in codes if c[2]]
    return substantive, missing


def evaluate_qualification(
    rec_a: dict[str, Any],
    rec_b: dict[str, Any],
    resource_type: str,
    rule: QualificationRuleConfig,
) -> QualificationReport:
    """Evaluate response-domain qualification and context caveats independently."""
    normalizer = TextNormalizer()
    caveat: str | None = None
    if rule.warn_on_administration_context and resource_type in (
        "QuestionItem",
        "RepresentedVariable",
    ):
        caveat = ADMIN_CONTEXT_CAVEAT

    if not rule.enabled or resource_type not in (
        "CodeList",
        "RepresentedVariable",
        "QuestionItem",
    ):
        return QualificationReport(
            codelist_qualification=CodeListQualification.NOT_APPLICABLE,
            administration_context_caveat=caveat,
            compatible_for_merge=True,
        )

    codes_a: list[tuple[str, str, bool]] = list(rec_a.get("codes") or [])
    codes_b: list[tuple[str, str, bool]] = list(rec_b.get("codes") or [])
    cl_a = rec_a.get("codelist_urn")
    cl_b = rec_b.get("codelist_urn")

    if not codes_a and not codes_b:
        return QualificationReport(
            codelist_qualification=CodeListQualification.NOT_APPLICABLE,
            source_codelist_urn=cl_a,
            target_codelist_urn=cl_b,
            administration_context_caveat=caveat,
            compatible_for_merge=True,
        )

    if bool(codes_a) != bool(codes_b):
        return QualificationReport(
            codelist_qualification=CodeListQualification.UNCOMPARABLE_OR_UNCODED,
            source_codelist_urn=cl_a,
            target_codelist_urn=cl_b,
            substantive_count_source=len([c for c in codes_a if not c[2]]),
            substantive_count_target=len([c for c in codes_b if not c[2]]),
            missing_count_source=len([c for c in codes_a if c[2]]),
            missing_count_target=len([c for c in codes_b if c[2]]),
            administration_context_caveat=caveat,
            notes=["One resource has a categorical CodeList while the other is uncoded/open."],
            compatible_for_merge=False,
        )

    sub_a, miss_a = _split_codes(codes_a, rule.exclude_missing_from_scale_diff)
    sub_b, miss_b = _split_codes(codes_b, rule.exclude_missing_from_scale_diff)
    excluded_labels = sorted({f"{v}:{lbl or 'missing'}" for v, lbl, _ in (miss_a + miss_b)})

    sub_norm_pairs_a = [(v.strip(), _norm_label(lbl, normalizer)) for v, lbl, _ in sub_a]
    sub_norm_pairs_b = [(v.strip(), _norm_label(lbl, normalizer)) for v, lbl, _ in sub_b]
    miss_norm_pairs_a = [(v.strip(), _norm_label(lbl, normalizer)) for v, lbl, _ in miss_a]
    miss_norm_pairs_b = [(v.strip(), _norm_label(lbl, normalizer)) for v, lbl, _ in miss_b]

    labels_a = [lbl for _, lbl in sub_norm_pairs_a]
    labels_b = [lbl for _, lbl in sub_norm_pairs_b]
    dim_note = _detect_dimension_cue(labels_a, labels_b)

    base_kwargs: dict[str, Any] = {
        "source_codelist_urn": cl_a,
        "target_codelist_urn": cl_b,
        "substantive_count_source": len(sub_a),
        "substantive_count_target": len(sub_b),
        "missing_count_source": len(miss_a),
        "missing_count_target": len(miss_b),
        "missing_values_excluded": excluded_labels,
        "dimension_note": dim_note,
        "administration_context_caveat": caveat,
    }

    # 1. Identical substantive codes + check whether missing values are the only delta
    if sub_norm_pairs_a == sub_norm_pairs_b:
        if miss_norm_pairs_a == miss_norm_pairs_b:
            return QualificationReport(
                codelist_qualification=CodeListQualification.IDENTICAL,
                compatible_for_merge=True,
                notes=["Substantive and missing-value codes are identical."],
                **base_kwargs,
            )
        return QualificationReport(
            codelist_qualification=CodeListQualification.MISSING_VALUES_ONLY,
            compatible_for_merge=True,
            notes=[
                "Substantive categories match identically; difference is isolated to "
                "missing/non-response codes."
            ],
            **base_kwargs,
        )

    # 2. Check frequency vs. intensity dimension shift before cardinality comparison
    if rule.warn_on_dimension_mismatch and dim_note:
        return QualificationReport(
            codelist_qualification=CodeListQualification.DIMENSION_MISMATCH_SUSPECTED,
            compatible_for_merge=False,
            notes=[dim_note],
            **base_kwargs,
        )

    # 3. Substantive cardinality difference (e.g. 4-point vs 5-point or 5-point vs 7-point)
    if len(sub_a) != len(sub_b):
        return QualificationReport(
            codelist_qualification=CodeListQualification.SCALE_CARDINALITY_DIFF,
            compatible_for_merge=False,
            notes=[
                f"Substantive response-scale cardinality differs "
                f"({len(sub_a)} vs {len(sub_b)} substantive categories"
                + (
                    f"; {len(miss_a)} vs {len(miss_b)} missing excluded)."
                    if (miss_a or miss_b)
                    else ")."
                )
            ],
            **base_kwargs,
        )

    # 4. Same cardinality: recoded categories vs slight wording diff vs dimension mismatch
    set_labels_a = sorted(labels_a)
    set_labels_b = sorted(labels_b)
    if set_labels_a == set_labels_b:
        return QualificationReport(
            codelist_qualification=CodeListQualification.RECODED_SAME_CATEGORIES,
            compatible_for_merge=rule.allow_recoded_same_categories,
            notes=["Identical substantive category labels under different numeric code values."],
            **base_kwargs,
        )

    hcl_a = _build_hcodelist(str(cl_a or rec_a["urn"]), sub_a, normalizer)
    hcl_b = _build_hcodelist(str(cl_b or rec_b["urn"]), sub_b, normalizer)
    cl_res = compare_codelists(hcl_a, hcl_b, threshold=rule.codelist_label_threshold)
    pair_sim = sum(
        difflib.SequenceMatcher(None, la, lb).ratio()
        for la, lb in zip(labels_a, labels_b, strict=False)
    ) / max(1, len(labels_a))
    eff_sim = max(cl_res.score, pair_sim)

    if eff_sim >= 0.72:
        return QualificationReport(
            codelist_qualification=CodeListQualification.LABELS_SLIGHT_DIFF,
            compatible_for_merge=True,
            notes=[
                f"Same substantive cardinality ({len(sub_a)}) with minor category wording "
                f"differences (similarity={eff_sim:.2f})."
            ],
            **base_kwargs,
        )

    return QualificationReport(
        codelist_qualification=CodeListQualification.DIMENSION_MISMATCH_SUSPECTED,
        compatible_for_merge=False,
        notes=[
            f"Same cardinality ({len(sub_a)}) but low substantive label overlap "
            f"(similarity={eff_sim:.2f}); verify response scale equivalence."
        ],
        **base_kwargs,
    )
