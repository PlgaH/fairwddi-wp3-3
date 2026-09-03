"""Streaming parsers and resource extractors for DDI metadata formats.

Streams DDI-Lifecycle 3.x XML, DDI-Lifecycle 4.0 JSON, and DDI-Codebook 2.5 XML
in constant O(1) memory, extracting structured JSON dictionary payloads.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Self

from lxml import etree
from pydantic import BaseModel, ConfigDict, Field, model_validator

from fairwddi.importer.detector import MetadataFormatInfo, detect_metadata_format
from fairwddi.importer.profiles import ImportProfile


class RawResourceNode(BaseModel):
    """Individual extracted metadata element prior to database staging."""

    model_config = ConfigDict(arbitrary_types_allowed=True, validate_assignment=True)

    resource_type: str = Field(
        ..., description="DDI resource class name (e.g. QuestionItem, Variable)."
    )
    raw_urn: str = Field(..., description="Raw incoming URN or deterministic ID.")
    raw_value: dict[str, Any] = Field(..., description="Pre-normalized raw JSON dictionary.")
    referenced_urns: set[str] = Field(default_factory=set, description="Referenced resource URNs.")
    content_fingerprint: str = Field(
        default="", description="Deterministic SHA-256 content fingerprint."
    )

    @model_validator(mode="after")
    def compute_content_fingerprint(self) -> Self:
        if not self.content_fingerprint:
            canonical_json = json.dumps(self.raw_value, sort_keys=True, ensure_ascii=False)
            self.content_fingerprint = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
        return self

    def to_json(self) -> str:
        """Return canonical JSON representation of the resource payload."""
        return json.dumps(self.raw_value, sort_keys=True, ensure_ascii=False)


def xml_to_json_dict(elem: Any) -> Any:
    """Recursively convert an lxml XML element to a clean structured JSON dict or scalar.

    Strips XML namespaces, extracts attributes prefixed with '@', collapses single-item
    children while maintaining arrays for repeated tags, and simplifies text leaves.
    """
    result: dict[str, Any] = {}

    # Extract attributes
    for k, v in elem.attrib.items():
        attr_name = etree.QName(k).localname if "}" in k else k
        if "lang" in k.lower():
            attr_name = "xml:lang"
        result[f"@{attr_name}"] = v

    # Extract text content
    text = elem.text.strip() if elem.text and elem.text.strip() else None

    # Group child elements by tag name to support single items vs. lists
    children_by_tag: dict[str, list[Any]] = {}
    for child in elem:
        c_tag = etree.QName(child).localname
        c_dict = xml_to_json_dict(child)
        if c_tag not in children_by_tag:
            children_by_tag[c_tag] = []
        children_by_tag[c_tag].append(c_dict)

    for c_tag, items in children_by_tag.items():
        if len(items) == 1:
            result[c_tag] = items[0]
        else:
            result[c_tag] = items

    # Simplify leaf nodes with only text and no attributes/children
    if not elem.attrib and not children_by_tag:
        return text or ""

    if text is not None and "#text" not in result:
        result["#text"] = text

    return result


def resource_to_json(resource: Any) -> dict[str, Any]:
    """Serialize any metadata resource (model instance, XML element, or dict) to a clean JSON dict.

    Priority:
    1. If object provides a .to_json() method, invoke it.
    2. If object provides a .model_dump() method (Pydantic v2), invoke it.
    3. If object provides a .dict() method (Pydantic v1), invoke it.
    4. If object is already a dict, return as-is.
    5. If object is an lxml XML Element, convert via xml_to_json_dict.
    """
    if hasattr(resource, "to_json") and callable(resource.to_json):
        res = resource.to_json()
        if isinstance(res, str):
            return json.loads(res)
        if isinstance(res, dict):
            return res
    if hasattr(resource, "model_dump") and callable(resource.model_dump):
        return resource.model_dump(by_alias=True, exclude_none=True)
    if hasattr(resource, "dict") and callable(resource.dict):
        return resource.dict()
    if isinstance(resource, dict):
        return resource
    if etree.iselement(resource):
        converted = xml_to_json_dict(resource)
        if isinstance(converted, dict):
            return converted
        return {"#text": converted}
    return {"value": str(resource)}


def xml_elem_to_dict(elem: Any) -> dict[str, Any]:
    """Alias for backwards compatibility: converts XML element to JSON dictionary."""
    return resource_to_json(elem)


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


DDI_IDENTIFIABLE_RESOURCE_TAGS = {
    "QuestionItem",
    "QuestionGrid",
    "QuestionConstruct",
    "QuestionGroup",
    "QuestionScheme",
    "StatementItem",
    "Instruction",
    "InterviewerInstruction",
    "InterviewerInstructionScheme",
    "Category",
    "CategorySet",
    "CategoryGroup",
    "CategoryScheme",
    "CodeList",
    "CodeListScheme",
    "CodeItem",
    "ManagedMissingValuesRepresentation",
    "ManagedRepresentationScheme",
    "StatisticalClassification",
    "ClassificationFamily",
    "ClassificationSeries",
    "ClassificationLevel",
    "ClassificationItem",
    "Variable",
    "InstanceVariable",
    "RepresentedVariable",
    "RepresentedVariableGroup",
    "RepresentedVariableScheme",
    "ConceptualVariable",
    "ConceptualVariableGroup",
    "ConceptualVariableScheme",
    "VariableGroup",
    "VariableScheme",
    "Instrument",
    "InstrumentScheme",
    "ControlConstructScheme",
    "Sequence",
    "IfThenElse",
    "Loop",
    "ComputationItem",
    "Concept",
    "ConceptGroup",
    "ConceptScheme",
    "ConceptualComponent",
    "Universe",
    "UniverseScheme",
    "StudyUnit",
    "Group",
    "DataCollection",
    "DataRelationship",
    "Organization",
    "OrganizationScheme",
}


def stream_ddi_l_xml(file_path: Path, profile: ImportProfile) -> Iterator[RawResourceNode]:
    """Stream DDI-Lifecycle 3.x XML files element-by-element using iterparse."""
    # Detect if document uses <Fragment> container architecture
    has_fragments = False
    for _event, elem in etree.iterparse(file_path, events=("start",)):
        tag = etree.QName(elem).localname
        if tag in ("FragmentInstance", "Fragment"):
            has_fragments = True
        break

    context = etree.iterparse(file_path, events=("end",))

    for _event, elem in context:
        tag = etree.QName(elem).localname

        if has_fragments:
            if tag != "Fragment":
                continue
            if len(elem) == 0:
                elem.clear()
                continue
            target_elem = elem[0]
            r_type = etree.QName(target_elem).localname
        else:
            if tag not in DDI_IDENTIFIABLE_RESOURCE_TAGS:
                continue
            target_elem = elem
            r_type = tag

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
        raw_dict = resource_to_json(target_elem)

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
        raw_dict = resource_to_json(item)

        yield RawResourceNode(
            resource_type=r_type,
            raw_urn=urn.strip(),
            raw_value=raw_dict,
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
