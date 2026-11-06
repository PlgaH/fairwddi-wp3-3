"""Pydantic schemas for the FAIRwDDI Ninja API layer."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class OverviewStats(BaseModel):
    """Global bank and harmonization statistics."""

    survey_count: int
    question_count: int
    reused_question_count: int
    variable_count: int
    category_count: int
    codelist_count: int
    alias_count: int
    batch_count: int


class SurveyItem(BaseModel):
    """Summary of an ingested survey study unit."""

    urn: str
    name: str
    title: str | None = None
    variable_count: int = 0
    question_count: int = 0
    created_at: str | None = None


class QuestionItemSummary(BaseModel):
    """Summary of a canonical QuestionItem with reuse indicators."""

    urn: str
    name: str
    question_text: Any = None
    text_display: str
    surveys: list[str] = Field(default_factory=list)
    survey_count: int = 0
    variable_names: list[str] = Field(default_factory=list)
    instance_variables: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    is_reused: bool = False


class GraphNode(BaseModel):
    """Node in an interactive lineage and cascade graph."""

    id: str
    label: str
    type: str  # QuestionItem, RepresentedVariable, InstanceVariable, StudyUnit, URNAlias, Concept
    sublabel: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class GraphLink(BaseModel):
    """Directed relationship between entities in the cascade graph."""

    source: str
    target: str
    type: str  # cascade, realization, alias, membership, concept
    label: str | None = None


class QuestionCascadeGraph(BaseModel):
    """Complete node-link graph payload centered on a QuestionItem."""

    question_urn: str
    question_text: str
    nodes: list[GraphNode]
    links: list[GraphLink]


class AliasItem(BaseModel):
    """URN alias crosswalk record."""

    id: int
    alias_urn: str
    canonical_urn: str
    entity_type: str
    hash_strategy: str
    source_file: str | None = None
    created_at: str | None = None


class MatrixWaveEntry(BaseModel):
    """Variable metadata for a specific survey wave."""

    variable_name: str
    instance_variable_urn: str
    datafile_name: str | None = None
    frequency_count: int = 0


class MatrixRow(BaseModel):
    """Question reuse comparison across survey waves."""

    canonical_urn: str
    question_text: str
    waves: dict[str, MatrixWaveEntry] = Field(default_factory=dict)
    is_shared: bool = False
    aliases: list[str] = Field(default_factory=list)


class CodeItemInfo(BaseModel):
    """A response code value paired with its category label."""

    code_value: str
    category_label: str
    category_urn: str
    is_missing: bool = False
    order: int = 0


class CodeListQuestionRef(BaseModel):
    """Question referencing a code list."""

    urn: str
    name: str
    text: str


class RepresentedVariableUsage(BaseModel):
    """RepresentedVariable using a CodeList, with its questions and dataset occurrences."""

    urn: str
    name: str
    label: str | None = None
    question_urn: str | None = None
    question_name: str | None = None
    question_text: str | None = None
    instance_variables: list[str] = Field(default_factory=list)
    surveys: list[str] = Field(default_factory=list)


class CodeListSummary(BaseModel):
    """Summary of a CodeList and its response domain."""

    urn: str
    name: str
    description: str | None = None
    code_count: int = 0
    codes: list[CodeItemInfo] = Field(default_factory=list)
    variable_count: int = 0
    variable_names: list[str] = Field(default_factory=list)
    represented_variables: list[RepresentedVariableUsage] = Field(default_factory=list)
    questions: list[CodeListQuestionRef] = Field(default_factory=list)
    surveys: list[str] = Field(default_factory=list)
    is_reused: bool = False


class CategoryReference(BaseModel):
    """Reference to a code list using a specific category."""

    code_list_urn: str
    code_list_name: str
    code_value: str
    is_missing: bool = False
    surveys: list[str] = Field(default_factory=list)


class CategorySummary(BaseModel):
    """Summary of a standardized Category entity."""

    urn: str
    name: str
    label: Any = None
    label_display: str
    is_missing: bool = False
    codelist_count: int = 0
    codelists: list[CategoryReference] = Field(default_factory=list)
    surveys: list[str] = Field(default_factory=list)
    is_reused: bool = False
