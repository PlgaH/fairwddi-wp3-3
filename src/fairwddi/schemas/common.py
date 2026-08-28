"""Common Pydantic v2 schemas and models for FAIRwDDI."""

from __future__ import annotations

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
        description="Persistent canonical URN: urn:ddi:{agency}:{identifier}:{version}",
    )
    agency: str = Field(default="fr.cdsp", description="DDI maintenance agency identifier.")
    ddi_identifier: str | None = Field(default=None, description="Local or canonical identifier.")
    version: str = Field(default="1.0.0", description="Entity version string.")
    content_hash: str = Field(
        default="",
        description="Primary SHA-256 content digest (64 hex characters).",
    )
    content_hashes: dict[str, str] = Field(
        default_factory=dict,
        description="Multi-algorithm auxiliary content digests.",
    )
