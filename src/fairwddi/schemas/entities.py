"""Entity-specific Pydantic v2 schemas for FAIRwDDI domain models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from fairwddi.schemas.common import DDIIdentifiableSchema, MultilingualText

# ============================================================================
# Organizational Hierarchy
# ============================================================================


class DistributorSchema(BaseModel):
    """Schema for top-level Distributor entity."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    name: str = Field(..., description="Organization name.")
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CollectionSchema(DDIIdentifiableSchema):
    """Schema for Collection (Series / Group)."""

    distributor_id: int
    name: str = Field(..., description="Series / Collection title.")
    description: MultilingualText | None = Field(
        default=None,
        description="Multilingual collection abstract/description.",
    )
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SubcollectionSchema(DDIIdentifiableSchema):
    """Schema for Subcollection (Sub-Series / SubGroup)."""

    collection_urn: str = Field(..., description="Parent Collection URN.")
    name: str = Field(..., description="Subcollection title.")
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ============================================================================
# Concept Layer
# ============================================================================


class ConceptSchema(BaseModel):
    """Schema for Concept entity from any controlled vocabulary."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    uri: str | None = Field(default=None, description="Controlled vocabulary concept URI.")
    vocabulary: str = Field(default="", description="Controlled vocabulary name or scheme.")
    notation: str | None = Field(default=None, description="Thesaurus classification code.")
    label: MultilingualText = Field(..., description="Multilingual concept label.")
    description: MultilingualText | None = Field(
        default=None, description="Multilingual description."
    )
    definition: MultilingualText | None = Field(
        default=None, description="Multilingual definition."
    )
    parent_urn: str | None = Field(default=None, description="Parent concept URN for hierarchy.")
    concept_type: str = Field(default="concept", description="Type (domain, concept, etc.).")
    extended_attributes: list[dict[str, Any]] = Field(
        default_factory=list, description="Extensible attributes list of objects."
    )
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ConceptualVariableSchema(DDIIdentifiableSchema):
    """Schema for abstract ConceptualVariable."""

    concept_urn: str | None = Field(
        default=None, description="Parent Concept URN in controlled vocabulary."
    )
    label: MultilingualText = Field(..., description="Multilingual concept label.")
    description: MultilingualText | None = Field(
        default=None, description="Multilingual description."
    )
    extended_attributes: list[dict[str, Any]] = Field(
        default_factory=list, description="Extensible attributes list of objects."
    )
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SemanticRelationshipSchema(BaseModel):
    """Schema for SemanticRelationship capturing RDF triple-like links between resources."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    subject_type: str = Field(..., description="Subject resource classification type.")
    subject_urn: str = Field(..., description="Subject canonical URN or URI.")
    predicate: str = Field(..., description="Semantic predicate (e.g. 'skos:exactMatch').")
    object_type: str = Field(..., description="Target/object resource classification type.")
    object_urn: str = Field(..., description="Target/object canonical URN or URI.")
    extended_attributes: list[dict[str, Any]] = Field(
        default_factory=list, description="Extensible attributes list of objects."
    )
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ============================================================================
# Representation Layer
# ============================================================================


class QuestionItemSchema(DDIIdentifiableSchema):
    """Schema for standalone reusable QuestionItem."""

    question_text: MultilingualText = Field(..., description="Multilingual literal question text.")
    extended_attributes: list[dict[str, Any]] = Field(
        default_factory=list, description="Extensible attributes list of objects."
    )
    created_at: datetime | None = None
    updated_at: datetime | None = None


class QuestionGroupItemSchema(BaseModel):
    """Schema for QuestionGroupItem junction."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    question_group_urn: str | None = None
    question_item_urn: str
    order: int = 0


class QuestionGroupSchema(DDIIdentifiableSchema):
    """Schema for QuestionGroup."""

    label: MultilingualText = Field(..., description="Multilingual group title.")
    description: MultilingualText | None = Field(
        default=None, description="Multilingual description."
    )
    parent_group_urn: str | None = None
    items: list[QuestionGroupItemSchema] = Field(default_factory=list)
    extended_attributes: list[dict[str, Any]] = Field(
        default_factory=list, description="Extensible attributes list of objects."
    )
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CategorySchema(DDIIdentifiableSchema):
    """Schema for Category (response label)."""

    category_scheme_urn: str | None = Field(default=None, description="Parent CategoryScheme URN.")
    label: MultilingualText = Field(..., description="Multilingual response category label.")
    parent_urn: str | None = Field(
        default=None, description="Parent Category URN for hierarchical schemes."
    )
    order: int = Field(default=0, description="Display order within category scheme.")
    is_missing: bool = Field(
        default=False, description="Whether this category represents a missing value."
    )
    extended_attributes: list[dict[str, Any]] = Field(
        default_factory=list, description="Extensible attributes list of objects."
    )
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CategorySchemeSchema(DDIIdentifiableSchema):
    """Schema for CategoryScheme."""

    name: MultilingualText = Field(..., description="Multilingual name for the category scheme.")
    description: MultilingualText | None = Field(
        default=None, description="Multilingual description."
    )
    categories: list[CategorySchema] = Field(default_factory=list)
    extended_attributes: list[dict[str, Any]] = Field(
        default_factory=list, description="Extensible attributes list of objects."
    )
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CodeSchema(DDIIdentifiableSchema):
    """Schema for individual Code inside a CodeList."""

    code_list_urn: str | None = None
    category_urn: str
    code_value: str = Field(..., description="Numerical or text code string.")
    parent_urn: str | None = Field(
        default=None, description="Parent Code URN for hierarchical code schemes."
    )
    order: int = 0
    is_missing: bool = Field(
        default=False, description="Whether this code represents a missing / non-response value."
    )
    extended_attributes: list[dict[str, Any]] = Field(
        default_factory=list, description="Extensible attributes list of objects."
    )
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CodeListSchema(DDIIdentifiableSchema):
    """Schema for CodeList entity."""

    name: MultilingualText | None = Field(default=None, description="Multilingual title.")
    description: MultilingualText | None = Field(
        default=None, description="Multilingual description."
    )
    category_scheme_urn: str | None = None
    codes: list[CodeSchema] = Field(default_factory=list)
    extended_attributes: list[dict[str, Any]] = Field(
        default_factory=list, description="Extensible attributes list of objects."
    )
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RepresentedVariableSchema(DDIIdentifiableSchema):
    """Schema for RepresentedVariable."""

    conceptual_variable_urn: str
    code_list_urn: str | None = None
    label: MultilingualText | None = Field(default=None, description="Multilingual short label.")
    extended_attributes: list[dict[str, Any]] = Field(
        default_factory=list, description="Extensible attributes list of objects."
    )
    created_at: datetime | None = None
    updated_at: datetime | None = None


class QuestionVariableSchema(BaseModel):
    """Schema for QuestionItem to RepresentedVariable relationship junction."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    question_item_urn: str
    represented_variable_urn: str
    path: str = Field(default="", description="Referencing path from question to variable.")
    order: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ============================================================================
