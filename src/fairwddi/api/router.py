"""Ninja API Router for FAIRwDDI Question Bank & Harmonization Explorer."""

from __future__ import annotations

from typing import Any
from urllib.parse import unquote

from fairwddi.db.config import configure_django_for_cli

configure_django_for_cli()

from ninja import NinjaAPI, Query

from fairwddi.api.schemas import (
    AliasItem,
    CategoryReference,
    CategorySummary,
    CodeItemInfo,
    CodeListQuestionRef,
    CodeListSummary,
    GraphLink,
    GraphNode,
    MatrixRow,
    MatrixWaveEntry,
    OverviewStats,
    QuestionCascadeGraph,
    QuestionItemSummary,
    SurveyItem,
)
from fairwddi.models import (
    Category,
    CodeList,
    IngestBatch,
    InstanceVariable,
    QuestionItem,
    StudyUnit,
    URNAlias,
)

api = NinjaAPI(
    title="FAIRwDDI Question Bank API",
    version="0.1.0",
    description="DDI-Lifecycle 4.0 / CDI Question Bank, Variable Cascade & Harmonization API",
    urls_namespace="fairwddi_api",
)


def _extract_display_text(val: Any, preferred_lang: str = "fr") -> str:
    """Extract a user-readable string from multilingual dict, list, or scalar."""
    if not val:
        return ""
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        if preferred_lang in val:
            return str(val[preferred_lang])
        for lang in ("en", "fr"):
            if lang in val:
                return str(val[lang])
        if val:
            return str(next(iter(val.values())))
        return ""
    if isinstance(val, list):
        for item in val:
            if isinstance(item, dict):
                if item.get("language") == preferred_lang and "value" in item:
                    return str(item["value"])
                if item.get("lang") == preferred_lang and "value" in item:
                    return str(item["value"])
                if preferred_lang in item:
                    return str(item[preferred_lang])
                if "value" in item:
                    return str(item["value"])
            elif isinstance(item, str):
                return item
    return str(val)


@api.get("/overview", response=OverviewStats, summary="Global bank overview and reuse statistics")
def get_overview(request: Any) -> OverviewStats:
    """Return counts of surveys, questions, harmonized questions, and URN aliases."""
    total_surveys = StudyUnit.objects.count()
    total_questions = QuestionItem.objects.count()
    total_variables = InstanceVariable.objects.count()
    total_categories = Category.objects.count()
    total_codelists = CodeList.objects.count()
    total_aliases = URNAlias.objects.count()
    total_batches = IngestBatch.objects.count()

    # Reused questions: questions linked to >= 2 distinct StudyUnits OR having URNAliases
    # Fast computation via alias canonical targets
    aliased_question_urns = set(
        URNAlias.objects.filter(entity_type="QuestionItem").values_list(
            "canonical_urn", flat=True
        )
    )
    reused_count = len(aliased_question_urns)

    return OverviewStats(
        survey_count=total_surveys,
        question_count=total_questions,
        reused_question_count=reused_count,
        variable_count=total_variables,
        category_count=total_categories,
        codelist_count=total_codelists,
        alias_count=total_aliases,
        batch_count=total_batches,
    )


@api.get("/surveys", response=list[SurveyItem], summary="List all ingested survey waves")
def list_surveys(request: Any) -> list[SurveyItem]:
    """Return all ingested surveys with variable and question counts."""
    surveys: list[SurveyItem] = []
    for su in StudyUnit.objects.all().order_by("urn"):
        var_count = InstanceVariable.objects.filter(
            datafile__study_unit=su
        ).count()
        title_str = _extract_display_text(su.label or su.name)
        surveys.append(
            SurveyItem(
                urn=su.urn,
                name=_extract_display_text(su.name) or su.urn,
                title=title_str or None,
                variable_count=var_count,
                created_at=su.created_at.isoformat() if su.created_at else None,
            )
        )
    return surveys


