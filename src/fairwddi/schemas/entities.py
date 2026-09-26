"""Entity-specific Pydantic v2 schemas for FAIRwDDI domain models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from fairwddi.schemas.common import (
    DDIIdentifiableSchema,
    DDIResourceSchema,
    DDISchemeSchema,
    MultilingualText,
)

# ============================================================================
# Organizational Hierarchy
# ============================================================================


class OrganizationSchema(DDIResourceSchema):
    """Schema for DDI-Lifecycle Organization resource."""

    organization_type: str | None = Field(
        default=None,
        description="Organization type (e.g. 'archive', 'distributor', 'research_center').",
    )
    extended_attributes: list[dict[str, Any]] = Field(
        default_factory=list, description="Extensible attributes list of objects."
    )
    created_at: datetime | None = None
    updated_at: datetime | None = None


class GroupReferenceSchema(BaseModel):
    """Schema for resource references contained in a Group."""

    model_config = ConfigDict(from_attributes=True)

    resource_type: str = Field(
        ..., description="Target DDI entity type (e.g. 'StudyUnit', 'QuestionScheme')."
    )
    urn: str = Field(..., description="Canonical URN of the referenced resource.")


class GroupSchema(DDIResourceSchema):
    """Schema for generic Group DDI resource."""

    description: MultilingualText | None = Field(
        default=None, description="Multilingual description for the group."
    )
    group_type: str | None = Field(
        default=None,
        description=(
            "Group classification type (e.g. 'study_series', 'panel', 'thematic', 'collection')."
        ),
    )
    references: list[GroupReferenceSchema | dict[str, Any]] = Field(
        default_factory=list,
        description="List of referenced member resources with resource_type and urn.",
    )
    extended_attributes: list[dict[str, Any]] = Field(
        default_factory=list, description="Extensible attributes list of objects."
    )
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ============================================================================
# Concept Layer
# ============================================================================


class ConceptSchema(DDIIdentifiableSchema):
    """Schema for Concept entity from any controlled vocabulary."""

    scheme_urn: str | None = Field(default=None, description="Parent ConceptScheme URN.")
    uri: str | None = Field(default=None, description="Controlled vocabulary concept URI.")
    vocabulary: str | None = Field(
        default=None, description="Controlled vocabulary name or scheme."
    )
    notation: str | None = Field(default=None, description="Thesaurus classification code.")
    label: MultilingualText | None = Field(default=None, description="Multilingual concept label.")
    description: MultilingualText | None = Field(
        default=None, description="Multilingual description."
    )
    definition: MultilingualText | None = Field(
        default=None, description="Multilingual definition."
    )
    parent_urn: str | None = Field(default=None, description="Parent concept URN for hierarchy.")
    concept_type: str | None = Field(default=None, description="Type (domain, concept, etc.).")
    hashes: dict[str, Any] | None = Field(
        default=None,
        description="Unified key-value hash digests dictionary (e.g. {'sha256': '...'}).",
    )
    extended_attributes: list[dict[str, Any]] = Field(
        default_factory=list, description="Extensible attributes list of objects."
    )
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ConceptSchemeSchema(DDISchemeSchema):
    """Schema for ConceptScheme."""

    concepts: list[ConceptSchema] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ConceptualVariableSchemeSchema(DDISchemeSchema):
    """Schema for ConceptualVariableScheme."""

    conceptual_variables: list[ConceptualVariableSchema] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ConceptualVariableSchema(DDIResourceSchema):
    """Schema for abstract ConceptualVariable."""

    scheme_urn: str | None = Field(default=None, description="Parent ConceptualVariableScheme URN.")
    concept_urn: str | None = Field(
        default=None, description="Parent Concept URN in controlled vocabulary."
    )
    label: MultilingualText | None = Field(default=None, description="Multilingual concept label.")
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


class QuestionItemSchema(DDIResourceSchema):
    """Schema for standalone reusable QuestionItem."""

    name: MultilingualText = Field(default_factory=list, description="Multilingual question name.")
    scheme_urn: str | None = Field(default=None, description="Parent QuestionScheme URN.")
    code_list_urn: str | None = Field(default=None, description="Associated response CodeList URN.")
    response_domain: dict[str, Any] | None = Field(
        default=None,
        description=(
            "JSON object describing the response domain "
            "(e.g. {'type': 'code', 'code_list_urn': '...'}, {'type': 'numeric', ...})."
        ),
    )
    question_text: MultilingualText | None = Field(
        default=None, description="Multilingual literal question text."
    )
    extended_attributes: list[dict[str, Any]] = Field(
        default_factory=list, description="Extensible attributes list of objects."
    )
    created_at: datetime | None = None
    updated_at: datetime | None = None


class QuestionSchemeSchema(DDISchemeSchema):
    """Schema for QuestionScheme."""

    questions: list[QuestionItemSchema] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CategorySchema(DDIResourceSchema):
    """Schema for Category (response label)."""

    name: MultilingualText = Field(default_factory=list, description="Multilingual category name.")
    scheme_urn: str | None = Field(default=None, description="Parent CategoryScheme URN.")
    concept_urn: str | None = Field(
        default=None, description="Optional Concept URN anchor in a controlled vocabulary."
    )
    label: MultilingualText | None = Field(
        default=None, description="Multilingual response category label."
    )
    parent_urn: str | None = Field(
        default=None, description="Parent Category URN for hierarchical schemes."
    )
    order: int | None = Field(default=0, description="Display order within category scheme.")
    is_missing: bool | None = Field(
        default=False, description="Whether this category represents a missing value."
    )
    extended_attributes: list[dict[str, Any]] = Field(
        default_factory=list, description="Extensible attributes list of objects."
    )
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CategorySchemeSchema(DDISchemeSchema):
    """Schema for CategoryScheme."""

    categories: list[CategorySchema] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CodeSchema(DDIIdentifiableSchema):
    """Schema for individual Code inside a CodeList."""

    code_list_urn: str | None = None
    category_urn: str | None = None
    code_value: str | None = Field(default=None, description="Numerical or text code string.")
    parent_urn: str | None = Field(
        default=None, description="Parent Code URN for hierarchical code schemes."
    )
    order: int | None = 0
    is_missing: bool | None = Field(
        default=False, description="Whether this code represents a missing / non-response value."
    )
    hashes: dict[str, Any] | None = Field(
        default=None,
        description="Unified key-value hash digests dictionary (e.g. {'sha256': '...'}).",
    )
    extended_attributes: list[dict[str, Any]] = Field(
        default_factory=list, description="Extensible attributes list of objects."
    )
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CodeListSchema(DDIResourceSchema):
    """Schema for CodeList entity."""

    name: MultilingualText = Field(default_factory=list, description="Multilingual title.")
    description: MultilingualText | None = Field(
        default=None, description="Multilingual description."
    )
    scheme_urn: str | None = None
    codes: list[CodeSchema] = Field(default_factory=list)
    extended_attributes: list[dict[str, Any]] = Field(
        default_factory=list, description="Extensible attributes list of objects."
    )
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RepresentedVariableSchemeSchema(DDISchemeSchema):
    """Schema for RepresentedVariableScheme."""

    represented_variables: list[RepresentedVariableSchema] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RepresentedVariableSchema(DDIResourceSchema):
    """Schema for RepresentedVariable."""

    scheme_urn: str | None = Field(
        default=None, description="Parent RepresentedVariableScheme URN."
    )
    conceptual_variable_urn: str | None = None
    code_list_urn: str | None = None
    value_representation: dict[str, Any] | None = Field(
        default=None,
        description=(
            "JSON object describing the value representation "
            "(e.g. {'type': 'code', 'code_list_urn': '...'}, {'type': 'numeric', ...})."
        ),
    )
    label: MultilingualText | None = Field(default=None, description="Multilingual short label.")
    description: MultilingualText | None = Field(
        default=None, description="Multilingual description."
    )
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


class InstrumentSchema(DDIResourceSchema):
    """Schema for DDI-Lifecycle Instrument."""

    name: MultilingualText = Field(default_factory=list, description="Technical name.")
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


class StudyUnitSchema(DDIResourceSchema):
    """Schema for StudyUnit (survey wave dataset)."""

    name: MultilingualText = Field(default_factory=list, description="Multilingual study name.")
    title: MultilingualText | None = Field(default=None, description="Multilingual study title.")
    external_ref: str | None = Field(default=None, description="External reference or DOI.")
    year: int | None = Field(default=None, description="Survey year.")
    description: MultilingualText | None = Field(default=None, description="Multilingual abstract.")
    extended_attributes: list[dict[str, Any]] = Field(
        default_factory=list, description="Extensible attributes list of objects."
    )
    created_at: datetime | None = None
    updated_at: datetime | None = None


class InstanceVariableSchemeSchema(DDISchemeSchema):
    """Schema for InstanceVariableScheme."""

    instance_variables: list[InstanceVariableSchema] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class InstanceVariableSchema(DDIResourceSchema):
    """Schema for InstanceVariable (column realization in a study dataset)."""

    scheme_urn: str | None = Field(default=None, description="Parent InstanceVariableScheme URN.")
    represented_variable_urn: str | None = None
    label: MultilingualText | None = Field(default=None, description="Multilingual variable label.")
    description: MultilingualText | None = Field(
        default=None, description="Multilingual description."
    )
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


class UrnRegistrySchema(BaseModel):
    """Schema for UrnRegistry capturing URN/URI to resource type mapping."""

    model_config = ConfigDict(from_attributes=True)

    urn: str = Field(..., description="Canonical URN or external identifier/URI.")
    resource_type: str = Field(
        ...,
        description="Target resource type (e.g. 'QuestionItem', 'Category', 'ExternalConcept').",
    )
    extended_attributes: list[dict[str, Any]] = Field(
        default_factory=list, description="Extensible attributes list of objects."
    )
    created_at: datetime | None = None
    updated_at: datetime | None = None


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
