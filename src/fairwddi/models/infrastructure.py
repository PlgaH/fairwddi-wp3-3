"""Infrastructure, Provenance, Quarantine, and Batch Receipt models for FAIRwDDI.

Includes UrnRegistry, URNAlias, MetadataQuarantine, and IngestBatch.
"""

from django.db import models


class UrnRegistry(models.Model):
    """Central registry mapping URNs and external URIs to their resource types.

    Provides referential integrity and O(1) URN-to-type crosswalk resolution
    for both DDI and non-DDI identifiers.
    """

    urn = models.CharField(
        max_length=512,
        primary_key=True,
        help_text="Canonical URN or external identifier/URI.",
    )
    resource_type = models.CharField(
        max_length=64,
        db_index=True,
        help_text="Resource/entity type (e.g. 'QuestionItem', 'Category', 'ExternalConcept').",
    )
    status = models.CharField(
        max_length=32,
        default="active",
        db_index=True,
        help_text="Publication or lifecycle status (e.g. 'active', 'deprecated').",
    )
    extended_attributes = models.JSONField(
        default=list,
        blank=True,
        null=True,
        help_text="Extended attributes stored as an array of objects.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "request_ddi_urnregistry"
        verbose_name = "URN Registry"
        verbose_name_plural = "URN Registries"

    def __str__(self) -> str:
        return f"{self.urn} ({self.resource_type})"


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


class IngestBatch(models.Model):
    """Lightweight receipt tracking a completed or rolled-back file ingestion batch.

    Stores one summary row per ingested file (zero per-node JSONB duplication) to
    prevent duplicate file ingestion via SHA-256, track batch statistics, and support
    instant transactional rollback (`undo_ingestion`).
    """

    source_format = models.CharField(
        max_length=64,
        help_text=(
            "Source format slug: 'ddi-l:4.0:json', 'ddi-l:4.0:jsonl', "
            "'ddi-l:3.3:xml', 'ddi-c:2.5:xml'."
        ),
    )
    file_name = models.CharField(
        max_length=512,
        help_text="Original or upgraded filename ingested.",
    )
    file_sha256 = models.CharField(
        max_length=64,
        db_index=True,
        help_text="SHA-256 digest of the ingested file for duplicate prevention.",
    )
    file_path = models.CharField(
        max_length=1024,
        null=True,
        blank=True,
        help_text="Resolved path to the ingested metadata file on disk.",
    )
    status = models.CharField(
        max_length=32,
        default="completed",
        db_index=True,
        help_text="Batch status: 'completed', 'quarantined', 'undone', 'failed'.",
    )
    options = models.JSONField(
        default=dict,
        blank=True,
        help_text="Batch configuration, job_id, profile, and options.",
    )
    created_urns = models.JSONField(
        default=list,
        blank=True,
        help_text="Ordered list of canonical URNs created exclusively by this batch.",
    )
    reused_urns = models.JSONField(
        default=list,
        blank=True,
        help_text="List of pre-existing canonical URNs reused during this batch.",
    )
    created_aliases = models.JSONField(
        default=list,
        blank=True,
        help_text="List of alias_urn values registered in URNAlias by this batch.",
    )
    stats = models.JSONField(
        default=dict,
        blank=True,
        help_text="Summary counts of created entities, shortcuts, and frequencies.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "request_ddi_ingestbatch"
        verbose_name = "Ingest Batch"
        verbose_name_plural = "Ingest Batches"

    def __str__(self) -> str:
        return f"Batch #{self.pk}: {self.file_name} ({self.status})"
