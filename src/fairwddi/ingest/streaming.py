"""Streaming parsers and resource extractors for DDI metadata formats.

Streams DDI-Lifecycle 3.x XML, DDI-Lifecycle 4.0 JSON/JSONL, and DDI-Codebook 2.5 XML
in constant O(1) memory, yielding structured in-memory `RawResourceNode` payloads
directly to preflight and core ingestion without intermediate database staging.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Self

from lxml import etree
from pydantic import BaseModel, ConfigDict, Field, model_validator

from fairwddi.ingest.detector import MetadataFormatInfo, detect_metadata_format
from fairwddi.ingest.profiles import ImportProfile


class RawResourceNode(BaseModel):
    """Individual extracted metadata element yielded during streaming."""

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
    """Recursively convert an lxml XML element to a clean structured JSON dict or scalar."""
    result: dict[str, Any] = {}

    for k, v in elem.attrib.items():
        attr_name = etree.QName(k).localname if "}" in k else k
        if "lang" in k.lower():
            attr_name = "xml:lang"
        result[f"@{attr_name}"] = v

    text = elem.text.strip() if elem.text and elem.text.strip() else None

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

    if not elem.attrib and not children_by_tag:
        return text or ""

    if text is not None and "#text" not in result:
        result["#text"] = text

    return result


def resource_to_json(resource: Any) -> dict[str, Any]:
    """Serialize any metadata resource (model instance, XML element, or dict) to a JSON dict."""
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
    "PhysicalInstance",
    "VariableStatistics",
    "Group",
    "DataCollection",
    "DataRelationship",
    "Organization",
    "OrganizationScheme",
}


def stream_ddi_l_xml(file_path: Path, profile: ImportProfile) -> Iterator[RawResourceNode]:
    """Stream DDI-Lifecycle 3.x XML files element-by-element using iterparse."""
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


def _flatten_nested_ddi4_dict(root_item: dict[str, Any]) -> list[dict[str, Any]]:
    """Unpack nested DDI 4.0 RC1 resources from a root StudyUnit or ResourcePackage dict."""
    flattened: list[dict[str, Any]] = []
    seen_urns: set[str] = set()

    def _visit(node: Any) -> None:
        if isinstance(node, list):
            for child in node:
                _visit(child)
            return
        if not isinstance(node, dict):
            return
        r_type = node.get("$type") or node.get("ResourceType")
        is_substantive = bool(
            r_type
            and r_type in DDI_IDENTIFIABLE_RESOURCE_TAGS
            and len(
                node.keys()
                - {"$type", "ResourceType", "URN", "urn", "Agency", "ID", "Version", "TypeOfObject"}
            )
            > 0
        )
        for k, v in node.items():
            if k.endswith("Reference") and isinstance(v, (dict, list)):
                _visit(v)
        if is_substantive:
            urn = node.get("URN") or node.get("urn") or node.get("ID") or node.get("id")
            if not urn or urn not in seen_urns:
                if urn:
                    seen_urns.add(str(urn))
                flattened.append(node)

    _visit(root_item)
    return flattened or [root_item]


def _dict_to_resource_node(item: dict[str, Any]) -> RawResourceNode:
    """Convert a DDI 4.0 JSON dict into a RawResourceNode."""
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

    return RawResourceNode(
        resource_type=r_type,
        raw_urn=urn.strip(),
        raw_value=raw_dict,
        referenced_urns=refs,
    )


def stream_ddi_l_json(file_path: Path, profile: ImportProfile) -> Iterator[RawResourceNode]:
    """Stream DDI-Lifecycle 4.0 / Colectica JSON files item by item."""
    with open(file_path, encoding="utf-8", errors="ignore") as f:
        data = json.load(f)

    if isinstance(data, dict):
        if "items" in data and isinstance(data["items"], list):
            items = data["items"]
        else:
            items = _flatten_nested_ddi4_dict(data)
    elif isinstance(data, list):
        items = data
    else:
        items = [data]

    for item in items:
        if not isinstance(item, dict):
            continue
        yield _dict_to_resource_node(item)


def stream_ddi_l_jsonl(file_path: Path, profile: ImportProfile) -> Iterator[RawResourceNode]:
    """Stream DDI-Lifecycle 4.0 JSON Lines (.jsonl) files in O(1) memory."""
    with open(file_path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            item = json.loads(stripped)
            if isinstance(item, dict):
                yield _dict_to_resource_node(item)


def stream_ddi_c_xml(file_path: Path, profile: ImportProfile) -> Iterator[RawResourceNode]:
    """Parse DDI-Codebook 2.5 XML files using dartfx-ddi and stream resources."""
    from dartfx.ddi.ddicodebook.utils import loadxml

    codebook = loadxml(str(file_path))
    data = codebook.model_dump(by_alias=True, exclude_none=True)

    study_id = "stdy-001"
    stdy_dscr = data.get("stdyDscr")
    if isinstance(stdy_dscr, list) and stdy_dscr:
        stdy_dscr = stdy_dscr[0]
    if stdy_dscr and isinstance(stdy_dscr, dict):
        citation = stdy_dscr.get("citation", {})
        if isinstance(citation, list) and citation:
            citation = citation[0]
        titl_stmt = citation.get("titlStmt", {}) if isinstance(citation, dict) else {}
        if isinstance(titl_stmt, list) and titl_stmt:
            titl_stmt = titl_stmt[0]
        id_no = titl_stmt.get("IDNo") if isinstance(titl_stmt, dict) else None
        if isinstance(id_no, list) and id_no:
            first_id = id_no[0]
            study_id = (
                first_id.get("content") or first_id.get("#text") or "stdy-001"
                if isinstance(first_id, dict)
                else str(first_id)
            )
        elif isinstance(id_no, dict):
            study_id = id_no.get("content") or id_no.get("#text") or "stdy-001"
        yield RawResourceNode(
            resource_type="StudyUnit",
            raw_urn=f"urn:ddi:codebook:study:{study_id}:1.0.0",
            raw_value={"stdyDscr": stdy_dscr},
            referenced_urns=set(),
        )

    file_dscr_list = data.get("fileDscr", [])
    if isinstance(file_dscr_list, dict):
        file_dscr_list = [file_dscr_list]
    for idx, f_dscr in enumerate(file_dscr_list, start=1):
        if isinstance(f_dscr, dict):
            f_id = f_dscr.get("@ID") or f_dscr.get("ID") or f"F{idx}"
            yield RawResourceNode(
                resource_type="PhysicalInstance",
                raw_urn=f"urn:ddi:codebook:file:{study_id}:{f_id}:1.0.0",
                raw_value=f_dscr,
                referenced_urns=set(),
            )

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

            if categories:
                cl_urn = f"urn:ddi:codebook:codelist:{study_id}:{var_name}:1.0.0"
                refs.add(cl_urn)

                cat_refs = []
                for idx, cat in enumerate(categories):
                    cat_val = cat.get("catValu", f"cat-{idx + 1}")
                    if isinstance(cat_val, list) and cat_val:
                        cat_val = cat_val[0]
                    if isinstance(cat_val, dict):
                        cat_val = cat_val.get("content") or cat_val.get("#text") or f"cat-{idx + 1}"
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
        if resolved_format.serialization == "jsonl":
            return stream_ddi_l_jsonl(file_path, profile)
        if resolved_format.serialization == "json":
            return stream_ddi_l_json(file_path, profile)
        return stream_ddi_l_xml(file_path, profile)

    if resolved_format.specification == "DDI-C":
        return stream_ddi_c_xml(file_path, profile)

    if resolved_format.serialization == "jsonl":
        return stream_ddi_l_jsonl(file_path, profile)
    if resolved_format.serialization in ("json", "json-ld"):
        return stream_ddi_l_json(file_path, profile)

    return stream_ddi_l_xml(file_path, profile)
