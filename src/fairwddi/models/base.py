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

    # Unified multi-algorithm hash digests: e.g. {"sha256": "...", "canonical_nfkc": "..."}
    hashes = models.JSONField(
        default=dict,
        blank=True,
        help_text="Unified key-value hash digests dictionary (e.g. {'sha256': '...'}).",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    @property
    def is_canonical_ddi(self) -> bool:
        """Check if URN strictly matches canonical DDI 3.3 / 4.0 format (urn:ddi:agency:ID:version)."""
        if not self.urn or not self.urn.startswith("urn:ddi:"):
            return False
        parts = self.urn.split(":")
        return len(parts) in (4, 5)

    @property
    def is_maintainable_scoped(self) -> bool:
        """Check if the ID section represents a nested MaintainableID.ObjectID."""
        id_sec = self.identifier
        return "." in id_sec

    @property
    def agency(self) -> str:
        """Parse the maintenance agency identifier from the canonical or legacy URN."""
        if self.urn and self.urn.startswith("urn:ddi:"):
            parts = self.urn.split(":")
            if len(parts) >= 3:
                return parts[2]
        return os.getenv("DDI_AGENCY", "fr.sciencespo")

    @property
    def identifier(self) -> str:
        """Parse the full ID component (e.g. 'ID' or 'MaintainableID.ObjectID')."""
        if self.urn and self.urn.startswith("urn:ddi:"):
            parts = self.urn.split(":")
            if len(parts) in (4, 5):
                return parts[3]
            if len(parts) >= 6:
                # Legacy 5-colon format: urn:ddi:agency:maintainable:object:version
                return f"{parts[3]}.{parts[4]}"
        return self.urn or ""

    @property
    def maintainable_id(self) -> str | None:
        """Extract the MaintainableID portion if maintainable-scoped, or ID if agency-scoped."""
        if self.urn and self.urn.startswith("urn:ddi:"):
            parts = self.urn.split(":")
            if len(parts) >= 6:
                return parts[3]
            if len(parts) in (4, 5):
                id_part = parts[3]
                if "." in id_part:
                    return id_part.split(".", 1)[0]
                return id_part
        return None

    @property
    def object_id(self) -> str | None:
        """Extract the specific ObjectID portion if maintainable-scoped."""
        if self.urn and self.urn.startswith("urn:ddi:"):
            parts = self.urn.split(":")
            if len(parts) >= 6:
                return parts[4]
            if len(parts) in (4, 5):
                id_part = parts[3]
                if "." in id_part:
                    return id_part.split(".", 1)[1]
                return id_part
        return self.urn or None

    @property
    def version(self) -> str:
        """Parse the version component from the canonical or legacy URN."""
        if self.urn and self.urn.startswith("urn:ddi:"):
            parts = self.urn.split(":")
            if len(parts) == 5:
                return parts[4]
            if len(parts) >= 6:
                return parts[5]
        return "1.0.0"

    def save(self, *args, **kwargs) -> None:
        """Ensure a canonical URN is present before saving."""
        if not self.urn:
            agency = os.getenv("DDI_AGENCY", "fr.sciencespo")
            primary_hash = (
                self.hashes.get("sha256") or self.hashes.get("primary")
                if isinstance(self.hashes, dict)
                else None
            )
            object_id = (
                primary_hash[:16]
                if primary_hash
                else f"{self.__class__.__name__}-{uuid.uuid4().hex[:12]}"
            )
            self.urn = f"urn:ddi:{agency}:{object_id}:1.0.0"
        super().save(*args, **kwargs)
