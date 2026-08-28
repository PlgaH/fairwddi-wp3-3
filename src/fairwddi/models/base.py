"""Abstract base models and mixins for FAIRwDDI."""

from django.db import models


class DDIIdentifiable(models.Model):
    """Abstract mixin for DDI-Lifecycle URN identification and multi-algorithm fingerprinting.

    Decoupled from specific hashing implementations, this base model stores
    persistent URN identifiers, versioning, and hash fingerprints.
    """

    urn = models.CharField(
        max_length=512,
        unique=True,
        null=True,
        blank=True,
        help_text="Full persistent URN: urn:ddi:{agency}:{identifier}:{version}",
    )
    agency = models.CharField(
        max_length=255,
        default="fr.cdsp",
        help_text="DDI maintenance agency identifier.",
    )
    ddi_identifier = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        help_text="Local or canonical identifier string within the agency scope.",
    )
    version = models.CharField(
        max_length=64,
        default="1.0.0",
        help_text="Entity version string.",
    )

    # Primary content hash digest (e.g. SHA-256)
    content_hash = models.CharField(
        max_length=64,
        blank=True,
        default="",
        db_index=True,
        help_text="Primary content digest (64-char hex) for drift detection and deduplication.",
    )

    # Multi-algorithm auxiliary strategy hashes: e.g. {"v1_strict": "...", "v2_unordered": "..."}
    content_hashes = models.JSONField(
        default=dict,
        blank=True,
        help_text="Multi-algorithm strategy hash digests dictionary.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
