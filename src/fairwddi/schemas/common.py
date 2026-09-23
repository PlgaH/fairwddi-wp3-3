"""Common Pydantic v2 schemas and models for FAIRwDDI."""

from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, RootModel


class MultilingualItem(BaseModel):
    """Localized text object with value, optional language, and extensible attributes."""

    model_config = ConfigDict(extra="allow")

    value: str = Field(..., description="The textual string content.")
    lang: str | None = Field(
        default=None,
        description="ISO 639-1 / BCP 47 language code, or None.",
    )
    type: str | None = Field(
        default=None,
        description="Text classification (e.g. 'literal', 'normalized', 'raw', 'translated').",
    )
    format: str | None = Field(
        default=None,
        description="MIME format (e.g. 'text/plain', 'text/markdown', 'text/html').",
    )


class MultilingualText(RootModel[list[MultilingualItem]]):
    """Root container representing multilingual text stored as a JSONB array of objects."""

    root: list[MultilingualItem] = Field(default_factory=list)

    def __iter__(self):  # type: ignore[override]
        return iter(self.root)

    def __len__(self) -> int:
        return len(self.root)

    def __getitem__(self, index: int) -> MultilingualItem:
        return self.root[index]

    def get(self, lang: str | None = None, fallback: bool = True) -> str | None:
        """Retrieve the text value for a specific language code.

        If lang is specified, attempts to find an exact match.
        If fallback is True and no match is found, returns the first item's value.
        """
        if not self.root:
            return None

        if lang is not None:
            # First pass: matching lang and (type is None or type == 'literal')
            for item in self.root:
                if item.lang == lang and (item.type is None or item.type == "literal"):
                    return item.value
            # Second pass: matching lang regardless of type
            for item in self.root:
                if item.lang == lang:
                    return item.value

        if fallback and self.root:
            return self.root[0].value

        return None

    def add(
        self,
        value: str,
        lang: str | None = None,
        type: str | None = None,
        format: str | None = None,
        **extra: Any,
    ) -> MultilingualItem:
        """Add a new localized text item to the list."""
        item_data: dict[str, Any] = {
            "value": value,
            "lang": lang,
            "type": type,
            "format": format,
            **extra,
        }
        item = MultilingualItem(**item_data)
        self.root.append(item)
        return item

    def to_dict(self) -> dict[str, str]:
        """Convert array of objects to a simple {lang: value} dictionary for convenience."""
        result: dict[str, str] = {}
        for item in self.root:
            key = item.lang or "und"
            if key not in result or (item.type is None or item.type == "literal"):
                result[key] = item.value
        return result

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> MultilingualText:
        """Factory method to construct MultilingualText from a {lang: value} dictionary."""
        items = [MultilingualItem(lang=k, value=v) for k, v in data.items()]
        return cls(root=items)

    @classmethod
    def from_single(cls, value: str, lang: str | None = None) -> MultilingualText:
        """Factory method to construct MultilingualText from a single string."""
        return cls(root=[MultilingualItem(lang=lang, value=value)])


class DDIIdentifiableSchema(BaseModel):
    """Base Pydantic schema for DDI-Lifecycle identifiable entities."""

    model_config = ConfigDict(from_attributes=True)

    urn: str | None = Field(
        default=None,
        description="Persistent canonical URN: urn:ddi:{agency}:{ID}:{version}",
    )
    hashes: dict[str, str] = Field(
        default_factory=dict,
        description="Unified key-value hash digests dictionary (e.g. {'sha256': '...'}).",
    )

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
        """Parse agency from URN."""
        if self.urn and self.urn.startswith("urn:ddi:"):
            parts = self.urn.split(":")
            if len(parts) >= 3:
                return parts[2]
        return os.getenv("DDI_AGENCY", "fr.sciencespo")

    @property
    def identifier(self) -> str:
        """Parse identifier from URN."""
        if self.urn and self.urn.startswith("urn:ddi:"):
            parts = self.urn.split(":")
            if len(parts) in (4, 5):
                return parts[3]
            if len(parts) >= 6:
                return f"{parts[3]}.{parts[4]}"
        return self.urn or ""

    @property
    def maintainable_id(self) -> str | None:
        """Extract MaintainableID portion if maintainable-scoped, or ID if agency-scoped."""
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
        """Extract specific ObjectID portion if maintainable-scoped."""
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
        """Parse version from URN."""
        if self.urn and self.urn.startswith("urn:ddi:"):
            parts = self.urn.split(":")
            if len(parts) == 5:
                return parts[4]
            if len(parts) >= 6:
                return parts[5]
        return "1.0.0"
