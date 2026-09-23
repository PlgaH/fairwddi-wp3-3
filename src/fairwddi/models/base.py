"""Abstract base models and mixins for FAIRwDDI."""

from __future__ import annotations

import os
import uuid

from django.db import models


class DDIIdentifiable(models.Model):
    """Abstract mixin for DDI-Lifecycle URN identification and multi-algorithm fingerprinting.

    Canonical DDI 3.3 / 4.0 URN format:
    urn:ddi:{agency[.sub-agency]}:{ID}:{version}
    e.g. urn:ddi:fr.sciencespo:Category.cat-fr-yes:1.0.0
    """

    urn = models.CharField(
        max_length=512,
        primary_key=True,
        help_text="Persistent canonical URN: urn:ddi:{agency}:{ID}:{version}",
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

    @property
    def agency(self) -> str:
        """Parse the maintenance agency identifier from the canonical URN."""
        if self.urn and self.urn.startswith("urn:ddi:"):
            parts = self.urn.split(":")
            if len(parts) >= 3:
                return parts[2]
        return os.getenv("DDI_AGENCY", "fr.sciencespo")

    @property
    def identifier(self) -> str:
        """Parse the object/maintainable ID component from the canonical URN."""
        if self.urn and self.urn.startswith("urn:ddi:"):
            parts = self.urn.split(":")
            if len(parts) >= 4:
                return parts[3]
        return self.urn or ""

    @property
    def version(self) -> str:
        """Parse the version component from the canonical URN."""
        if self.urn and self.urn.startswith("urn:ddi:"):
            parts = self.urn.split(":")
            if len(parts) >= 5:
                return parts[4]
        return "1.0.0"

    def save(self, *args, **kwargs) -> None:
        """Ensure a canonical URN is present before saving."""
        if not self.urn:
            agency = os.getenv("DDI_AGENCY", "fr.sciencespo")
            object_id = (
                self.content_hash[:16]
                if self.content_hash
                else f"{self.__class__.__name__}-{uuid.uuid4().hex[:12]}"
            )
            self.urn = f"urn:ddi:{agency}:{object_id}:1.0.0"
        super().save(*args, **kwargs)
