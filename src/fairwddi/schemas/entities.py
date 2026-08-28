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


class CollectionSchema(BaseModel):
    """Schema for Collection (Series / Group)."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    distributor_id: int
    name: str = Field(..., description="Series / Collection title.")
    description: MultilingualText | None = Field(
        default=None,
        description="Multilingual collection abstract/description.",
    )
    urn: str | None = Field(default=None, description="DDI-L Group URN.")
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SubcollectionSchema(BaseModel):
    """Schema for Subcollection (Sub-Series / SubGroup)."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    collection_id: int
    name: str = Field(..., description="Subcollection title.")
    urn: str | None = Field(default=None, description="DDI-L SubGroup URN.")
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


class ConceptRelationshipSchema(BaseModel):
    """Schema for SKOS/XKOS concept-to-concept semantic mappings."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    source_concept_id: int
    target_concept_id: int | None = None
    relationship_type: str = Field(
        ...,
        description="SKOS relation: broader, narrower, related, exactMatch, correspondsTo.",
    )
    target_uri: str | None = Field(
        default=None, description="External URI if target is outside DB."
    )
    created_at: datetime | None = None


class ConceptualVariableSchema(DDIIdentifiableSchema):
    """Schema for abstract ConceptualVariable."""

    id: int | None = None
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

    id: int | None = None
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


class CategorySchema(DDIIdentifiableSchema):
    """Schema for Category (response label)."""

    id: int | None = None
    label: MultilingualText = Field(..., description="Multilingual response category label.")
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CategorySetItemSchema(BaseModel):
    """Schema for member item inside a CategorySet."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    category_set_id: int | None = None
    category_id: int
    order: int = 0


class CategorySetSchema(DDIIdentifiableSchema):
    """Schema for CategorySet (CategoryScheme)."""

    id: int | None = None
    name: MultilingualText = Field(..., description="Multilingual name for the category set.")
    description: MultilingualText | None = Field(
        default=None, description="Multilingual description."
    )
    items: list[CategorySetItemSchema] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CodeItemSchema(BaseModel):
    """Schema for individual CodeItem inside a CodeList."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    code_list_id: int | None = None
    category_id: int
    code_value: str = Field(..., description="Numerical or text code string.")
    order: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CodeListSchema(DDIIdentifiableSchema):
    """Schema for CodeList entity."""

    id: int | None = None
    name: MultilingualText | None = Field(default=None, description="Multilingual title.")
    description: MultilingualText | None = Field(
        default=None, description="Multilingual description."
    )
    category_set_id: int | None = None
    items: list[CodeItemSchema] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RepresentedVariableSchema(DDIIdentifiableSchema):
    """Schema for RepresentedVariable."""

    id: int | None = None
    conceptual_variable_id: int
    question_item_id: int
    code_list_id: int | None = None
    label: MultilingualText | None = Field(default=None, description="Multilingual short label.")
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ============================================================================
# Dataset Layer
# ============================================================================


class StudyUnitSchema(DDIIdentifiableSchema):
    """Schema for StudyUnit (survey wave dataset)."""

    id: int | None = None
    subcollection_id: int
    title: MultilingualText = Field(..., description="Multilingual study title.")
    external_ref: str | None = Field(default=None, description="External reference or DOI.")
    year: int | None = Field(default=None, description="Survey year.")
    description: MultilingualText | None = Field(default=None, description="Multilingual abstract.")
    created_at: datetime | None = None
    updated_at: datetime | None = None


class InstanceVariableSchema(DDIIdentifiableSchema):
    """Schema for InstanceVariable (column realization in a study dataset)."""

    id: int | None = None
    study_unit_id: int
    represented_variable_id: int
    variable_name: str = Field(..., description="Dataset column name (e.g. q01a).")
    universe: MultilingualText | None = Field(
        default=None, description="Target population universe."
    )
    notes: MultilingualText | None = Field(default=None, description="Multilingual notes.")
    is_indexed: bool = Field(default=False, description="Elasticsearch indexing status.")
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ============================================================================
# Grouping / Organization Layer
# ============================================================================


class VariableGroupMembershipSchema(BaseModel):
    """Schema for VariableGroup membership junction."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    variable_group_id: int | None = None
    instance_variable_id: int
    order: int = 0


class VariableGroupSchema(DDIIdentifiableSchema):
    """Schema for DDI VariableGroup."""

    id: int | None = None
    study_unit_id: int | None = None
    collection_id: int | None = None
    parent_group_id: int | None = None
    label: MultilingualText = Field(..., description="Multilingual group title/label.")
    description: MultilingualText | None = Field(
        default=None, description="Multilingual description."
    )
    type_of_group: str = Field(default="Thematic", description="DDI-L typeOfVariableGroup.")
    concept_id: int | None = None
    memberships: list[VariableGroupMembershipSchema] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ============================================================================
# Infrastructure & Staging Layer
# ============================================================================


class URNAliasSchema(BaseModel):
    """Schema for URNAlias mapping."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    alias_urn: str = Field(..., description="External or random URN.")
    canonical_urn: str = Field(..., description="Canonical database URN.")
    entity_type: str = Field(..., description="Target DDI entity type name.")
    hash_strategy: str = Field(
        default="v1_strict_sha256", description="Strategy used for alias link."
    )
    source_file: str | None = Field(default=None, description="Originating filename.")
    created_at: datetime | None = None


class MetadataQuarantineSchema(BaseModel):
    """Schema for MetadataQuarantine records."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    incoming_urn: str
    existing_urn: str | None = None
    entity_type: str
    incoming_content: dict[str, Any] | list[Any]
    existing_content_hash: str | None = None
    incoming_content_hash: str
    conflict_type: str = Field(..., description="hash_mismatch, fuzzy_match, version_conflict.")
    resolution: str | None = Field(default=None, description="approved, forked, rejected, null.")
    resolved_by: str | None = None
    resolved_at: datetime | None = None
    source_file: str | None = None
    import_task_id: str | None = None
    created_at: datetime | None = None


class StagedImportPayloadSchema(BaseModel):
    """Schema for raw StagedImportPayload record."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    source_format: str = Field(
        ..., description="ddi_l_3.3, ddi_l_4_json, ddi_c_2.5, croissant, csv."
    )
    file_name: str
    file_path: str | None = None
    raw_payload: dict[str, Any] | list[Any] | None = None
    original_urns: dict[str, str] = Field(default_factory=dict)
    status: str = Field(default="staged", description="staged, harmonized, quarantined, failed.")
    import_task_id: str | None = None
    created_at: datetime | None = None
    processed_at: datetime | None = None


class StagedResourceNodeSchema(BaseModel):
    """Schema for decomposed StagedResourceNode."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    import_payload_id: int
    resource_type: str = Field(..., description="QuestionItem, CodeList, Category, etc.")
    raw_urn: str = Field(..., description="Incoming raw URN or element identifier.")
    raw_value: dict[str, Any] = Field(..., description="Un-harmonized raw JSON dictionary.")
    canonical_urn: str | None = None
    status: str = Field(default="staged", description="staged, harmonized, quarantined, failed.")
    created_at: datetime | None = None
