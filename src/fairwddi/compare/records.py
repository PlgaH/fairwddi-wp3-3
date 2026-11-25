"""Read-only database loader mapping ORM entities to normalized comparison records."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from dartfx.ddi.harmonizer import TextNormalizer


def _raw_lang_dict(val: Any) -> dict[str, str]:
    if isinstance(val, dict):
        return {str(k).strip().lower(): str(v).strip() for k, v in val.items() if str(v).strip()}
    if isinstance(val, list):
        out: dict[str, str] = {}
        for item in val:
            if isinstance(item, dict) and item.get("value"):
                lang = str(item.get("language") or item.get("lang") or "en").strip().lower()
                out[lang] = str(item["value"]).strip()
        return out
    if isinstance(val, str) and val.strip():
        return {"en": val.strip()}
    return {}


def _norm_lang_dict(val: Any, normalizer: TextNormalizer | None = None) -> dict[str, str]:
    norm = normalizer or TextNormalizer()
    return norm.extract_multilingual_dict(val, normalize_spacing=True, lowercase=False)


def _display_from_ml(ml: dict[str, str], fallback: str = "") -> str:
    if ml:
        for lang in ("fr", "en"):
            if lang in ml and ml[lang].strip():
                return ml[lang].strip()
        return next(iter(ml.values())).strip()
    return fallback


def _merge_field_dicts(
    field_dicts: Sequence[dict[str, str]],
) -> dict[str, str]:
    """Combine multiple multilingual field dicts cleanly by language key."""
    merged: dict[str, str] = {}
    for d in field_dicts:
        for lang, text in d.items():
            if not text:
                continue
            if lang not in merged:
                merged[lang] = text
            elif text not in merged[lang]:
                merged[lang] = f"{merged[lang]} — {text}"
    return merged


def _load_codelist_codes(
    codelist_urns: set[str],
) -> dict[str, list[tuple[str, str, bool]]]:
    """Return `{codelist_urn: [(code_value, cat_label, is_missing), ...]}`."""
    from fairwddi.models import Code

    by_cl: dict[str, list[tuple[str, str, bool]]] = {}
    if not codelist_urns:
        return by_cl

    for code in (
        Code.objects.filter(code_list_id__in=codelist_urns)
        .select_related("category")
        .order_by("code_list_id", "order", "code_value")
    ):
        cat_lbl = ""
        cat_missing = False
        if code.category:
            cat_missing = bool(code.category.is_missing)
            cat_lbl = _display_from_ml(
                _norm_lang_dict(code.category.label),
                fallback=str(code.category.name or ""),
            )
        is_missing = bool(code.is_missing) or cat_missing
        by_cl.setdefault(code.code_list_id, []).append(
            (str(code.code_value or ""), cat_lbl, is_missing)
        )
    return by_cl


def load_records_for_urns(
    resource_type: str,
    urns: set[str],
    *,
    fields: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    """Load read-only normalized comparison dicts for explicit URNs of `resource_type`."""
    from fairwddi.models import (
        Category,
        CodeList,
        ConceptualVariable,
        QuestionItem,
        RepresentedVariable,
        SemanticRelationship,
    )

    if not urns:
        return []

    normalizer = TextNormalizer()

    lineage_targets: dict[str, set[str]] = {}
    for subj_u, obj_u in SemanticRelationship.objects.filter(
        predicate="prov:wasDerivedFrom",
        object_urn__in=urns,
    ).values_list("subject_urn", "object_urn"):
        lineage_targets.setdefault(obj_u, set()).add(subj_u)

    concept_rel_links: dict[str, list[dict[str, str]]] = {}
    for subj_u, pred, obj_u in SemanticRelationship.objects.filter(
        predicate__in=(
            "skos:exactMatch",
            "skos:closeMatch",
            "skos:broadMatch",
            "skos:narrowMatch",
            "dcterms:subject",
        ),
        subject_urn__in=urns,
    ).values_list("subject_urn", "predicate", "object_urn"):
        concept_rel_links.setdefault(subj_u, []).append({"predicate": pred, "concept_urn": obj_u})

    records: list[dict[str, Any]] = []

    if resource_type == "Category":
        for cat in Category.objects.filter(urn__in=urns).order_by("urn"):
            lbl_ml = _norm_lang_dict(cat.label, normalizer)
            raw_lbl = _raw_lang_dict(cat.label)
            text = _display_from_ml(lbl_ml, fallback=str(cat.name or ""))
            records.append(
                {
                    "urn": cat.urn,
                    "resource_type": "Category",
                    "origin": cat.origin or "imported",
                    "name": str(cat.name or ""),
                    "text": text,
                    "ml_text": lbl_ml,
                    "raw_ml": raw_lbl,
                    "is_missing": bool(cat.is_missing),
                    "concept_urn": cat.concept_id,
                    "concept_links": concept_rel_links.get(cat.urn, []),
                    "codelist_urn": None,
                    "codes": [],
                    "study_urns": set(),
                    "harmonized_targets": lineage_targets.get(cat.urn, set()),
                    "hashes": cat.hashes or {},
                }
            )
        return records

    if resource_type == "CodeList":
        cl_list = list(CodeList.objects.filter(urn__in=urns).order_by("urn"))
        codes_by_cl = _load_codelist_codes({cl.urn for cl in cl_list})
        for cl in cl_list:
            desc_ml = _norm_lang_dict(cl.description, normalizer)
            raw_desc = _raw_lang_dict(cl.description)
            codes = codes_by_cl.get(cl.urn, [])
            text = _display_from_ml(desc_ml, fallback=str(cl.name or ""))
            records.append(
                {
                    "urn": cl.urn,
                    "resource_type": "CodeList",
                    "origin": cl.origin or "imported",
                    "name": str(cl.name or ""),
                    "text": text,
                    "ml_text": desc_ml,
                    "raw_ml": raw_desc,
                    "concept_urn": None,
                    "concept_links": concept_rel_links.get(cl.urn, []),
                    "codelist_urn": cl.urn,
                    "codes": codes,
                    "study_urns": set(),
                    "harmonized_targets": lineage_targets.get(cl.urn, set()),
                    "hashes": cl.hashes or {},
                }
            )
        return records

    if resource_type == "QuestionItem":
        q_list = list(
            QuestionItem.objects.filter(urn__in=urns)
            .prefetch_related("variable_associations__represented_variable__instance_variables")
            .order_by("urn")
        )
        # Collect attached CodeLists via QuestionVariable -> RepresentedVariable -> CodeList
        q_cl_map: dict[str, str] = {}
        cl_urns: set[str] = set()
        q_studies: dict[str, set[str]] = {}
        for q in q_list:
            for qv in q.variable_associations.all():
                rv = qv.represented_variable
                if rv:
                    if rv.code_list_id and q.urn not in q_cl_map:
                        q_cl_map[q.urn] = rv.code_list_id
                        cl_urns.add(rv.code_list_id)
                    for iv in rv.instance_variables.all():
                        if isinstance(iv.extended_attributes, list):
                            for item in iv.extended_attributes:
                                if (
                                    isinstance(item, dict)
                                    and item.get("type") == "study_unit_urn"
                                    and item.get("value")
                                ):
                                    q_studies.setdefault(q.urn, set()).add(str(item["value"]))
        codes_by_cl = _load_codelist_codes(cl_urns)
        selected_fields = list(fields) if fields else ["question_text", "label"]

        for q in q_list:
            field_dicts: list[dict[str, str]] = []
            raw_field_dicts: list[dict[str, str]] = []
            for fname in selected_fields:
                if fname == "question_text":
                    qt_n = _norm_lang_dict(q.question_text, normalizer)
                    qt_r = _raw_lang_dict(q.question_text)
                    if qt_n:
                        field_dicts.append(qt_n)
                    if qt_r:
                        raw_field_dicts.append(qt_r)
                elif fname == "label":
                    # Check extended_attributes for label if distinct
                    if isinstance(q.extended_attributes, list):
                        for item in q.extended_attributes:
                            if isinstance(item, dict) and item.get("type") == "label":
                                field_dicts.append(_norm_lang_dict(item.get("value"), normalizer))
                                raw_field_dicts.append(_raw_lang_dict(item.get("value")))
                elif fname == "interviewer_instructions":
                    instr_n = _norm_lang_dict(q.interviewer_instructions, normalizer)
                    if instr_n:
                        field_dicts.append(instr_n)
                        raw_field_dicts.append(_raw_lang_dict(q.interviewer_instructions))

            if not field_dicts:
                qt_fallback = _norm_lang_dict(q.question_text, normalizer)
                if qt_fallback:
                    field_dicts.append(qt_fallback)
                    raw_field_dicts.append(_raw_lang_dict(q.question_text))

            ml_merged = _merge_field_dicts(field_dicts)
            raw_merged = _merge_field_dicts(raw_field_dicts)
            cl_u = q_cl_map.get(q.urn)
            text = _display_from_ml(ml_merged, fallback=str(q.name or ""))
            records.append(
                {
                    "urn": q.urn,
                    "resource_type": "QuestionItem",
                    "origin": q.origin or "imported",
                    "name": str(q.name or ""),
                    "text": text,
                    "ml_text": ml_merged,
                    "raw_ml": raw_merged,
                    "concept_urn": None,
                    "concept_links": concept_rel_links.get(q.urn, []),
                    "codelist_urn": cl_u,
                    "codes": codes_by_cl.get(cl_u, []) if cl_u else [],
                    "study_urns": q_studies.get(q.urn, set()),
                    "harmonized_targets": lineage_targets.get(q.urn, set()),
                    "hashes": q.hashes or {},
                }
            )
        return records

    if resource_type == "RepresentedVariable":
        rv_list = list(
            RepresentedVariable.objects.filter(urn__in=urns)
            .prefetch_related("question_associations__question_item", "instance_variables")
            .order_by("urn")
        )
        cl_urns = {rv.code_list_id for rv in rv_list if rv.code_list_id}
        codes_by_cl = _load_codelist_codes(cl_urns)
        selected_fields = list(fields) if fields else ["label", "description", "question_text"]

        for rv in rv_list:
            field_dicts = []
            raw_field_dicts = []
            for fname in selected_fields:
                if fname == "label":
                    n = _norm_lang_dict(rv.label, normalizer)
                    if n:
                        field_dicts.append(n)
                        raw_field_dicts.append(_raw_lang_dict(rv.label))
                elif fname == "description":
                    n = _norm_lang_dict(rv.description, normalizer)
                    if n:
                        field_dicts.append(n)
                        raw_field_dicts.append(_raw_lang_dict(rv.description))
                elif fname == "question_text":
                    for qa in rv.question_associations.all():
                        if qa.question_item and qa.question_item.question_text:
                            n = _norm_lang_dict(qa.question_item.question_text, normalizer)
                            if n:
                                field_dicts.append(n)
                                raw_field_dicts.append(
                                    _raw_lang_dict(qa.question_item.question_text)
                                )
                            break

            if not field_dicts:
                n = _norm_lang_dict(rv.label, normalizer) or _norm_lang_dict(
                    rv.description, normalizer
                )
                if n:
                    field_dicts.append(n)
                    raw_field_dicts.append(
                        _raw_lang_dict(rv.label) or _raw_lang_dict(rv.description)
                    )

            studies: set[str] = set()
            for iv in rv.instance_variables.all():
                if isinstance(iv.extended_attributes, list):
                    for item in iv.extended_attributes:
                        if (
                            isinstance(item, dict)
                            and item.get("type") == "study_unit_urn"
                            and item.get("value")
                        ):
                            studies.add(str(item["value"]))

            ml_merged = _merge_field_dicts(field_dicts)
            raw_merged = _merge_field_dicts(raw_field_dicts)
            cl_u = rv.code_list_id
            text = _display_from_ml(ml_merged, fallback=str(rv.name or ""))
            records.append(
                {
                    "urn": rv.urn,
                    "resource_type": "RepresentedVariable",
                    "origin": rv.origin or "imported",
                    "name": str(rv.name or ""),
                    "text": text,
                    "ml_text": ml_merged,
                    "raw_ml": raw_merged,
                    "concept_urn": rv.conceptual_variable.concept_id
                    if rv.conceptual_variable
                    else None,
                    "conceptual_variable_urn": rv.conceptual_variable_id,
                    "concept_links": concept_rel_links.get(rv.urn, []),
                    "codelist_urn": cl_u,
                    "codes": codes_by_cl.get(cl_u, []) if cl_u else [],
                    "study_urns": studies,
                    "harmonized_targets": lineage_targets.get(rv.urn, set()),
                    "hashes": rv.hashes or {},
                }
            )
        return records

    if resource_type == "ConceptualVariable":
        selected_fields = list(fields) if fields else ["label", "description"]
        for cv in ConceptualVariable.objects.filter(urn__in=urns).order_by("urn"):
            field_dicts = []
            raw_field_dicts = []
            for fname in selected_fields:
                if fname == "label":
                    n = _norm_lang_dict(cv.label, normalizer)
                    if n:
                        field_dicts.append(n)
                        raw_field_dicts.append(_raw_lang_dict(cv.label))
                elif fname == "description":
                    n = _norm_lang_dict(cv.description, normalizer)
                    if n:
                        field_dicts.append(n)
                        raw_field_dicts.append(_raw_lang_dict(cv.description))

            ml_merged = _merge_field_dicts(field_dicts)
            raw_merged = _merge_field_dicts(raw_field_dicts)
            text = _display_from_ml(ml_merged, fallback=str(cv.name or ""))
            records.append(
                {
                    "urn": cv.urn,
                    "resource_type": "ConceptualVariable",
                    "origin": cv.origin or "imported",
                    "name": str(cv.name or ""),
                    "text": text,
                    "ml_text": ml_merged,
                    "raw_ml": raw_merged,
                    "concept_urn": cv.concept_id,
                    "concept_links": concept_rel_links.get(cv.urn, []),
                    "codelist_urn": None,
                    "codes": [],
                    "study_urns": set(),
                    "harmonized_targets": lineage_targets.get(cv.urn, set()),
                    "hashes": cv.hashes or {},
                }
            )
        return records

    # Generic fallback (Concept, StudyUnit, InstanceVariable, Instrument) via QuestionVariable/etc.
    from fairwddi.models import Concept, InstanceVariable, Instrument, StudyUnit

    model_map = {
        "Concept": Concept,
        "InstanceVariable": InstanceVariable,
        "Instrument": Instrument,
        "StudyUnit": StudyUnit,
    }
    cls = model_map.get(resource_type)
    if cls is None:
        return records
    for obj in cls.objects.filter(urn__in=urns).order_by("urn"):
        raw_val = (
            getattr(obj, "label", None) or getattr(obj, "title", None) or getattr(obj, "name", "")
        )
        ml = _norm_lang_dict(raw_val, normalizer)
        raw_ml = _raw_lang_dict(raw_val)
        text = _display_from_ml(ml, fallback=str(getattr(obj, "name", obj.urn) or obj.urn))
        records.append(
            {
                "urn": obj.urn,
                "resource_type": resource_type,
                "origin": getattr(obj, "origin", "imported") or "imported",
                "name": str(getattr(obj, "name", "") or ""),
                "text": text,
                "ml_text": ml,
                "raw_ml": raw_ml,
                "concept_urn": obj.urn if resource_type == "Concept" else None,
                "concept_links": concept_rel_links.get(obj.urn, []),
                "codelist_urn": None,
                "codes": [],
                "study_urns": {obj.urn} if resource_type == "StudyUnit" else set(),
                "harmonized_targets": lineage_targets.get(obj.urn, set()),
                "hashes": getattr(obj, "hashes", {}) or {},
            }
        )
    return records
