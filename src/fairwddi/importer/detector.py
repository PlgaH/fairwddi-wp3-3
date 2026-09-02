"""Metadata format detection for FAIRwDDI.

Detects specifications (DDI-Lifecycle, DDI-Codebook, DDI-CDI), versions,
serializations, and archive flavors (Colectica, Nesstar, etc.).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from lxml import etree
from pydantic import BaseModel, ConfigDict, Field


class MetadataFormatInfo(BaseModel):
    """Structured information about a detected metadata document format."""

    model_config = ConfigDict(frozen=True)

    specification: Literal["DDI-L", "DDI-C", "DDI-CDI", "Unknown"] = Field(
        ..., description="Metadata specification family."
    )
    version: str = Field(..., description="Specification version (e.g. '3.3', '3.2', '2.5').")
    serialization: Literal["xml", "json", "json-ld", "turtle", "csv", "unknown"] = Field(
        ..., description="Serialization format."
    )
    flavor: str | None = Field(
        default=None, description="Producer flavor/dialect (e.g. 'Colectica', 'Nesstar')."
    )
    root_tag_or_type: str | None = Field(
        default=None, description="Root XML element localname or top-level JSON type."
    )
    canonical_slug: str = Field(
        ..., description="Normalized format slug for StagedImport.source_format."
    )


def detect_metadata_format(file_path: str | Path) -> MetadataFormatInfo:
    """Detect metadata specification, version, serialization, and flavor from a file.

    Args:
        file_path: Absolute or relative path to the metadata file.

    Returns:
        MetadataFormatInfo instance with detailed format attributes.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Metadata file not found: {path}")

    suffix = path.suffix.lower()
    name = path.name.lower()

    # 1. JSON / JSON-LD files
    if suffix in (".json", ".jsonld") or ".json" in name:
        return _detect_json_format(path)

    # 2. XML files
    if suffix in (".xml", ".ddic", ".ddi33", ".ddi40") or ".xml" in name:
        return _detect_xml_format(path)

    # 3. Fallback / Unknown
    return MetadataFormatInfo(
        specification="Unknown",
        version="unknown",
        serialization="unknown",
        flavor=None,
        canonical_slug="unknown",
    )


def _detect_json_format(path: Path) -> MetadataFormatInfo:
    """Inspect JSON file contents to detect DDI 4.0 JSON or DDI-CDI JSON-LD."""
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            first_chars = f.read(4096)
            f.seek(0)
            data = json.load(f)

        if isinstance(data, dict):
            # Check for DDI-CDI JSON-LD
            context = data.get("@context", "")
            if isinstance(context, str) and "cdi" in context.lower():
                return MetadataFormatInfo(
                    specification="DDI-CDI",
                    version="1.0",
                    serialization="json-ld",
                    flavor="Generic",
                    root_tag_or_type=data.get("@type"),
                    canonical_slug="ddi-cdi:1.0:jsonld",
                )

            # Check for DDI 4 / Colectica JSON items
            if "items" in data or "$type" in data:
                items = data.get("items", [])
                root_type = (
                    items[0].get("$type")
                    if items and isinstance(items, list)
                    else data.get("$type")
                )
                flavor = (
                    "Colectica"
                    if "colectica" in first_chars.lower() or "uk.closer" in first_chars.lower()
                    else "Generic"
                )
                return MetadataFormatInfo(
                    specification="DDI-L",
                    version="4.0",
                    serialization="json",
                    flavor=flavor,
                    root_tag_or_type=root_type or "ResourcePackage",
                    canonical_slug="ddi-l:4.0:json",
                )

    except Exception:
        pass

    return MetadataFormatInfo(
        specification="Unknown",
        version="unknown",
        serialization="json",
        flavor=None,
        canonical_slug="json:unknown",
    )


def _detect_xml_format(path: Path) -> MetadataFormatInfo:
    """Inspect XML file namespaces and root elements using streaming iterparse."""
    try:
        root_tag = None
        root_ns = None
        nsmap: dict[str, str] = {}

        for _event, elem in etree.iterparse(path, events=("start",)):
            root_tag = etree.QName(elem).localname
            root_ns = etree.QName(elem).namespace
            nsmap = dict(elem.nsmap)
            break

        # Check DDI-Codebook
        if root_tag == "codeBook" or (root_ns and "codebook" in root_ns.lower()):
            version = "2.5"
            if root_ns and "2_1" in root_ns:
                version = "2.1"
            flavor = (
                "Nesstar"
                if "fsd" in str(path).lower() or "nesstar" in str(path).lower()
                else "Generic"
            )
            return MetadataFormatInfo(
                specification="DDI-C",
                version=version,
                serialization="xml",
                flavor=flavor,
                root_tag_or_type=root_tag,
                canonical_slug=f"ddi-c:{version}:xml",
            )

        # Check DDI-Lifecycle 3.3
        ns_values = " ".join(str(v) for v in nsmap.values())
        if "3_3" in ns_values or "3.3" in str(path) or ".ddi33." in path.name:
            flavor = (
                "Colectica"
                if "closer" in str(path).lower()
                or "midus" in str(path).lower()
                or "colectica" in ns_values.lower()
                else "Generic"
            )
            return MetadataFormatInfo(
                specification="DDI-L",
                version="3.3",
                serialization="xml",
                flavor=flavor,
                root_tag_or_type=root_tag,
                canonical_slug="ddi-l:3.3:xml",
            )

        # Check DDI-Lifecycle 3.2
        if "3_2" in ns_values or "3.2" in str(path):
            return MetadataFormatInfo(
                specification="DDI-L",
                version="3.2",
                serialization="xml",
                flavor="Generic",
                root_tag_or_type=root_tag,
                canonical_slug="ddi-l:3.2:xml",
            )

        # Check DDI-Lifecycle 4.0 XML
        if "4_0" in ns_values or ".ddi40." in path.name:
            return MetadataFormatInfo(
                specification="DDI-L",
                version="4.0",
                serialization="xml",
                flavor="Colectica",
                root_tag_or_type=root_tag,
                canonical_slug="ddi-l:4.0:xml",
            )

        # Check DDI-CDI XML
        if "cdi" in ns_values.lower() or (root_ns and "cdi" in root_ns.lower()):
            return MetadataFormatInfo(
                specification="DDI-CDI",
                version="1.0",
                serialization="xml",
                flavor="Generic",
                root_tag_or_type=root_tag,
                canonical_slug="ddi-cdi:1.0:xml",
            )

    except Exception:
        pass

    return MetadataFormatInfo(
        specification="Unknown",
        version="unknown",
        serialization="xml",
        flavor=None,
        canonical_slug="xml:unknown",
    )
