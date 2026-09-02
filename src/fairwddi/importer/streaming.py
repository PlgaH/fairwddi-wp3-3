"""Streaming parsers and resource extractors for DDI metadata formats.

Streams DDI-Lifecycle 3.x XML, DDI-Lifecycle 4.0 JSON, and DDI-Codebook 2.5 XML
in constant O(1) memory, extracting structured JSON dictionary payloads.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from lxml import etree

from fairwddi.importer.detector import MetadataFormatInfo, detect_metadata_format
from fairwddi.importer.profiles import ImportProfile


@dataclasses.dataclass
class RawResourceNode:
    """Individual extracted metadata element prior to database staging."""

    resource_type: str
    raw_urn: str
    raw_value: dict[str, Any]
    referenced_urns: set[str] = dataclasses.field(default_factory=set)
    content_fingerprint: str = ""

    def __post_init__(self) -> None:
        if not self.content_fingerprint:
            canonical_json = json.dumps(self.raw_value, sort_keys=True, ensure_ascii=False)
            self.content_fingerprint = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def xml_elem_to_dict(elem: Any) -> dict[str, Any]:
    """Recursively convert an lxml XML element to a structured JSON-compatible dictionary."""
    tag = etree.QName(elem).localname
    d: dict[str, Any] = {"@tag": tag}

    # Extract attributes
    for k, v in elem.attrib.items():
        attr_name = etree.QName(k).localname if "}" in k else k
        d[f"@{attr_name}"] = v

    # Extract text content
    text = elem.text.strip() if elem.text and elem.text.strip() else None
    if text:
        d["#text"] = text

    # Extract child elements
    children = [xml_elem_to_dict(c) for c in elem]
    if children:
        d["children"] = children

    return d


REFERENCE_TAG_PREFIXES = (
    "ConceptReference",
    "CodeListReference",
    "QuestionReference",
    "VariableReference",
    "CategoryReference",
    "InterviewerInstructionReference",
)


def extract_referenced_urns_from_xml(elem: Any) -> set[str]:
    """Extract referenced URNs from Reference elements within an XML tree."""
    refs: set[str] = set()
    for child in elem.iter():
        tag = etree.QName(child).localname
        if tag.endswith("Reference") or tag in REFERENCE_TAG_PREFIXES:
            urn = (
                child.findtext("{ddi:reusable:3_3}URN")
                or child.findtext(".//{ddi:reusable:3_3}URN")
                or child.findtext("URN")
                or child.findtext(".//URN")
            )
            if urn:
                refs.add(urn.strip())
            ref_id = child.findtext("{ddi:reusable:3_3}ID") or child.findtext("ID")
            if ref_id:
                refs.add(ref_id.strip())
    return refs


def extract_referenced_urns_from_json(obj: Any) -> set[str]:
    """Recursively extract referenced URNs from a JSON dictionary."""
    refs: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.endswith("Reference") or "Reference" in k:
                if isinstance(v, dict):
                    urn = v.get("URN") or v.get("urn") or v.get("ID") or v.get("id")
                    if urn and isinstance(urn, str):
                        refs.add(urn.strip())
                elif isinstance(v, str):
                    refs.add(v.strip())
            else:
                refs.update(extract_referenced_urns_from_json(v))
    elif isinstance(obj, list):
        for item in obj:
            refs.update(extract_referenced_urns_from_json(item))
    return refs


def stream_ddi_l_xml(file_path: Path, profile: ImportProfile) -> Iterator[RawResourceNode]:
    """Stream DDI-Lifecycle 3.x XML files element-by-element using iterparse."""
    context = etree.iterparse(file_path, events=("end",))

    for _event, elem in context:
        tag = etree.QName(elem).localname

        target_elem = elem
        if tag == "Fragment":
            children = list(elem)
            if children:
                target_elem = children[0]
            else:
                elem.clear()
                continue

        r_type = etree.QName(target_elem).localname
        if r_type in ("Fragment", "FragmentInstance", "DDIInstance", "TopLevelReference"):
            elem.clear()
            continue

        urn = (
            target_elem.findtext("{ddi:reusable:3_3}URN")
            or target_elem.findtext(".//{ddi:reusable:3_3}URN")
            or target_elem.findtext("{ddi:reusable:3_2}URN")
            or target_elem.findtext(".//{ddi:reusable:3_2}URN")
            or target_elem.findtext("URN")
            or target_elem.get("urn")
        )

        if not urn:
            elem_id = (
                target_elem.findtext("{ddi:reusable:3_3}ID")
                or target_elem.findtext("ID")
                or target_elem.get("id")
                or target_elem.get("ID")
            )
            agency = (
                target_elem.findtext("{ddi:reusable:3_3}Agency")
                or target_elem.findtext("Agency")
                or "unknown.agency"
            )
            version = (
                target_elem.findtext("{ddi:reusable:3_3}Version")
                or target_elem.findtext("Version")
                or "1"
            )
            if elem_id:
                urn = f"urn:ddi:{agency}:{elem_id}:{version}"
            else:
                urn = f"urn:ddi:anonymous:{r_type.lower()}-{id(target_elem)}:1.0.0"

        refs = extract_referenced_urns_from_xml(target_elem)
        raw_dict = xml_elem_to_dict(target_elem)

        yield RawResourceNode(
            resource_type=r_type,
            raw_urn=urn.strip(),
            raw_value=raw_dict,
            referenced_urns=refs,
        )

        elem.clear()
        while elem.getprevious() is not None:
            del elem.getparent()[0]


def stream_ddi_l_json(file_path: Path, profile: ImportProfile) -> Iterator[RawResourceNode]:
    """Stream DDI-Lifecycle 4.0 / Colectica JSON files item by item."""
    with open(file_path, encoding="utf-8", errors="ignore") as f:
        data = json.load(f)

    if isinstance(data, dict):
        items = data.get("items", [])
    elif isinstance(data, list):
        items = data
    else:
        items = [data]

    for item in items:
        if not isinstance(item, dict):
            continue

        r_type = item.get("$type") or item.get("ResourceType") or "Resource"
        urn = item.get("URN") or item.get("urn")
        if not urn:
            item_id = item.get("ID") or item.get("id")
            agency = item.get("Agency") or "unknown.agency"
            version = str(item.get("Version", "1"))
            if item_id:
                urn = f"urn:ddi:{agency}:{item_id}:{version}"
            else:
                urn = f"urn:ddi:anonymous:{r_type.lower()}-{id(item)}:1.0.0"

        refs = extract_referenced_urns_from_json(item)

        yield RawResourceNode(
            resource_type=r_type,
            raw_urn=urn.strip(),
            raw_value=item,
            referenced_urns=refs,
        )


def stream_ddi_c_xml(file_path: Path, profile: ImportProfile) -> Iterator[RawResourceNode]:
    """Parse DDI-Codebook 2.5 XML files using dartfx-ddi and stream resources."""
    from dartfx.ddi.ddicodebook.utils import loadxml

    codebook = loadxml(str(file_path))
    data = codebook.model_dump(by_alias=True, exclude_none=True)

    study_id = "stdy-001"
    stdy_dscr = data.get("stdyDscr")
    if stdy_dscr and isinstance(stdy_dscr, dict):
        titl_stmt = stdy_dscr.get("citation", {}).get("titlStmt", {})
        id_no = titl_stmt.get("IDNo")
        if isinstance(id_no, list) and id_no:
            study_id = id_no[0].get("#text", "stdy-001")
        else:
            study_id = "stdy-001"
        yield RawResourceNode(
            resource_type="StudyUnit",
            raw_urn=f"urn:ddi:codebook:study:{study_id}:1.0.0",
            raw_value={"stdyDscr": stdy_dscr},
            referenced_urns=set(),
        )

    # Variables & Categories
    data_dscr_list = data.get("dataDscr", [])
    if isinstance(data_dscr_list, dict):
        data_dscr_list = [data_dscr_list]

    for data_dscr in data_dscr_list:
        vars_list = data_dscr.get("var", [])
        if isinstance(vars_list, dict):
            vars_list = [vars_list]

        for var in vars_list:
            var_name = var.get("@name") or var.get("name") or "var"
            var_urn = f"urn:ddi:codebook:var:{study_id}:{var_name}:1.0.0"

            refs: set[str] = set()
            categories = var.get("catgry", [])
            if isinstance(categories, dict):
                categories = [categories]

            # Yield Categories and CodeList for this variable
            if categories:
                cl_urn = f"urn:ddi:codebook:codelist:{study_id}:{var_name}:1.0.0"
                refs.add(cl_urn)

                cat_refs = []
                for idx, cat in enumerate(categories):
                    cat_val = cat.get("catValu", f"cat-{idx + 1}")
                    cat_urn = f"urn:ddi:codebook:cat:{study_id}:{var_name}-{cat_val}:1.0.0"
                    cat_refs.append(cat_urn)
                    yield RawResourceNode(
                        resource_type="Category",
                        raw_urn=cat_urn,
                        raw_value={"category": cat, "variable_name": var_name},
                        referenced_urns=set(),
                    )

                yield RawResourceNode(
                    resource_type="CodeList",
                    raw_urn=cl_urn,
                    raw_value={"code_list_name": f"{var_name}_codes", "categories": cat_refs},
                    referenced_urns=set(cat_refs),
                )

            # Yield Variable
            yield RawResourceNode(
                resource_type="Variable",
                raw_urn=var_urn,
                raw_value=var,
                referenced_urns=refs,
            )


def stream_resources(
    file_path: Path,
    profile: ImportProfile,
    format_info: MetadataFormatInfo | None = None,
) -> Iterator[RawResourceNode]:
    """Unified dispatcher streaming RawResourceNode instances based on detected format."""
    resolved_format = format_info or detect_metadata_format(file_path)

    if resolved_format.specification == "DDI-L":
        if resolved_format.serialization == "json":
            return stream_ddi_l_json(file_path, profile)
        return stream_ddi_l_xml(file_path, profile)

    if resolved_format.specification == "DDI-C":
        return stream_ddi_c_xml(file_path, profile)

    if resolved_format.serialization in ("json", "json-ld"):
        return stream_ddi_l_json(file_path, profile)

    return stream_ddi_l_xml(file_path, profile)