@api.get("/questions", response=list[QuestionItemSummary], summary="Search and filter questions")
def list_questions(
    request: Any,
    q: str = Query("", description="Keyword search across text, name, or URN"),
    reused_only: bool = Query(
        False, description="Filter for cross-survey harmonized questions only"
    ),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[QuestionItemSummary]:
    """Search questions with survey reuse badges and URN aliases."""
    qs = QuestionItem.objects.all().prefetch_related(
        "variable_associations__represented_variable__instance_variables__datafile_variables__datafile__study_unit"
    )

    # Pre-fetch all QuestionItem aliases into a lookup dict
    alias_map: dict[str, list[str]] = {}
    for a in URNAlias.objects.filter(entity_type="QuestionItem"):
        alias_map.setdefault(a.canonical_urn, []).append(a.alias_urn)

    results: list[QuestionItemSummary] = []

    for qi in qs.order_by("urn"):
        text_disp = _extract_display_text(qi.question_text) or _extract_display_text(qi.name)
        aliases = alias_map.get(qi.urn, [])

        # Collect unique surveys and variable names
        surveys_set: set[str] = set()
        var_names: list[str] = []
        iv_urns: list[str] = []

        for qv in qi.variable_associations.all():
            rv = qv.represented_variable
            if not rv:
                continue
            for iv in rv.instance_variables.all():
                iv_urns.append(iv.urn)
                vname = iv.name or iv.urn
                if isinstance(vname, list) and vname:
                    vname = vname[0].get("value", iv.urn)
                var_names.append(str(vname))
                for dfv in iv.datafile_variables.all():
                    if dfv.datafile and dfv.datafile.study_unit:
                        s_name = _extract_display_text(dfv.datafile.study_unit.name)
                        surveys_set.add(s_name)

        is_reused = len(surveys_set) > 1 or len(aliases) > 0

        if reused_only and not is_reused:
            continue

        if q:
            q_lower = q.lower()
            text_match = q_lower in text_disp.lower() or q_lower in qi.urn.lower()
            var_match = any(q_lower in vn.lower() for vn in var_names)
            if not (text_match or var_match):
                continue

        results.append(
            QuestionItemSummary(
                urn=qi.urn,
                name=_extract_display_text(qi.name) or qi.urn,
                question_text=qi.question_text,
                text_display=text_disp,
                surveys=sorted(list(surveys_set)),
                survey_count=len(surveys_set),
                variable_names=var_names,
                instance_variables=iv_urns,
                aliases=aliases,
                is_reused=is_reused,
            )
        )

    return results[offset : offset + limit]


@api.get(
    "/questions/{path:urn}/cascade",
    response=QuestionCascadeGraph,
    summary="Get full DDI Variable Cascade graph for a QuestionItem",
)
def get_question_cascade(request: Any, urn: str) -> QuestionCascadeGraph:
    """Return the complete node-link graph centered on this question."""
    urn = unquote(urn)
    qi = QuestionItem.objects.filter(urn=urn).first()
    if not qi:
        # Fallback: check if urn is an alias
        alias = URNAlias.objects.filter(alias_urn=urn).first()
        if alias:
            qi = QuestionItem.objects.filter(urn=alias.canonical_urn).first()

    if not qi:
        raise ValueError(f"QuestionItem '{urn}' not found.")

    nodes: dict[str, GraphNode] = {}
    links: list[GraphLink] = []

    q_text = _extract_display_text(qi.question_text) or _extract_display_text(qi.name)

    # 1. Central Question Node
    nodes[qi.urn] = GraphNode(
        id=qi.urn,
        label=_extract_display_text(qi.name) or "Question",
        type="QuestionItem",
        sublabel=q_text[:80] + ("..." if len(q_text) > 80 else ""),
        data={
            "urn": qi.urn,
            "question_text": qi.question_text,
            "instructions": qi.interviewer_instructions,
            "hashes": qi.hashes or {},
        },
    )

    # 2. Inbound URN Aliases
    aliases = URNAlias.objects.filter(canonical_urn=qi.urn)
    for a in aliases:
        nodes[a.alias_urn] = GraphNode(
            id=a.alias_urn,
            label=f"Alias ({a.hash_strategy})",
            type="URNAlias",
            sublabel=a.alias_urn.split(":")[-2] if ":" in a.alias_urn else a.alias_urn,
            data={"alias_urn": a.alias_urn, "strategy": a.hash_strategy, "file": a.source_file},
        )
        links.append(
            GraphLink(
                source=a.alias_urn,
                target=qi.urn,
                type="alias",
                label="aliases_to",
            )
        )

    # 3. RepresentedVariables & InstanceVariables
    for qv in qi.variable_associations.all():
        rv = qv.represented_variable
        if not rv:
            continue

        rv_label = _extract_display_text(rv.name) or "RepresentedVariable"
        nodes[rv.urn] = GraphNode(
            id=rv.urn,
            label=rv_label,
            type="RepresentedVariable",
            sublabel="Representation",
            data={"urn": rv.urn, "hashes": rv.hashes or {}},
        )
        links.append(
            GraphLink(
                source=qi.urn,
                target=rv.urn,
                type="cascade",
                label="represents",
            )
        )

        # Conceptual Variable (Upstream)
        if rv.conceptual_variable:
            cv = rv.conceptual_variable
            cv_label = _extract_display_text(cv.name) or "ConceptualVariable"
            nodes[cv.urn] = GraphNode(
                id=cv.urn,
                label=cv_label,
                type="ConceptualVariable",
                sublabel="Abstract Concept",
                data={"urn": cv.urn},
            )
            links.append(
                GraphLink(
                    source=cv.urn,
                    target=rv.urn,
                    type="concept",
                    label="concept_of",
                )
            )

        # CodeList (Response categories)
        if rv.code_list:
            cl = rv.code_list
            cl_label = _extract_display_text(cl.name) or "CodeList"

            codes_list = []
            for code in cl.codes.select_related("category").order_by("order", "code_value"):
                cat_label = ""
                cat_urn = ""
                if code.category:
                    cat_label = _extract_display_text(code.category.label) or _extract_display_text(
                        code.category.name
                    )
                    cat_urn = code.category.urn
                codes_list.append(
                    {
                        "value": str(code.code_value),
                        "label": cat_label,
                        "is_missing": code.is_missing,
                        "urn": code.urn,
                        "category_urn": cat_urn,
                    }
                )

            nodes[cl.urn] = GraphNode(
                id=cl.urn,
                label=cl_label,
                type="CodeList",
                sublabel="Code List",
                data={
                    "urn": cl.urn,
                    "description": _extract_display_text(cl.description),
                    "code_count": len(codes_list),
                    "codes": codes_list,
                },
            )
            links.append(
                GraphLink(
                    source=rv.urn,
                    target=cl.urn,
                    type="membership",
                    label="response_domain",
                )
            )

        # InstanceVariables (Downstream realizations across survey waves)
        for iv in rv.instance_variables.all():
            vname = iv.name
            if isinstance(vname, list) and vname:
                vname = vname[0].get("value", iv.urn)
            iv_label = str(vname or iv.urn)

            dfv = iv.datafile_variables.first() if hasattr(iv, "datafile_variables") else None
            study_name = "Dataset"
            if dfv and dfv.datafile and dfv.datafile.study_unit:
                study_name = _extract_display_text(dfv.datafile.study_unit.name)

            stats = dfv.statistics if dfv and dfv.statistics else {}

            nodes[iv.urn] = GraphNode(
                id=iv.urn,
                label=iv_label,
                type="InstanceVariable",
                sublabel=study_name,
                data={
                    "urn": iv.urn,
                    "study_unit": study_name,
                    "statistics": stats,
                },
            )
            links.append(
                GraphLink(
                    source=rv.urn,
                    target=iv.urn,
                    type="realization",
                    label="realized_in",
                )
            )

    return QuestionCascadeGraph(
        question_urn=qi.urn,
        question_text=q_text,
        nodes=list(nodes.values()),
        links=links,
    )


@api.get(
    "/harmonization/matrix",
    response=list[MatrixRow],
    summary="Cross-wave survey harmonization matrix",
)
def get_harmonization_matrix(
    request: Any,
    limit: int = Query(50, ge=1, le=200),
) -> list[MatrixRow]:
    """Compare question realizations side-by-side across survey waves."""
    # Build alias map
    alias_map: dict[str, list[str]] = {}
    for a in URNAlias.objects.filter(entity_type="QuestionItem"):
        alias_map.setdefault(a.canonical_urn, []).append(a.alias_urn)

    rows: list[MatrixRow] = []

    qs = QuestionItem.objects.all().prefetch_related(
        "variable_associations__represented_variable__instance_variables__datafile__study_unit"
    )

    for qi in qs.order_by("urn"):
        q_text = _extract_display_text(qi.question_text) or _extract_display_text(qi.name)
        aliases = alias_map.get(qi.urn, [])

        waves_data: dict[str, MatrixWaveEntry] = {}

        for qv in qi.variable_associations.all():
            rv = qv.represented_variable
            if not rv:
                continue
            for iv in rv.instance_variables.all():
                dfv = iv.datafile_variables.first() if hasattr(iv, "datafile_variables") else None
                su_name = "Unknown"
                df_name = None
                if dfv and dfv.datafile:
                    df_name = dfv.datafile.file_name
                    if dfv.datafile.study_unit:
                        su_name = _extract_display_text(dfv.datafile.study_unit.name)

                # Determine wave identifier (e.g. 2013, 2014, or short study name)
                wave_key = su_name
                if "2013" in su_name:
                    wave_key = "ELIPSS 2013"
                elif "2014" in su_name:
                    wave_key = "ELIPSS 2014"

                vname = iv.name
                if isinstance(vname, list) and vname:
                    vname = vname[0].get("value", iv.urn)

                waves_data[wave_key] = MatrixWaveEntry(
                    variable_name=str(vname or iv.urn),
                    instance_variable_urn=iv.urn,
                    datafile_name=df_name,
                    frequency_count=iv.frequencies.count() if hasattr(iv, "frequencies") else 0,
                )

        is_shared = len(waves_data) > 1 or len(aliases) > 0
        if is_shared:
            rows.append(
                MatrixRow(
                    canonical_urn=qi.urn,
                    question_text=q_text,
                    waves=waves_data,
                    is_shared=True,
                    aliases=aliases,
                )
            )

    return rows[:limit]


@api.get("/aliases", response=list[AliasItem], summary="List all URN aliases")
def list_aliases(
    request: Any,
    entity_type: str = Query("", description="Filter by entity type (e.g. QuestionItem, Category)"),
    limit: int = Query(100, ge=1, le=1000),
) -> list[AliasItem]:
    """Return all recorded URN aliases with canonical targets and hash strategy."""
    qs = URNAlias.objects.all()
    if entity_type:
        qs = qs.filter(entity_type=entity_type)

    items: list[AliasItem] = []
    for a in qs.order_by("-id")[:limit]:
        items.append(
            AliasItem(
                id=a.id,
                alias_urn=a.alias_urn,
                canonical_urn=a.canonical_urn,
                entity_type=a.entity_type,
                hash_strategy=a.hash_strategy,
                source_file=a.source_file,
                created_at=a.created_at.isoformat() if a.created_at else None,
            )
        )
    return items


@api.get(
    "/codelists",
    response=list[CodeListSummary],
    summary="List CodeLists with response domains, variables, and cross-survey reuse",
)
def list_codelists(
    request: Any,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    q: str = Query("", description="Search by name, URN, or code label"),
    reused_only: bool = Query(
        False, description="Filter for code lists used across multiple variables"
    ),
) -> list[CodeListSummary]:
    """Return all code lists with their response categories and variable usages."""
    qs = (
        CodeList.objects.all()
        .prefetch_related(
            "codes__category",
            "represented_variables__instance_variables__datafile_variables__datafile__study_unit",
            "represented_variables__question_associations__question_item",
        )
        .order_by("name", "urn")
    )

    results: list[CodeListSummary] = []
    q_lower = q.lower().strip()

    for cl in qs:
        cl_name = _extract_display_text(cl.name) or cl.urn
        cl_desc = _extract_display_text(cl.description)

        codes_info: list[CodeItemInfo] = []
        for code in cl.codes.all().order_by("order", "code_value"):
            cat_label = ""
            cat_urn = ""
            if code.category:
                cat_label = _extract_display_text(
                    code.category.label
                ) or _extract_display_text(code.category.name)
                cat_urn = code.category.urn
            codes_info.append(
                CodeItemInfo(
                    code_value=str(code.code_value),
                    category_label=cat_label,
                    category_urn=cat_urn,
                    is_missing=bool(code.is_missing),
                    order=code.order,
                )
            )

        # Collect variables, questions, and surveys using this CodeList
        var_names: list[str] = []
        questions_map: dict[str, str] = {}
        surveys_set: set[str] = set()

        for rv in cl.represented_variables.all():
            rv_name = _extract_display_text(rv.name) or rv.urn
            var_names.append(rv_name)
            for qa in rv.question_associations.all():
                qi = qa.question_item
                q_text = _extract_display_text(qi.question_text) or _extract_display_text(
                    qi.name
                )
                questions_map[qi.urn] = q_text

            for iv in rv.instance_variables.all():
                for dfv in iv.datafile_variables.all():
                    if dfv.datafile and dfv.datafile.study_unit:
                        s_name = _extract_display_text(dfv.datafile.study_unit.name)
                        surveys_set.add(s_name)

        is_reused = len(var_names) > 1 or len(surveys_set) > 1

        if reused_only and not is_reused:
            continue

        if q_lower:
            name_match = q_lower in cl_name.lower() or q_lower in cl.urn.lower()
            code_match = any(
                q_lower in c.category_label.lower() or q_lower in c.code_value.lower()
                for c in codes_info
            )
            var_match = any(q_lower in v.lower() for v in var_names)
            if not (name_match or code_match or var_match):
                continue

        results.append(
            CodeListSummary(
                urn=cl.urn,
                name=cl_name,
                description=cl_desc,
                code_count=len(codes_info),
                codes=codes_info,
                variable_count=len(var_names),
                variable_names=sorted(list(set(var_names))),
                questions=[
                    CodeListQuestionRef(
                        urn=u,
                        name=u.split(":")[-2] if ":" in u else u,
                        text=t,
                    )
                    for u, t in questions_map.items()
                ],
                surveys=sorted(list(surveys_set)),
                is_reused=is_reused,
            )
        )

    return results[offset : offset + limit]


@api.get(
    "/categories",
    response=list[CategorySummary],
    summary="List standardized Categories and their reuse across CodeLists",
)
def list_categories(
    request: Any,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    q: str = Query("", description="Search by category label or name"),
    reused_only: bool = Query(
        False,
        description="Filter for categories used across multiple code lists",
    ),
) -> list[CategorySummary]:
    """Return all categories with their code list memberships and survey footprints."""
    qs = (
        Category.objects.all()
        .prefetch_related(
            "code_memberships__code_list__represented_variables__instance_variables__datafile_variables__datafile__study_unit"
        )
        .order_by("name", "urn")
    )

    results: list[CategorySummary] = []
    q_lower = q.lower().strip()

    for cat in qs:
        cat_name = _extract_display_text(cat.name) or cat.urn
        cat_label = _extract_display_text(cat.label) or cat_name

        cl_refs: list[CategoryReference] = []
        surveys_set: set[str] = set()

        for cm in cat.code_memberships.all():
            if cm.code_list:
                cl_name = _extract_display_text(cm.code_list.name) or cm.code_list.urn
                cl_surveys: set[str] = set()
                for rv in cm.code_list.represented_variables.all():
                    for iv in rv.instance_variables.all():
                        for dfv in iv.datafile_variables.all():
                            if dfv.datafile and dfv.datafile.study_unit:
                                s_name = _extract_display_text(
                                    dfv.datafile.study_unit.name
                                )
                                cl_surveys.add(s_name)
                                surveys_set.add(s_name)
                cl_refs.append(
                    CategoryReference(
                        code_list_urn=cm.code_list.urn,
                        code_list_name=cl_name,
                        code_value=str(cm.code_value),
                        is_missing=bool(cm.is_missing),
                        surveys=sorted(list(cl_surveys)),
                    )
                )

        is_reused = len(cl_refs) > 1 or len(surveys_set) > 1

        if reused_only and not is_reused:
            continue

        if q_lower:
            text_match = (
                q_lower in cat_label.lower()
                or q_lower in cat_name.lower()
                or q_lower in cat.urn.lower()
            )
            cl_match = any(q_lower in cr.code_list_name.lower() for cr in cl_refs)
            if not (text_match or cl_match):
                continue

        results.append(
            CategorySummary(
                urn=cat.urn,
                name=cat_name,
                label=cat.label,
                label_display=cat_label,
                is_missing=bool(cat.is_missing),
                codelist_count=len(cl_refs),
                codelists=cl_refs,
                surveys=sorted(list(surveys_set)),
                is_reused=is_reused,
            )
        )

    return results[offset : offset + limit]


@api.get(
    "/codelists/{path:urn}",
    response=CodeListSummary,
    summary="Get single CodeList detail by URN",
)
def get_codelist(request: Any, urn: str) -> CodeListSummary:
    """Return complete details for a single CodeList."""
    urn = unquote(urn)
    cl = (
        CodeList.objects.filter(urn=urn)
        .prefetch_related(
            "codes__category",
            "represented_variables__instance_variables__datafile_variables__datafile__study_unit",
            "represented_variables__question_associations__question_item",
        )
        .first()
    )
    if not cl:
        raise ValueError(f"CodeList '{urn}' not found.")

    cl_name = _extract_display_text(cl.name) or cl.urn
    cl_desc = _extract_display_text(cl.description)

    codes_info: list[CodeItemInfo] = []
    for code in cl.codes.all().order_by("order", "code_value"):
        cat_label = ""
        cat_urn = ""
        if code.category:
            cat_label = _extract_display_text(
                code.category.label
            ) or _extract_display_text(code.category.name)
            cat_urn = code.category.urn
        codes_info.append(
            CodeItemInfo(
                code_value=str(code.code_value),
                category_label=cat_label,
                category_urn=cat_urn,
                is_missing=bool(code.is_missing),
                order=code.order,
            )
        )

    var_names: list[str] = []
    questions_map: dict[str, str] = {}
    surveys_set: set[str] = set()

    for rv in cl.represented_variables.all():
        rv_name = _extract_display_text(rv.name) or rv.urn
        var_names.append(rv_name)
        for qa in rv.question_associations.all():
            qi = qa.question_item
            q_text = _extract_display_text(
                qi.question_text
            ) or _extract_display_text(qi.name)
            questions_map[qi.urn] = q_text

        for iv in rv.instance_variables.all():
            for dfv in iv.datafile_variables.all():
                if dfv.datafile and dfv.datafile.study_unit:
                    s_name = _extract_display_text(dfv.datafile.study_unit.name)
                    surveys_set.add(s_name)

    is_reused = len(var_names) > 1 or len(surveys_set) > 1

    return CodeListSummary(
        urn=cl.urn,
        name=cl_name,
        description=cl_desc,
        code_count=len(codes_info),
        codes=codes_info,
        variable_count=len(var_names),
        variable_names=sorted(list(set(var_names))),
        questions=[
            CodeListQuestionRef(
                urn=u,
                name=u.split(":")[-2] if ":" in u else u,
                text=t,
            )
            for u, t in questions_map.items()
        ],
        surveys=sorted(list(surveys_set)),
        is_reused=is_reused,
    )


@api.get(
    "/categories/{path:urn}",
    response=CategorySummary,
    summary="Get single Category detail by URN",
)
def get_category(request: Any, urn: str) -> CategorySummary:
    """Return complete details for a single Category."""
    urn = unquote(urn)
    cat = (
        Category.objects.filter(urn=urn)
        .prefetch_related(
            "code_memberships__code_list__represented_variables__instance_variables__datafile_variables__datafile__study_unit"
        )
        .first()
    )
    if not cat:
        raise ValueError(f"Category '{urn}' not found.")

    cat_name = _extract_display_text(cat.name) or cat.urn
    cat_label = _extract_display_text(cat.label) or cat_name

    cl_refs: list[CategoryReference] = []
    surveys_set: set[str] = set()

    for cm in cat.code_memberships.all():
        if cm.code_list:
            cl_name = _extract_display_text(cm.code_list.name) or cm.code_list.urn
            cl_surveys: set[str] = set()
            for rv in cm.code_list.represented_variables.all():
                for iv in rv.instance_variables.all():
                    for dfv in iv.datafile_variables.all():
                        if dfv.datafile and dfv.datafile.study_unit:
                            s_name = _extract_display_text(
                                dfv.datafile.study_unit.name
                            )
                            cl_surveys.add(s_name)
                            surveys_set.add(s_name)

            cl_refs.append(
                CategoryReference(
                    code_list_urn=cm.code_list.urn,
                    code_list_name=cl_name,
                    code_value=str(cm.code_value),
                    is_missing=bool(cm.is_missing),
                    surveys=sorted(list(cl_surveys)),
                )
            )

    is_reused = len(cl_refs) > 1 or len(surveys_set) > 1

    return CategorySummary(
        urn=cat.urn,
        name=cat_name,
        label=cat.label,
        label_display=cat_label,
        is_missing=bool(cat.is_missing),
        codelist_count=len(cl_refs),
        codelists=cl_refs,
        surveys=sorted(list(surveys_set)),
        is_reused=is_reused,
    )
