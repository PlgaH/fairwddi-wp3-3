"""Infrastructure, Provenance, Quarantine, and Staging Layer models for FAIRwDDI.

Includes URNAlias, MetadataQuarantine, StagedImport, and StagedResourceNode.
"""

from django.db import models


class URNAlias(models.Model):
    """Maps external or random URNs to canonical database entities.

    Preserves audit provenance without overwriting source URNs.
    """

    alias_urn = models.CharField(
        max_length=512,
        unique=True,
        help_text="The external, legacy, or random URN.",
    )
    canonical_urn = models.CharField(
        max_length=512,
        db_index=True,
        help_text="The resolved canonical database URN.",
    )
    entity_type = models.CharField(
        max_length=64,
        help_text="Target DDI entity type name (e.g. 'QuestionItem', 'CodeList').",
    )
    hash_strategy = models.CharField(
        max_length=64,
        default="v1_strict_sha256",
        help_text="Strategy used to establish the canonical alias link.",
    )
    source_file = models.CharField(
        max_length=512,
        null=True,
        blank=True,
        help_text="Originating import filename for audit trail.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "request_ddi_urnalias"
        verbose_name = "URN Alias"
        verbose_name_plural = "URN Aliases"

    def __str__(self) -> str:
        return f"{self.alias_urn} -> {self.canonical_urn}"


class MetadataQuarantine(models.Model):
    """Holds incoming metadata elements requiring archivist review due to collisions."""

    incoming_urn = models.CharField(
        max_length=512,
        help_text="URN of the conflicting element.",
    )
    existing_urn = models.CharField(
        max_length=512,
        null=True,
        blank=True,
        help_text="URN of the conflicting database entity.",
    )
    entity_type = models.CharField(
        max_length=64,
        help_text="DDI entity type name.",
    )
    incoming_content = models.JSONField(
        help_text="Full serialized payload of the incoming element.",
    )
    existing_content_hash = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="Hash of the existing record for comparison.",
    )
    incoming_content_hash = models.CharField(
        max_length=64,
        help_text="Hash of the incoming element.",
    )
    conflict_type = models.CharField(
        max_length=32,
        help_text="Reason: 'hash_mismatch', 'fuzzy_match', 'version_conflict'.",
    )
    resolution = models.CharField(
        max_length=32,
        null=True,
        blank=True,
        help_text="Status: 'approved', 'forked', 'rejected', or null (pending).",
    )
    resolved_by = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Username of the reviewing archivist.",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    source_file = models.CharField(
        max_length=512,
        null=True,
        blank=True,
        help_text="Originating import filename.",
    )
    import_task_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Link to background task execution.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "request_ddi_metadataquarantine"
        indexes = [
            models.Index(fields=["resolution"], name="req_ddi_mq_resolution_idx"),
        ]
        verbose_name = "Metadata Quarantine Record"
        verbose_name_plural = "Metadata Quarantine Records"

    def __str__(self) -> str:
        return f"Quarantine: {self.entity_type} ({self.incoming_urn}) - {self.conflict_type}"


class StagedImport(models.Model):
    """Stores metadata about uploaded file bundles and batch import jobs."""

    source_format = models.CharField(
        max_length=64,
        help_text="Source format: 'ddi_l_3.3', 'ddi_l_4_json', 'ddi_c_2.5', 'croissant', 'csv'.",
    )
    file_name = models.CharField(
        max_length=512,
        help_text="Original uploaded filename.",
    )
    file_path = models.FileField(
        upload_to="raw_imports/",
        null=True,
        blank=True,
        help_text="File storage path for large XML/JSON/CSV file payloads.",
    )
    import_options = models.JSONField(
        default=dict,
        blank=True,
        help_text="Lightweight batch configuration and options passed with the upload.",
    )
    total_resources = models.IntegerField(
        default=0,
        help_text="Total staged resource nodes extracted from the payload.",
    )
    processed_resources = models.IntegerField(
        default=0,
        help_text="Count of successfully processed resource nodes.",
    )
    status = models.CharField(
        max_length=32,
        default="staged",
        help_text="Status: 'staged', 'harmonized', 'quarantined', 'failed'.",
    )
    import_task_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Link to background task queue.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "request_ddi_stagedimport"
        verbose_name = "Staged Import"
        verbose_name_plural = "Staged Imports"

    def __str__(self) -> str:
        return f"Import #{self.pk}: {self.file_name} ({self.source_format})"


class StagedResourceNode(models.Model):
    """Stores individual broken-down raw element resources from Stage 1 parsing.

    Enables granular resource-level harmonization, selective re-harmonization,
    and native DDI-L 4 JSON / COGS model object ingestion.
    """

    staged_import = models.ForeignKey(
        StagedImport,
        on_delete=models.CASCADE,
        related_name="nodes",
        help_text="Parent staged import bundle.",
    )
    resource_type = models.CharField(
        max_length=64,
        db_index=True,
        help_text="DDI entity type (e.g. 'QuestionItem', 'CodeList', 'Category', 'StudyUnit').",
    )
    raw_urn = models.CharField(
        max_length=512,
        db_index=True,
        help_text="Raw external URN or local identifier from the source file.",
    )
    raw_value = models.JSONField(
        help_text="Un-harmonized raw JSON dictionary of fields/attributes.",
    )
    canonical_urn = models.CharField(
        max_length=512,
        null=True,
        blank=True,
        db_index=True,
        help_text="Resolved canonical database URN after normalization.",
    )
    status = models.CharField(
        max_length=32,
        default="staged",
        help_text="Status: 'staged', 'harmonized', 'quarantined', 'failed'.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "request_ddi_stagedresourcenode"
        verbose_name = "Staged Resource Node"
        verbose_name_plural = "Staged Resource Nodes"

    def __str__(self) -> str:
        return f"{self.resource_type}: {self.raw_urn} ({self.status})"
