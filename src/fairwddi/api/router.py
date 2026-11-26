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
    ConceptualVariableSummary,
    DatafileOccurrence,
    FrequencyBarItem,
    GenericResourceSummary,
    GraphLink,
    GraphNode,
    GroupMemberSummary,
    GroupSummary,
    IngestBatchSummary,
    InstanceVariableSummary,
    MatrixRow,
    MatrixWaveEntry,
    OverviewStats,
    QuarantineSummary,
    QuestionCascadeGraph,
    QuestionItemSummary,
    RepresentedVariableDetail,
    RepresentedVariableUsage,
    ResourceTypeCount,
    SemanticLinkInfo,
    SurveyItem,
    VariableRefItem,
)
from fairwddi.models import (
    Category,
    CodeList,
    ConceptualVariable,
    DatafileVariableFrequency,
    Group,
    IngestBatch,
    InstanceVariable,
    MetadataQuarantine,
    QuestionItem,
    RepresentedVariable,
    SemanticRelationship,
    StudyUnit,
    URNAlias,
    UrnRegistry,
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


def _resolve_batch_urns(batch_id: int | None) -> set[str] | None:
    """Return all created/reused URNs for an IngestBatch, or None when unfiltered."""
    if batch_id is None:
        return None
    batch = IngestBatch.objects.filter(id=batch_id).first()
    if batch is None:
        return set()
    return set(batch.created_urns or []) | set(batch.reused_urns or [])


@api.get("/overview", response=OverviewStats, summary="Global bank overview and reuse statistics")
def get_overview(
    request: Any,
    study_urn: str | None = Query(None, description="Optional StudyUnit URN scope filter"),
    batch_id: int | None = Query(None, description="Optional IngestBatch ID scope filter"),
    origin: str | None = Query(
        None, description="Optional UrnRegistry origin filter (imported, generated, instantiated)"
    ),
) -> OverviewStats:
    """Return counts of surveys, questions, harmonized questions, and URN aliases."""
    batch_urns = _resolve_batch_urns(batch_id)
    origin_urns = (
        set(UrnRegistry.objects.filter(origin=origin).values_list("urn", flat=True))
        if origin
        else None
    )

    su_qs = StudyUnit.objects.all()
    q_qs = QuestionItem.objects.all()
    iv_qs = InstanceVariable.objects.all()
    cat_qs = Category.objects.all()
    cl_qs = CodeList.objects.all()

    if study_urn:
        su_qs = su_qs.filter(urn=study_urn)
        q_qs = q_qs.filter(
            variable_associations__represented_variable__instance_variables__datafile_variables__datafile__study_unit__urn=study_urn
        ).distinct()
        iv_qs = iv_qs.filter(datafile_variables__datafile__study_unit__urn=study_urn).distinct()
        cl_qs = cl_qs.filter(
            represented_variables__instance_variables__datafile_variables__datafile__study_unit__urn=study_urn
        ).distinct()
        cat_qs = cat_qs.filter(
            code_memberships__code_list__represented_variables__instance_variables__datafile_variables__datafile__study_unit__urn=study_urn
        ).distinct()

    if batch_urns is not None:
        su_qs = su_qs.filter(urn__in=batch_urns)
        q_qs = q_qs.filter(urn__in=batch_urns)
        iv_qs = iv_qs.filter(urn__in=batch_urns)
        cl_qs = cl_qs.filter(urn__in=batch_urns)
        cat_qs = cat_qs.filter(urn__in=batch_urns)

    if origin_urns is not None:
        su_qs = su_qs.filter(urn__in=origin_urns)
        q_qs = q_qs.filter(urn__in=origin_urns)
        iv_qs = iv_qs.filter(urn__in=origin_urns)
        cl_qs = cl_qs.filter(urn__in=origin_urns)
        cat_qs = cat_qs.filter(urn__in=origin_urns)

    total_surveys = su_qs.count()
    total_questions = q_qs.count()
    total_variables = iv_qs.count()
    total_categories = cat_qs.count()
    total_codelists = cl_qs.count()
    total_aliases = URNAlias.objects.count()
    total_batches = (
        1
        if (batch_id is not None and batch_urns)
        else (0 if batch_id is not None else IngestBatch.objects.count())
    )

    # Reused questions: harmonized QuestionItems with prov:wasDerivedFrom or URNAliases
    aliased_question_urns = set(
        URNAlias.objects.filter(entity_type="QuestionItem").values_list("canonical_urn", flat=True)
    )
    derived_question_urns = set(
        SemanticRelationship.objects.filter(
            predicate="prov:wasDerivedFrom",
            subject_type="QuestionItem",
        ).values_list("subject_urn", flat=True)
    )
    reused_q_urns = aliased_question_urns | derived_question_urns
    if study_urn or batch_urns is not None:
        scoped_q_urns = set(q_qs.values_list("urn", flat=True))
        reused_q_urns &= scoped_q_urns
    reused_count = len(reused_q_urns)

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
        var_count = InstanceVariable.objects.filter(datafiles__study_unit=su).distinct().count()
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
    surveys.sort(key=lambda s: (s.title or s.name or s.urn).lower())
    return surveys


@api.get("/questions", response=list[QuestionItemSummary], summary="Search and filter questions")
def list_questions(
    request: Any,
    q: str = Query("", description="Keyword search across text, name, or URN"),
    reused_only: bool = Query(
        False,
        description="Filter for reused questions (multiple variables, surveys, or aliases)",
    ),
    study_urn: str | None = Query(None, description="Optional StudyUnit URN scope filter"),
    batch_id: int | None = Query(None, description="Optional IngestBatch ID scope filter"),
    origin: str | None = Query(None, description="Optional UrnRegistry origin filter"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[QuestionItemSummary]:
    """Search questions with survey reuse badges and URN aliases."""
    qs = QuestionItem.objects.all().prefetch_related(
        "variable_associations__represented_variable__instance_variables__datafile_variables__datafile__study_unit"
    )
    if study_urn:
        qs = qs.filter(
            variable_associations__represented_variable__instance_variables__datafile_variables__datafile__study_unit__urn=study_urn
        ).distinct()
    batch_urns = _resolve_batch_urns(batch_id)
    if batch_urns is not None:
        qs = qs.filter(urn__in=batch_urns)

    origin_map = dict(UrnRegistry.objects.values_list("urn", "origin"))

    # Pre-fetch all QuestionItem aliases and prov:wasDerivedFrom lineage links
    alias_map: dict[str, list[str]] = {}
    for a in URNAlias.objects.filter(entity_type="QuestionItem"):
        alias_map.setdefault(a.canonical_urn, []).append(a.alias_urn)

    derived_map: dict[str, list[str]] = {}
    for rel in SemanticRelationship.objects.filter(
        predicate="prov:wasDerivedFrom", subject_type="QuestionItem"
    ):
        derived_map.setdefault(rel.subject_urn, []).append(rel.object_urn)

    results: list[QuestionItemSummary] = []

    for qi in qs.order_by("urn"):
        text_disp = _extract_display_text(qi.question_text) or _extract_display_text(qi.name)
        aliases = alias_map.get(qi.urn, [])
        derived_from = derived_map.get(qi.urn, [])

        # Collect unique surveys, represented variables, and instance variable names
        surveys_set: set[str] = set()
        rv_urns: set[str] = set()
        var_names: list[str] = []
        iv_urns: list[str] = []

        for qv in qi.variable_associations.all():
            rv = qv.represented_variable
            if not rv:
                continue
            rv_urns.add(rv.urn)
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

        is_reused = (
            len(rv_urns) > 1
            or len(set(iv_urns)) > 1
            or len(surveys_set) > 1
            or len(aliases) > 0
            or len(derived_from) > 0
        )

        if reused_only and not is_reused:
            continue

        if origin and origin_map.get(qi.urn, "instantiated") != origin:
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
                origin=origin_map.get(qi.urn, "instantiated"),
                name=_extract_display_text(qi.name) or qi.urn,
                question_text=qi.question_text,
                text_display=text_disp,
                surveys=sorted(list(surveys_set)),
                survey_count=len(surveys_set),
                variable_names=var_names,
                instance_variables=iv_urns,
                aliases=aliases,
                derived_from=derived_from,
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

    origin_map = dict(UrnRegistry.objects.values_list("urn", "origin"))

    # 1. Central Question Node
    nodes[qi.urn] = GraphNode(
        id=qi.urn,
        label=_extract_display_text(qi.name) or "Question",
        type="QuestionItem",
        sublabel=q_text[:80] + ("..." if len(q_text) > 80 else ""),
        data={
            "urn": qi.urn,
            "origin": origin_map.get(qi.urn, "instantiated"),
            "question_text": qi.question_text,
            "instructions": qi.interviewer_instructions,
            "hashes": qi.hashes or {},
        },
    )

    # 2. Lineage via prov:wasDerivedFrom (both constituent imported sources & harmonized parents)
    for rel in SemanticRelationship.objects.filter(
        subject_urn=qi.urn, predicate="prov:wasDerivedFrom"
    ):
        src_qi = QuestionItem.objects.filter(urn=rel.object_urn).first()
        src_label = _extract_display_text(src_qi.name) if src_qi else rel.object_urn.split(":")[-2]
        src_text = (_extract_display_text(src_qi.question_text) or "") if src_qi else ""
        nodes[rel.object_urn] = GraphNode(
            id=rel.object_urn,
            label=src_label or rel.object_urn,
            type="QuestionItem",
            sublabel=f"[{origin_map.get(rel.object_urn, 'imported')}] {src_text[:60]}",
            data={
                "urn": rel.object_urn,
                "origin": origin_map.get(rel.object_urn, "imported"),
                "question_text": src_qi.question_text if src_qi else None,
            },
        )
        links.append(
            GraphLink(
                source=qi.urn,
                target=rel.object_urn,
                type="lineage",
                label="prov:wasDerivedFrom",
            )
        )

    for rel in SemanticRelationship.objects.filter(
        object_urn=qi.urn, predicate="prov:wasDerivedFrom"
    ):
        parent_qi = QuestionItem.objects.filter(urn=rel.subject_urn).first()
        parent_label = (
            _extract_display_text(parent_qi.name) if parent_qi else rel.subject_urn.split(":")[-2]
        )
        parent_text = (_extract_display_text(parent_qi.question_text) or "") if parent_qi else ""
        nodes[rel.subject_urn] = GraphNode(
            id=rel.subject_urn,
            label=parent_label or rel.subject_urn,
            type="QuestionItem",
            sublabel=f"[{origin_map.get(rel.subject_urn, 'generated')}] {parent_text[:60]}",
            data={
                "urn": rel.subject_urn,
                "origin": origin_map.get(rel.subject_urn, "generated"),
                "question_text": parent_qi.question_text if parent_qi else None,
            },
        )
        links.append(
            GraphLink(
                source=rel.subject_urn,
                target=qi.urn,
                type="lineage",
                label="prov:wasDerivedFrom",
            )
        )

    # 3. Inbound URN Aliases
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


def _build_codelist_summary(cl: CodeList) -> CodeListSummary:
    """Build a complete summary of a CodeList and its variable cascade footprint."""
    cl_name = _extract_display_text(cl.name) or cl.urn
    cl_desc = _extract_display_text(cl.description)

    codes_info: list[CodeItemInfo] = []
    for code in cl.codes.all().order_by("order", "code_value"):
        cat_label = ""
        cat_urn = ""
        if code.category:
            cat_label = _extract_display_text(code.category.label) or _extract_display_text(
                code.category.name
            )
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

    rv_usages: list[RepresentedVariableUsage] = []
    var_names: list[str] = []
    questions_map: dict[str, str] = {}
    surveys_set: set[str] = set()

    for rv in cl.represented_variables.all().order_by("urn"):
        rv_name = _extract_display_text(rv.name) or rv.urn
        rv_label = _extract_display_text(rv.label)
        var_names.append(rv_name)

        q_urn: str | None = None
        q_name: str | None = None
        q_text: str | None = None
        for qa in rv.question_associations.all():
            qi = qa.question_item
            q_urn = qi.urn
            q_name = _extract_display_text(qi.name) or (
                qi.urn.split(":")[-2] if ":" in qi.urn else qi.urn
            )
            q_text = _extract_display_text(qi.question_text) or _extract_display_text(qi.name)
            questions_map[qi.urn] = q_text
            break

        rv_surveys: set[str] = set()
        iv_names: list[str] = []
        for iv in rv.instance_variables.all().order_by("urn"):
            iv_name = _extract_display_text(iv.name) or iv.urn
            iv_names.append(iv_name)
            for dfv in iv.datafile_variables.all():
                if dfv.datafile and dfv.datafile.study_unit:
                    s_name = _extract_display_text(dfv.datafile.study_unit.name)
                    surveys_set.add(s_name)
                    rv_surveys.add(s_name)

        rv_usages.append(
            RepresentedVariableUsage(
                urn=rv.urn,
                name=rv_name,
                label=rv_label if rv_label and rv_label != rv_name else None,
                question_urn=q_urn,
                question_name=q_name,
                question_text=q_text,
                instance_variables=sorted(list(set(iv_names))),
                surveys=sorted(list(rv_surveys)),
            )
        )

    is_reused = len(var_names) > 1 or len(surveys_set) > 1
    cl_origin = (
        UrnRegistry.objects.filter(urn=cl.urn).values_list("origin", flat=True).first()
        or "instantiated"
    )

    return CodeListSummary(
        urn=cl.urn,
        origin=cl_origin,
        name=cl_name,
        description=cl_desc,
        code_count=len(codes_info),
        codes=codes_info,
        variable_count=len(var_names),
        variable_names=sorted(list(set(var_names))),
        represented_variables=rv_usages,
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
    study_urn: str | None = Query(None, description="Optional StudyUnit URN scope filter"),
    batch_id: int | None = Query(None, description="Optional IngestBatch ID scope filter"),
    origin: str | None = Query(None, description="Optional UrnRegistry origin filter"),
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
    if study_urn:
        qs = qs.filter(
            represented_variables__instance_variables__datafile_variables__datafile__study_unit__urn=study_urn
        ).distinct()
    batch_urns = _resolve_batch_urns(batch_id)
    if batch_urns is not None:
        qs = qs.filter(urn__in=batch_urns)

    results: list[CodeListSummary] = []
    q_lower = q.lower().strip() if isinstance(q, str) else ""
    is_reused_filter = reused_only if isinstance(reused_only, bool) else False
    limit_val = limit if isinstance(limit, int) else 100
    offset_val = offset if isinstance(offset, int) else 0

    for cl in qs:
        summary = _build_codelist_summary(cl)

        if is_reused_filter and not summary.is_reused:
            continue

        if origin and summary.origin != origin:
            continue

        if q_lower:
            name_match = q_lower in summary.name.lower() or q_lower in summary.urn.lower()
            code_match = any(
                q_lower in c.category_label.lower() or q_lower in c.code_value.lower()
                for c in summary.codes
            )
            var_match = any(q_lower in v.lower() for v in summary.variable_names)
            if not (name_match or code_match or var_match):
                continue

        results.append(summary)

    return results[offset_val : offset_val + limit_val]


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
    study_urn: str | None = Query(None, description="Optional StudyUnit URN scope filter"),
    batch_id: int | None = Query(None, description="Optional IngestBatch ID scope filter"),
    origin: str | None = Query(None, description="Optional UrnRegistry origin filter"),
) -> list[CategorySummary]:
    """Return all categories with their code list memberships and survey footprints."""
    qs = (
        Category.objects.all()
        .prefetch_related(
            "code_memberships__code_list__represented_variables__instance_variables__datafile_variables__datafile__study_unit"
        )
        .order_by("name", "urn")
    )
    if study_urn:
        qs = qs.filter(
            code_memberships__code_list__represented_variables__instance_variables__datafile_variables__datafile__study_unit__urn=study_urn
        ).distinct()
    batch_urns = _resolve_batch_urns(batch_id)
    if batch_urns is not None:
        qs = qs.filter(urn__in=batch_urns)

    results: list[CategorySummary] = []
    q_lower = q.lower().strip()

    origin_map = dict(UrnRegistry.objects.values_list("urn", "origin"))

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
                                s_name = _extract_display_text(dfv.datafile.study_unit.name)
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

        if origin and origin_map.get(cat.urn, "instantiated") != origin:
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
                origin=origin_map.get(cat.urn, "instantiated"),
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

    return _build_codelist_summary(cl)


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
                            s_name = _extract_display_text(dfv.datafile.study_unit.name)
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
    cat_origin = (
        UrnRegistry.objects.filter(urn=cat.urn).values_list("origin", flat=True).first()
        or "instantiated"
    )

    return CategorySummary(
        urn=cat.urn,
        origin=cat_origin,
        name=cat_name,
        label=cat.label,
        label_display=cat_label,
        is_missing=bool(cat.is_missing),
        codelist_count=len(cl_refs),
        codelists=cl_refs,
        surveys=sorted(list(surveys_set)),
        is_reused=is_reused,
    )


@api.get(
    "/groups",
    response=list[GroupSummary],
    summary="List curated DDI Groups",
)
def list_groups_api(
    request: Any,
    group_type: str | None = Query(None, description="Filter by group_type"),
    q: str | None = Query(None, description="Filter by slug, name, or URN"),
    limit: int = Query(100, ge=1, le=500),
) -> list[GroupSummary]:
    """Return curated DDI Groups with their slugs, types, and member references."""
    qs = Group.objects.all().order_by("slug", "urn")
    if group_type:
        qs = qs.filter(group_type=group_type)

    results: list[GroupSummary] = []
    q_lower = q.lower().strip() if q else None
    for grp in qs:
        name_str = _extract_display_text(grp.name) or grp.slug or grp.urn
        desc_str = _extract_display_text(grp.description)
        if q_lower:
            hay = f"{grp.slug or ''} {name_str} {grp.urn} {grp.group_type}".lower()
            if q_lower not in hay:
                continue
        members = [
            GroupMemberSummary(
                resource_type=str(ref.get("resource_type", "Resource")),
                urn=str(ref.get("urn", "")),
                label=str(ref.get("label", "")),
            )
            for ref in (grp.references or [])
            if isinstance(ref, dict) and ref.get("urn")
        ]
        results.append(
            GroupSummary(
                urn=grp.urn,
                slug=grp.slug,
                name=name_str,
                description=desc_str,
                group_type=grp.group_type or "custom",
                member_count=len(members),
                members=members,
            )
        )
        if len(results) >= limit:
            break
    return results


@api.get(
    "/batches",
    response=list[IngestBatchSummary],
    summary="List IngestBatch import receipts",
)
def list_batches_api(
    request: Any,
    status: str | None = Query(None, description="Filter by batch status"),
    limit: int = Query(100, ge=1, le=500),
) -> list[IngestBatchSummary]:
    """Return recent IngestBatch receipts ordered newest first."""
    qs = IngestBatch.objects.all().order_by("-id")
    if status:
        qs = qs.filter(status=status)

    return [
        IngestBatchSummary(
            id=b.id,
            source_format=b.source_format,
            file_name=b.file_name,
            file_sha256=b.file_sha256,
            status=b.status,
            created_count=len(b.created_urns or []),
            reused_count=len(b.reused_urns or []),
            stats=b.stats or {},
            created_at=b.created_at.isoformat() if b.created_at else None,
        )
        for b in qs[:limit]
    ]


@api.get(
    "/quarantine",
    response=list[QuarantineSummary],
    summary="List MetadataQuarantine drift records",
)
def list_quarantine_api(
    request: Any,
    status: str | None = Query(None, description="Filter by quarantine status"),
    limit: int = Query(100, ge=1, le=500),
) -> list[QuarantineSummary]:
    """Return MetadataQuarantine records ordered newest first."""
    qs = MetadataQuarantine.objects.all().order_by("-id")
    if status == "pending":
        qs = qs.filter(resolution__isnull=True)
    elif status:
        qs = qs.filter(resolution=status)

    return [
        QuarantineSummary(
            id=q_rec.id,
            incoming_urn=q_rec.incoming_urn,
            existing_urn=q_rec.existing_urn,
            entity_type=q_rec.entity_type,
            conflict_type=q_rec.conflict_type,
            status=q_rec.resolution or "pending",
            source_file=q_rec.source_file,
            existing_content_hash=q_rec.existing_content_hash,
            incoming_content_hash=q_rec.incoming_content_hash,
            created_at=q_rec.created_at.isoformat() if q_rec.created_at else None,
        )
        for q_rec in qs[:limit]
    ]


def _build_instance_variable_summary(
    iv: InstanceVariable,
    origin_map: dict[str, str],
    include_occurrences: bool = False,
) -> InstanceVariableSummary:
    """Build an InstanceVariableSummary with cascade references and optional stats/frequencies."""
    iv_name = _extract_display_text(iv.name) or iv.urn
    iv_label = _extract_display_text(iv.label)
    iv_desc = _extract_display_text(iv.description)

    rv = iv.represented_variable
    rv_urn = rv.urn if rv else None
    rv_name = (_extract_display_text(rv.name) or rv.urn) if rv else None
    cv = rv.conceptual_variable if rv else None
    cv_urn = cv.urn if cv else None
    cv_name = (_extract_display_text(cv.name) or cv.urn) if cv else None
    cl = rv.code_list if rv else None
    cl_urn = cl.urn if cl else None
    cl_name = (_extract_display_text(cl.name) or cl.urn) if cl else None

    code_label_map: dict[str, tuple[str, bool]] = {}
    if cl is not None and include_occurrences:
        for ci in cl.codes.all():
            cat_lbl = (
                _extract_display_text(ci.category.label or ci.category.name) if ci.category else ""
            )
            code_label_map[str(ci.code_value)] = (cat_lbl, bool(ci.is_missing))

    questions: list[VariableRefItem] = []
    if rv is not None:
        for qv in rv.question_associations.all():
            qi = qv.question_item
            if qi:
                questions.append(
                    VariableRefItem(
                        urn=qi.urn,
                        name=_extract_display_text(qi.name) or qi.urn,
                        label=_extract_display_text(qi.question_text) or "",
                        resource_type="QuestionItem",
                    )
                )

    surveys_set: set[str] = set()
    df_vars = list(iv.datafile_variables.all())
    has_stats = any(bool(dfv.statistics) for dfv in df_vars)

    freqs_by_df: dict[str, list[DatafileVariableFrequency]] = {}
    freq_total_count = 0
    for f_row in iv.frequencies.all():
        freqs_by_df.setdefault(f_row.datafile_id, []).append(f_row)
        freq_total_count += 1
    if freq_total_count > 0:
        has_stats = True

    occurrences: list[DatafileOccurrence] = []
    for dfv in df_vars:
        df = dfv.datafile
        su = df.study_unit if df else None
        su_name = _extract_display_text(su.name) if su else None
        if su_name:
            surveys_set.add(su_name)
        if include_occurrences and df is not None:
            raw_freqs = freqs_by_df.get(df.urn, [])
            valid_sum = sum(
                f.frequency
                for f in raw_freqs
                if not code_label_map.get(str(f.code_value), ("", False))[1]
            )
            denom = valid_sum if valid_sum > 0 else sum(f.frequency for f in raw_freqs)
            freq_items = [
                FrequencyBarItem(
                    code_value=str(f.code_value),
                    category_label=code_label_map.get(str(f.code_value), ("", False))[0],
                    is_missing=code_label_map.get(str(f.code_value), ("", False))[1],
                    frequency=float(f.frequency),
                    percentage=round((float(f.frequency) / denom) * 100.0, 2)
                    if denom > 0
                    else None,
                    weight=f.weight,
                )
                for f in raw_freqs
            ]
            occurrences.append(
                DatafileOccurrence(
                    datafile_urn=df.urn,
                    datafile_name=df.name or df.urn,
                    study_urn=su.urn if su else None,
                    study_name=su_name,
                    order=dfv.order,
                    statistics=dfv.statistics or {},
                    frequencies=freq_items,
                )
            )

    return InstanceVariableSummary(
        urn=iv.urn,
        origin=origin_map.get(iv.urn, "imported"),
        name=iv_name,
        label=iv_label,
        description=iv_desc,
        represented_variable_urn=rv_urn,
        represented_variable_name=rv_name,
        conceptual_variable_urn=cv_urn,
        conceptual_variable_name=cv_name,
        codelist_urn=cl_urn,
        codelist_name=cl_name,
        questions=questions,
        surveys=sorted(surveys_set),
        datafile_count=len(df_vars),
        frequency_count=freq_total_count,
        has_statistics=has_stats,
        occurrences=occurrences,
    )


@api.get(
    "/variables/instance",
    response=list[InstanceVariableSummary],
    summary="List InstanceVariables with datafile/statistics indicators",
)
def list_instance_variables(
    request: Any,
    q: str = Query("", description="Search by name, label, or URN"),
    has_stats: bool = Query(False, description="Only variables with statistics or frequencies"),
    study_urn: str | None = Query(None, description="Optional StudyUnit URN scope filter"),
    batch_id: int | None = Query(None, description="Optional IngestBatch ID scope filter"),
    origin: str | None = Query(None, description="Optional UrnRegistry origin filter"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[InstanceVariableSummary]:
    """List dataset-level InstanceVariables with optional study/batch and stats filters."""
    qs = (
        InstanceVariable.objects.all()
        .select_related(
            "represented_variable__conceptual_variable",
            "represented_variable__code_list",
        )
        .prefetch_related(
            "represented_variable__question_associations__question_item",
            "datafile_variables__datafile__study_unit",
            "frequencies",
        )
        .order_by("name", "urn")
    )
    if study_urn:
        qs = qs.filter(datafile_variables__datafile__study_unit__urn=study_urn).distinct()
    batch_urns = _resolve_batch_urns(batch_id)
    if batch_urns is not None:
        qs = qs.filter(urn__in=batch_urns)

    origin_map = dict(UrnRegistry.objects.values_list("urn", "origin"))
    q_lower = q.lower().strip()
    results: list[InstanceVariableSummary] = []

    for iv in qs:
        summary = _build_instance_variable_summary(iv, origin_map, include_occurrences=False)
        if has_stats and not summary.has_statistics:
            continue
        if origin and summary.origin != origin:
            continue
        if q_lower:
            hay = (
                f"{summary.name} {summary.label} {summary.urn} {summary.codelist_name or ''}"
            ).lower()
            if q_lower not in hay:
                continue
        results.append(summary)

    return results[offset : offset + limit]


@api.get(
    "/variables/instance/{path:urn}",
    response=InstanceVariableSummary,
    summary="Get single InstanceVariable detail with statistics and frequencies",
)
def get_instance_variable(request: Any, urn: str) -> InstanceVariableSummary:
    """Return full InstanceVariable detail including Datafile statistics and frequency bars."""
    urn = unquote(urn)
    iv = (
        InstanceVariable.objects.filter(urn=urn)
        .select_related(
            "represented_variable__conceptual_variable",
            "represented_variable__code_list",
        )
        .prefetch_related(
            "represented_variable__code_list__codes__category",
            "represented_variable__question_associations__question_item",
            "datafile_variables__datafile__study_unit",
            "frequencies",
        )
        .first()
    )
    if not iv:
        raise ValueError(f"InstanceVariable '{urn}' not found.")
    origin_map = dict(UrnRegistry.objects.filter(urn=urn).values_list("urn", "origin"))
    return _build_instance_variable_summary(iv, origin_map, include_occurrences=True)


def _build_represented_variable_detail(
    rv: RepresentedVariable,
    origin_map: dict[str, str],
    links_by_subject: dict[str, list[SemanticLinkInfo]],
) -> RepresentedVariableDetail:
    """Build a RepresentedVariableDetail with cascade, children, and harmonization links."""
    rv_name = _extract_display_text(rv.name) or rv.urn
    rv_label = _extract_display_text(rv.label)
    rv_desc = _extract_display_text(rv.description)
    cv = rv.conceptual_variable
    cl = rv.code_list

    questions = [
        VariableRefItem(
            urn=qv.question_item.urn,
            name=_extract_display_text(qv.question_item.name) or qv.question_item.urn,
            label=_extract_display_text(qv.question_item.question_text) or "",
            resource_type="QuestionItem",
        )
        for qv in rv.question_associations.all()
        if qv.question_item
    ]

    ivs: list[VariableRefItem] = []
    surveys_set: set[str] = set()
    for iv in rv.instance_variables.all():
        iv_study: str | None = None
        for dfv in iv.datafile_variables.all():
            if dfv.datafile and dfv.datafile.study_unit:
                s_name = _extract_display_text(dfv.datafile.study_unit.name)
                if s_name:
                    surveys_set.add(s_name)
                    iv_study = iv_study or s_name
        ivs.append(
            VariableRefItem(
                urn=iv.urn,
                name=_extract_display_text(iv.name) or iv.urn,
                label=_extract_display_text(iv.label) or "",
                resource_type="InstanceVariable",
                study_name=iv_study,
            )
        )

    sem_links = links_by_subject.get(rv.urn, [])
    is_reused = len(ivs) > 1 or len(surveys_set) > 1 or len(sem_links) > 0

    return RepresentedVariableDetail(
        urn=rv.urn,
        origin=origin_map.get(rv.urn, "imported"),
        name=rv_name,
        label=rv_label,
        description=rv_desc,
        conceptual_variable_urn=cv.urn if cv else None,
        conceptual_variable_name=(_extract_display_text(cv.name) or cv.urn) if cv else None,
        codelist_urn=cl.urn if cl else None,
        codelist_name=(_extract_display_text(cl.name) or cl.urn) if cl else None,
        value_representation=rv.value_representation
        if isinstance(rv.value_representation, dict)
        else {},
        questions=questions,
        instance_variables=ivs,
        surveys=sorted(surveys_set),
        semantic_links=sem_links,
        is_reused=is_reused,
    )


def _fetch_rv_semantic_links(urns: list[str] | None = None) -> dict[str, list[SemanticLinkInfo]]:
    """Fetch outgoing SemanticRelationship links for RepresentedVariables."""
    qs = SemanticRelationship.objects.filter(subject_type="RepresentedVariable")
    if urns is not None:
        qs = qs.filter(subject_urn__in=urns)
    out: dict[str, list[SemanticLinkInfo]] = {}
    for rel in qs:
        lvl = None
        conf = None
        for attr in rel.extended_attributes or []:
            if isinstance(attr, dict):
                if attr.get("type") == "correspondence_level":
                    lvl = str(attr.get("value"))
                elif attr.get("type") == "confidence":
                    try:
                        conf = float(attr.get("value"))
                    except (TypeError, ValueError):
                        conf = None
        out.setdefault(rel.subject_urn, []).append(
            SemanticLinkInfo(
                predicate=rel.predicate,
                target_urn=rel.object_urn,
                target_type=rel.object_type or "",
                correspondence_level=lvl,
                confidence=conf,
            )
        )
    return out


@api.get(
    "/variables/represented",
    response=list[RepresentedVariableDetail],
    summary="List RepresentedVariables with cascade and harmonization links",
)
def list_represented_variables(
    request: Any,
    q: str = Query("", description="Search by name, label, or URN"),
    reused_only: bool = Query(
        False, description="Only variables reused across >1 IV/study or linked"
    ),
    has_codelist: bool = Query(False, description="Only variables with a linked CodeList"),
    study_urn: str | None = Query(None, description="Optional StudyUnit URN scope filter"),
    batch_id: int | None = Query(None, description="Optional IngestBatch ID scope filter"),
    origin: str | None = Query(None, description="Optional UrnRegistry origin filter"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[RepresentedVariableDetail]:
    """List reusable RepresentedVariables with optional study/batch and reuse filters."""
    qs = (
        RepresentedVariable.objects.all()
        .select_related("conceptual_variable", "code_list")
        .prefetch_related(
            "question_associations__question_item",
            "instance_variables__datafile_variables__datafile__study_unit",
        )
        .order_by("name", "urn")
    )
    if has_codelist:
        qs = qs.filter(code_list__isnull=False)
    if study_urn:
        qs = qs.filter(
            instance_variables__datafile_variables__datafile__study_unit__urn=study_urn
        ).distinct()
    batch_urns = _resolve_batch_urns(batch_id)
    if batch_urns is not None:
        qs = qs.filter(urn__in=batch_urns)

    origin_map = dict(UrnRegistry.objects.values_list("urn", "origin"))
    links_map = _fetch_rv_semantic_links()
    q_lower = q.lower().strip()
    results: list[RepresentedVariableDetail] = []

    for rv in qs:
        detail = _build_represented_variable_detail(rv, origin_map, links_map)
        if reused_only and not detail.is_reused:
            continue
        if origin and detail.origin != origin:
            continue
        if q_lower:
            hay = f"{detail.name} {detail.label} {detail.urn} {detail.codelist_name or ''}".lower()
            if q_lower not in hay:
                continue
        results.append(detail)

    return results[offset : offset + limit]


@api.get(
    "/variables/represented/{path:urn}",
    response=RepresentedVariableDetail,
    summary="Get single RepresentedVariable detail by URN",
)
def get_represented_variable(request: Any, urn: str) -> RepresentedVariableDetail:
    """Return complete detail for a single RepresentedVariable."""
    urn = unquote(urn)
    rv = (
        RepresentedVariable.objects.filter(urn=urn)
        .select_related("conceptual_variable", "code_list")
        .prefetch_related(
            "question_associations__question_item",
            "instance_variables__datafile_variables__datafile__study_unit",
        )
        .first()
    )
    if not rv:
        raise ValueError(f"RepresentedVariable '{urn}' not found.")
    origin_map = dict(UrnRegistry.objects.filter(urn=urn).values_list("urn", "origin"))
    links_map = _fetch_rv_semantic_links([urn])
    return _build_represented_variable_detail(rv, origin_map, links_map)


def _build_conceptual_variable_summary(
    cv: ConceptualVariable,
    origin_map: dict[str, str],
) -> ConceptualVariableSummary:
    """Build a ConceptualVariableSummary with Concept anchor and clustered RVs."""
    cv_name = _extract_display_text(cv.name) or cv.urn
    cv_label = _extract_display_text(cv.label)
    cv_desc = _extract_display_text(cv.description)
    concept = cv.concept

    rvs: list[VariableRefItem] = []
    surveys_set: set[str] = set()
    for rv in cv.represented_variables.all():
        for iv in rv.instance_variables.all():
            for dfv in iv.datafile_variables.all():
                if dfv.datafile and dfv.datafile.study_unit:
                    s_name = _extract_display_text(dfv.datafile.study_unit.name)
                    if s_name:
                        surveys_set.add(s_name)
        rvs.append(
            VariableRefItem(
                urn=rv.urn,
                name=_extract_display_text(rv.name) or rv.urn,
                label=_extract_display_text(rv.label) or "",
                resource_type="RepresentedVariable",
            )
        )

    return ConceptualVariableSummary(
        urn=cv.urn,
        origin=origin_map.get(cv.urn, "imported"),
        name=cv_name,
        label=cv_label,
        description=cv_desc,
        concept_urn=concept.urn if concept else None,
        concept_uri=concept.uri if concept else None,
        concept_vocabulary=concept.vocabulary if concept else None,
        concept_label=(_extract_display_text(concept.label) or concept.urn) if concept else None,
        represented_variables=rvs,
        surveys=sorted(surveys_set),
        represented_count=len(rvs),
    )


@api.get(
    "/variables/conceptual",
    response=list[ConceptualVariableSummary],
    summary="List ConceptualVariables with thesaurus anchors and clustered RVs",
)
def list_conceptual_variables(
    request: Any,
    q: str = Query("", description="Search by name, label, concept URI, or URN"),
    study_urn: str | None = Query(None, description="Optional StudyUnit URN scope filter"),
    batch_id: int | None = Query(None, description="Optional IngestBatch ID scope filter"),
    origin: str | None = Query(None, description="Optional UrnRegistry origin filter"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[ConceptualVariableSummary]:
    """List abstract ConceptualVariables with their Concept anchors and clustered RVs."""
    qs = (
        ConceptualVariable.objects.all()
        .select_related("concept")
        .prefetch_related(
            "represented_variables__instance_variables__datafile_variables__datafile__study_unit"
        )
        .order_by("name", "urn")
    )
    if study_urn:
        qs = qs.filter(
            represented_variables__instance_variables__datafile_variables__datafile__study_unit__urn=study_urn
        ).distinct()
    batch_urns = _resolve_batch_urns(batch_id)
    if batch_urns is not None:
        qs = qs.filter(urn__in=batch_urns)

    origin_map = dict(UrnRegistry.objects.values_list("urn", "origin"))
    q_lower = q.lower().strip()
    results: list[ConceptualVariableSummary] = []

    for cv in qs:
        summary = _build_conceptual_variable_summary(cv, origin_map)
        if origin and summary.origin != origin:
            continue
        if q_lower:
            hay = (
                f"{summary.name} {summary.label} {summary.urn} "
                f"{summary.concept_uri or ''} {summary.concept_label or ''}"
            ).lower()
            if q_lower not in hay:
                continue
        results.append(summary)

    return results[offset : offset + limit]


@api.get(
    "/variables/conceptual/{path:urn}",
    response=ConceptualVariableSummary,
    summary="Get single ConceptualVariable detail by URN",
)
def get_conceptual_variable(request: Any, urn: str) -> ConceptualVariableSummary:
    """Return complete detail for a single ConceptualVariable."""
    urn = unquote(urn)
    cv = (
        ConceptualVariable.objects.filter(urn=urn)
        .select_related("concept")
        .prefetch_related(
            "represented_variables__instance_variables__datafile_variables__datafile__study_unit"
        )
        .first()
    )
    if not cv:
        raise ValueError(f"ConceptualVariable '{urn}' not found.")
    origin_map = dict(UrnRegistry.objects.filter(urn=urn).values_list("urn", "origin"))
    return _build_conceptual_variable_summary(cv, origin_map)


def _serialize_generic_resource(reg: UrnRegistry, obj: Any | None) -> GenericResourceSummary:
    """Extract common DDI attributes from any concrete model instance."""
    name_val = ""
    label_val = ""
    desc_val = ""
    scheme_urn = None
    ext_attrs: list[dict[str, Any]] = []
    hashes_val: dict[str, Any] = {}
    created_at = reg.created_at.isoformat() if reg.created_at else None
    updated_at = reg.updated_at.isoformat() if reg.updated_at else None

    if obj is not None:
        raw_name = getattr(obj, "name", None)
        name_val = _extract_display_text(raw_name) or reg.urn
        raw_label = getattr(obj, "label", None) or getattr(obj, "title", None)
        label_val = _extract_display_text(raw_label)
        raw_desc = getattr(obj, "description", None)
        desc_val = _extract_display_text(raw_desc)
        scheme_urn = getattr(obj, "scheme_id", None)
        raw_ext = getattr(obj, "extended_attributes", None)
        if isinstance(raw_ext, list):
            ext_attrs = [item for item in raw_ext if isinstance(item, dict)]
        raw_hashes = getattr(obj, "hashes", None)
        if isinstance(raw_hashes, dict):
            hashes_val = raw_hashes
        obj_created = getattr(obj, "created_at", None)
        obj_updated = getattr(obj, "updated_at", None)
        if obj_created is not None:
            created_at = obj_created.isoformat()
        if obj_updated is not None:
            updated_at = obj_updated.isoformat()

    return GenericResourceSummary(
        urn=reg.urn,
        resource_type=reg.resource_type,
        origin=reg.origin,
        name=name_val or reg.urn,
        label=label_val,
        description=desc_val,
        scheme_urn=scheme_urn,
        extended_attributes=ext_attrs,
        hashes=hashes_val,
        created_at=created_at,
        updated_at=updated_at,
    )


@api.get(
    "/resources/types",
    response=list[ResourceTypeCount],
    summary="List registered DDI resource types and counts",
)
def list_resource_types(request: Any) -> list[ResourceTypeCount]:
    """Return all resource_type values in UrnRegistry with counts sorted alphabetically."""
    from django.db.models import Count

    rows = (
        UrnRegistry.objects.values("resource_type")
        .annotate(count=Count("urn"))
        .order_by("resource_type")
    )
    return [ResourceTypeCount(resource_type=r["resource_type"], count=r["count"]) for r in rows]


@api.get(
    "/resources",
    response=list[GenericResourceSummary],
    summary="Browse any DDI resource registered in UrnRegistry by type and keyword",
)
def list_generic_resources(
    request: Any,
    resource_type: str | None = Query(None, description="Filter by UrnRegistry resource_type"),
    origin: str | None = Query(None, description="Filter by UrnRegistry origin"),
    q: str = Query("", description="Search by URN, name, or label"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[GenericResourceSummary]:
    """List common attributes for registered DDI resources filtered by type and search query."""
    from django.apps import apps

    qs = UrnRegistry.objects.all().order_by("resource_type", "urn")
    if resource_type:
        qs = qs.filter(resource_type=resource_type)
    if origin:
        qs = qs.filter(origin=origin)

    reg_rows = list(qs)
    urns_by_type: dict[str, list[str]] = {}
    for r in reg_rows:
        urns_by_type.setdefault(r.resource_type, []).append(r.urn)

    obj_map: dict[str, Any] = {}
    for r_type, urns in urns_by_type.items():
        try:
            model_cls = apps.get_model("fairwddi", r_type)
            for obj in model_cls.objects.filter(urn__in=urns):
                obj_map[obj.urn] = obj
        except LookupError:
            continue

    q_lower = q.lower().strip()
    results: list[GenericResourceSummary] = []
    for r in reg_rows:
        item = _serialize_generic_resource(r, obj_map.get(r.urn))
        if q_lower:
            hay = f"{item.urn} {item.resource_type} {item.name} {item.label}".lower()
            if q_lower not in hay:
                continue
        results.append(item)

    return results[offset : offset + limit]


@api.get(
    "/resources/{path:urn}",
    response=GenericResourceSummary,
    summary="Get common attributes for any DDI resource by URN",
)
def get_generic_resource(request: Any, urn: str) -> GenericResourceSummary:
    """Return common attributes for a single registered DDI resource."""
    from django.apps import apps

    urn = unquote(urn)
    reg = UrnRegistry.objects.filter(urn=urn).first()
    if not reg:
        raise ValueError(f"Resource '{urn}' not found in UrnRegistry.")
    obj = None
    try:
        model_cls = apps.get_model("fairwddi", reg.resource_type)
        obj = model_cls.objects.filter(urn=urn).first()
    except LookupError:
        pass
    return _serialize_generic_resource(reg, obj)
