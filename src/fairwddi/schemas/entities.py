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
    parent_id: int | None = Field(default=None, description="Parent concept for hierarchy.")
    concept_type: str = Field(default="concept", description="Type (domain, concept, etc.).")
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ConceptualVariableSchema(DDIIdentifiableSchema):
    """Schema for abstract ConceptualVariable."""

    concept_id: int | None = None
    label: MultilingualText = Field(..., description="Multilingual concept label.")
    description: MultilingualText | None = Field(
        default=None, description="Multilingual description."
    )
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ============================================================================
# Representation Layer
# ============================================================================


class QuestionItemSchema(DDIIdentifiableSchema):
    """Schema for standalone reusable QuestionItem."""

    question_text: MultilingualText = Field(..., description="Multilingual literal question text.")
    pre_question_text: MultilingualText | None = Field(
        default=None,
        description="Multilingual routing preamble or introductory text.",
    )
    post_question_text: MultilingualText | None = Field(
        default=None,
        description="Multilingual post-question transition text.",
    )
    interviewer_instructions: MultilingualText | None = Field(
        default=None,
        description="Multilingual interviewer guidance.",
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
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CategorySchema(DDIIdentifiableSchema):
    """Schema for Category (response label)."""

    label: MultilingualText = Field(..., description="Multilingual response category label.")
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CategorySchemeItemSchema(BaseModel):
    """Schema for member item inside a CategoryScheme."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    category_scheme_urn: str | None = None
    category_urn: str
    order: int = 0


class CategorySchemeSchema(DDIIdentifiableSchema):
    """Schema for CategoryScheme."""

    name: MultilingualText = Field(..., description="Multilingual name for the category scheme.")
    description: MultilingualText | None = Field(
        default=None, description="Multilingual description."
    )
    items: list[CategorySchemeItemSchema] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CodeSchema(BaseModel):
    """Schema for individual Code inside a CodeList."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    code_list_urn: str | None = None
    category_urn: str
    code_value: str = Field(..., description="Numerical or text code string.")
    order: int = 0
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
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RepresentedVariableSchema(DDIIdentifiableSchema):
    """Schema for RepresentedVariable."""

    conceptual_variable_urn: str
    question_item_urn: str
    code_list_urn: str | None = None
    label: MultilingualText | None = Field(default=None, description="Multilingual short label.")
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
    created_at: datetime | None = None
    updated_at: datetime | None = None


class InstanceVariableSchema(DDIIdentifiableSchema):
    """Schema for InstanceVariable (column realization in a study dataset)."""

    study_unit_urn: str
    represented_variable_urn: str
    variable_name: str = Field(..., description="Dataset column name (e.g. q01a).")
    universe: MultilingualText | None = Field(
        default=None, description="Target population universe."
    )
    notes: MultilingualText | None = Field(default=None, description="Multilingual notes.")
    is_indexed: bool = Field(default=False, description="Elasticsearch indexing status.")
    created_at: datetime | None = None
    updated_at: datetime | None = None


class StudyUnitVariableSchema(BaseModel):
    """Schema for StudyUnit to Variable relationship junction."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    study_unit_urn: str
    instance_variable_urn: str
    order: int = 0


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
