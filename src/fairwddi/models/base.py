"""Abstract base models and mixins for FAIRwDDI."""

from __future__ import annotations

import os
import uuid
from typing import Any

from django.db import models


class DDIIdentifiable(models.Model):
    """Abstract mixin for DDI-Lifecycle URN identification.

    Canonical DDI 3.3 / 4.0 URN format:
    urn:ddi:{agency[.sub-agency]}:{ID}:{version}
    e.g. urn:ddi:fr.cdsp:Category.cat-fr-yes:1.0.0
    """

    urn = models.CharField(
        max_length=512,
        primary_key=True,
        help_text="Persistent canonical URN: urn:ddi:{agency}:{ID}:{version}",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        origin_val = kwargs.pop("origin", None)
        super().__init__(*args, **kwargs)
        self._origin: str | None = origin_val

    def refresh_from_db(self, *args: Any, **kwargs: Any) -> None:
        self._origin = None
        super().refresh_from_db(*args, **kwargs)

    @property
    def origin(self) -> str:
        """Return resource origin ('imported', 'generated', or 'instantiated')."""
        if self._origin:
            return self._origin
        if self.urn:
            from fairwddi.models.infrastructure import ResourceOrigin, UrnRegistry

            val = UrnRegistry.objects.filter(urn=self.urn).values_list("origin", flat=True).first()
            if val:
                self._origin = str(val)
                return self._origin
            return ResourceOrigin.INSTANTIATED.value
        return "instantiated"

    @origin.setter
    def origin(self, value: str) -> None:
        from fairwddi.models.infrastructure import ResourceOrigin

        if value not in ResourceOrigin.values:
            raise ValueError(
                f"Invalid origin '{value}'. Must be one of {list(ResourceOrigin.values)}."
            )
        self._origin = value

    @property
    def is_canonical_ddi(self) -> bool:
        """Check if URN strictly matches canonical DDI 3.3 / 4.0 format.

        Canonical format: urn:ddi:agency:ID:version.
        """
        if not self.urn or not self.urn.startswith("urn:ddi:"):
            return False
        parts = self.urn.split(":")
        return len(parts) in (4, 5)

    @property
    def is_maintainable_scoped(self) -> bool:
        """Check if the ID section represents a nested MaintainableID.ObjectID."""
        if not self.urn or not self.urn.startswith("urn:ddi:"):
            return False
        parts = self.urn.split(":")
        if len(parts) >= 6:
            return True
        id_sec = self.identifier
        return "." in id_sec

    @property
    def agency(self) -> str:
        """Parse the maintenance agency identifier from the canonical or legacy URN."""
        if self.urn and self.urn.startswith("urn:ddi:"):
            parts = self.urn.split(":")
            if len(parts) >= 3:
                return parts[2]
        return os.getenv("DDI_AGENCY", "fr.cdsp")

    @agency.setter
    def agency(self, value: str) -> None:
        """Allow setting or overriding agency component."""
        if not self.urn:
            self.urn = f"urn:ddi:{value}:unassigned:1.0.0"

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

    @identifier.setter
    def identifier(self, value: str) -> None:
        """Allow setting or overriding identifier component."""
        if not self.urn:
            agency = os.getenv("DDI_AGENCY", "fr.cdsp")
            self.urn = f"urn:ddi:{agency}:{value}:1.0.0"

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

    @version.setter
    def version(self, value: str) -> None:
        """Allow setting or overriding version component."""
        pass

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Ensure a canonical URN is present and registered before saving."""
        if not self.urn:
            agency = os.getenv("DDI_AGENCY", "fr.cdsp")
            primary_hash = None
            hashes_val = getattr(self, "hashes", None)
            if isinstance(hashes_val, dict):
                primary_hash = hashes_val.get("sha256") or hashes_val.get("primary")
            object_id = (
                primary_hash[:16]
                if primary_hash
                else f"{self.__class__.__name__}-{uuid.uuid4().hex[:12]}"
            )
            self.urn = f"urn:ddi:{agency}:{object_id}:1.0.0"

        # Pre-register URN in UrnRegistry supertype table before inserting child row
        from fairwddi.models.infrastructure import ResourceOrigin, UrnRegistry

        target_origin = self._origin
        if target_origin is not None and target_origin not in ResourceOrigin.values:
            raise ValueError(
                f"Invalid origin '{target_origin}'. Must be one of {list(ResourceOrigin.values)}."
            )

        reg, created = UrnRegistry.objects.get_or_create(
            urn=self.urn,
            defaults={
                "resource_type": self.__class__.__name__,
                "origin": target_origin or ResourceOrigin.INSTANTIATED,
            },
        )
        if not created:
            update_fields: list[str] = []
            if reg.resource_type != self.__class__.__name__:
                reg.resource_type = self.__class__.__name__
                update_fields.append("resource_type")
            if target_origin and reg.origin != target_origin:
                reg.origin = target_origin
                update_fields.append("origin")
            if update_fields:
                reg.save(update_fields=[*update_fields, "updated_at"])
        self._origin = str(reg.origin)
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        """Delete instance after verifying zero active references, then clean up UrnRegistry."""
        from fairwddi.models.concept import SemanticRelationship
        from fairwddi.models.infrastructure import UrnRegistry
        from fairwddi.utils.integrity import assert_can_delete, integrity_deletion_context

        ignore_urns = kwargs.pop("ignore_urns", None)
        force = kwargs.pop("force", False)
        urn = self.urn
        if not force:
            assert_can_delete(urn, ignore_urns=ignore_urns)
        with integrity_deletion_context(ignore_urns=ignore_urns, bypass=force):
            res = super().delete(*args, **kwargs)
        SemanticRelationship.objects.filter(subject_urn=urn).delete()
        UrnRegistry.objects.filter(urn=urn).delete()
        return res


class DDIScheme(DDIIdentifiable):
    """Abstract base model for all DDI Scheme containers (without hashes)."""

    name = models.JSONField(
        default=list,
        help_text="Multilingual scheme name: [{'lang': 'fr', 'value': '...' }].",
    )
    description = models.JSONField(
        default=list,
        blank=True,
        null=True,
        help_text="Multilingual scheme description stored as an array of objects.",
    )
    extended_attributes = models.JSONField(
        default=list,
        blank=True,
        null=True,
        help_text="Extended attributes stored as an array of objects.",
    )

    class Meta:
        abstract = True

    def __str__(self) -> str:
        if isinstance(self.name, list) and self.name:
            return self.name[0].get("value", self.urn)
        if isinstance(self.name, str):
            return self.name
        return self.urn


class DDIResource(DDIIdentifiable):
    """Abstract base model for all top-level DDI resources requiring urn and name, with hashes."""

    name = models.JSONField(
        default=list,
        help_text="Multilingual name: [{'lang': 'fr', 'value': '...' }].",
    )
    hashes = models.JSONField(
        default=dict,
        blank=True,
        null=True,
        help_text="Unified key-value hash digests dictionary (e.g. {'sha256': '...'}).",
    )

    class Meta:
        abstract = True

    def __str__(self) -> str:
        if isinstance(self.name, list) and self.name:
            return self.name[0].get("value", self.urn)
        if isinstance(self.name, str):
            return self.name
        return self.urn
