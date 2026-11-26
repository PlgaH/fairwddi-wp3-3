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
    """Summary of a QuestionItem with origin and reuse indicators."""

    urn: str
    origin: str = "instantiated"
    name: str
    question_text: Any = None
    text_display: str
    surveys: list[str] = Field(default_factory=list)
    survey_count: int = 0
    variable_names: list[str] = Field(default_factory=list)
    instance_variables: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    derived_from: list[str] = Field(default_factory=list)
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
    origin: str = "instantiated"
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
    origin: str = "instantiated"
    name: str
    label: Any = None
    label_display: str
    is_missing: bool = False
    codelist_count: int = 0
    codelists: list[CategoryReference] = Field(default_factory=list)
    surveys: list[str] = Field(default_factory=list)
    is_reused: bool = False


class GroupMemberSummary(BaseModel):
    """Member reference inside a DDI Group."""

    resource_type: str
    urn: str
    label: str = ""


class GroupSummary(BaseModel):
    """Curated DDI Group (longitudinal series, thematic scope, etc.)."""

    urn: str
    slug: str | None = None
    name: str
    description: str = ""
    group_type: str = "custom"
    member_count: int = 0
    members: list[GroupMemberSummary] = Field(default_factory=list)


class IngestBatchSummary(BaseModel):
    """Summary of an IngestBatch import receipt."""

    id: int
    source_format: str
    file_name: str
    file_sha256: str
    status: str
    created_count: int = 0
    reused_count: int = 0
    stats: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None


class QuarantineSummary(BaseModel):
    """Summary of a MetadataQuarantine content-drift record."""

    id: int
    incoming_urn: str
    existing_urn: str | None = None
    entity_type: str
    conflict_type: str
    status: str
    source_file: str | None = None
    existing_content_hash: str | None = None
    incoming_content_hash: str
    created_at: str | None = None


class FrequencyBarItem(BaseModel):
    """Single category frequency entry for an InstanceVariable in a Datafile."""

    code_value: str
    category_label: str = ""
    is_missing: bool = False
    frequency: float = 0.0
    percentage: float | None = None
    weight: str | None = None


class DatafileOccurrence(BaseModel):
    """Physical occurrence of an InstanceVariable in a Datafile with statistics."""

    datafile_urn: str
    datafile_name: str
    study_urn: str | None = None
    study_name: str | None = None
    order: int = 0
    statistics: dict[str, Any] = Field(default_factory=dict)
    frequencies: list[FrequencyBarItem] = Field(default_factory=list)


class VariableRefItem(BaseModel):
    """Compact reference to a related Variable, Question, or CodeList."""

    urn: str
    name: str
    label: str = ""
    resource_type: str = ""
    study_name: str | None = None


class SemanticLinkInfo(BaseModel):
    """Harmonization or provenance SemanticRelationship edge."""

    predicate: str
    target_urn: str
    target_type: str = ""
    correspondence_level: str | None = None
    confidence: float | None = None


class InstanceVariableSummary(BaseModel):
    """Dataset-level InstanceVariable with cascade links, stats, and frequencies."""

    urn: str
    origin: str = "imported"
    name: str
    label: str = ""
    description: str = ""
    represented_variable_urn: str | None = None
    represented_variable_name: str | None = None
    conceptual_variable_urn: str | None = None
    conceptual_variable_name: str | None = None
    codelist_urn: str | None = None
    codelist_name: str | None = None
    questions: list[VariableRefItem] = Field(default_factory=list)
    surveys: list[str] = Field(default_factory=list)
    datafile_count: int = 0
    frequency_count: int = 0
    has_statistics: bool = False
    occurrences: list[DatafileOccurrence] = Field(default_factory=list)


class RepresentedVariableDetail(BaseModel):
    """Reusable RepresentedVariable with cascade, harmonization links, and child IVs."""

    urn: str
    origin: str = "imported"
    name: str
    label: str = ""
    description: str = ""
    conceptual_variable_urn: str | None = None
    conceptual_variable_name: str | None = None
    codelist_urn: str | None = None
    codelist_name: str | None = None
    value_representation: dict[str, Any] = Field(default_factory=dict)
    questions: list[VariableRefItem] = Field(default_factory=list)
    instance_variables: list[VariableRefItem] = Field(default_factory=list)
    surveys: list[str] = Field(default_factory=list)
    semantic_links: list[SemanticLinkInfo] = Field(default_factory=list)
    is_reused: bool = False


class ConceptualVariableSummary(BaseModel):
    """Abstract ConceptualVariable with thesaurus anchor and clustered RVs."""

    urn: str
    origin: str = "imported"
    name: str
    label: str = ""
    description: str = ""
    concept_urn: str | None = None
    concept_uri: str | None = None
    concept_vocabulary: str | None = None
    concept_label: str | None = None
    represented_variables: list[VariableRefItem] = Field(default_factory=list)
    surveys: list[str] = Field(default_factory=list)
    represented_count: int = 0


class ResourceTypeCount(BaseModel):
    """Resource type inventory count from UrnRegistry."""

    resource_type: str
    count: int


class GenericResourceSummary(BaseModel):
    """Common attributes across any DDI resource registered in UrnRegistry."""

    urn: str
    resource_type: str
    origin: str = "imported"
    name: str = ""
    label: str = ""
    description: str = ""
    scheme_urn: str | None = None
    extended_attributes: list[dict[str, Any]] = Field(default_factory=list)
    hashes: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None