# Instrument Layer
# ============================================================================


class InstrumentSchema(DDIIdentifiableSchema):
    """Schema for DDI-Lifecycle Instrument."""

    name: MultilingualText | None = Field(default=None, description="Technical name.")
    label: MultilingualText | None = Field(default=None, description="Human-readable title.")
    description: MultilingualText | None = Field(default=None, description="Description.")
    extended_attributes: list[dict[str, Any]] = Field(
        default_factory=list, description="Extensible attributes list of objects."
    )
    created_at: datetime | None = None
    updated_at: datetime | None = None


class InstrumentQuestionSchema(BaseModel):
    """Schema for Instrument to QuestionItem relationship junction."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    instrument_urn: str
    question_item_urn: str
    path: str = Field(default="", description="Referencing path from instrument to question.")
    order: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ============================================================================
# Dataset Layer
# ============================================================================


class StudyUnitSchema(DDIIdentifiableSchema):
    """Schema for StudyUnit (survey wave dataset)."""

    subcollection_urn: str
    title: MultilingualText = Field(..., description="Multilingual study title.")
    external_ref: str | None = Field(default=None, description="External reference or DOI.")
    year: int | None = Field(default=None, description="Survey year.")
    description: MultilingualText | None = Field(default=None, description="Multilingual abstract.")
    extended_attributes: list[dict[str, Any]] = Field(
        default_factory=list, description="Extensible attributes list of objects."
    )
    created_at: datetime | None = None
    updated_at: datetime | None = None


class InstanceVariableSchema(DDIIdentifiableSchema):
    """Schema for InstanceVariable (column realization in a study dataset)."""

    represented_variable_urn: str
    name: str = Field(..., description="Dataset column name (e.g. q01a).")
    label: MultilingualText | None = Field(default=None, description="Multilingual variable label.")
    extended_attributes: list[dict[str, Any]] = Field(
        default_factory=list, description="Extensible attributes list of objects."
    )
    created_at: datetime | None = None
    updated_at: datetime | None = None


class StudyUnitVariableSchema(BaseModel):
    """Schema for StudyUnit to Variable relationship junction."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    study_unit_urn: str
    instance_variable_urn: str
    path: str = Field(default="", description="Referencing path from study unit to variable.")
    order: int = 0


# ============================================================================
# Event Logging & Audit Trail
# ============================================================================


class EventLogSchema(BaseModel):
    """Schema for DDI resource event logs."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    urn: str = Field(..., description="Target resource canonical URN.")
    timestamp: datetime | None = None
    event_type: str = Field(..., description="Event type classification.")
    event_data: dict[str, Any] = Field(default_factory=dict, description="Event payload JSON.")


# ============================================================================
# Infrastructure, Provenance & Quarantine
# ============================================================================


class URNAliasSchema(BaseModel):
    """Schema for external URN alias mapping."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    alias_urn: str = Field(..., description="External or random source URN.")
    canonical_urn: str = Field(..., description="Canonical database URN.")
    entity_type: str = Field(..., description="DDI entity type name.")
    hash_strategy: str = Field(default="v1_strict_sha256")
    source_file: str | None = None
    created_at: datetime | None = None


class MetadataQuarantineSchema(BaseModel):
    """Schema for quarantined metadata elements."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    incoming_urn: str
    existing_urn: str | None = None
    entity_type: str
    incoming_content: dict[str, Any]
    existing_content_hash: str | None = None
    incoming_content_hash: str
    conflict_type: str
    resolution: str | None = None
    resolved_by: str | None = None
    resolved_at: datetime | None = None
    source_file: str | None = None
    import_task_id: str | None = None
    created_at: datetime | None = None


class StagedResourceNodeSchema(BaseModel):
    """Schema for Stage 1 broken-down raw element node."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    staged_import_id: int
    resource_type: str
    raw_urn: str
    raw_value: dict[str, Any]
    canonical_urn: str | None = None
    status: str = "staged"
    created_at: datetime | None = None


class StagedImportSchema(BaseModel):
    """Schema for file upload and batch import job."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    source_format: str
    file_name: str
    file_path: str | None = None
    import_options: dict[str, Any] = Field(default_factory=dict)
    total_resources: int = 0
    processed_resources: int = 0
    status: str = "staged"
    import_task_id: str | None = None
    created_at: datetime | None = None
    processed_at: datetime | None = None
    nodes: list[StagedResourceNodeSchema] = Field(default_factory=list)
