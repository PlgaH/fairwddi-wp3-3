"""FAIRwDDI Pure Deterministic Import Package (`fairwddi.importer`).

Provides clean, standalone metadata import with zero harmonization coupling:

- Format detection & SHA-256 fingerprinting (`detector`)
- Profile-driven resource filtering (`profiles`)
- Low-memory XML/JSON/JSONL streaming (`streaming`)
- Review-gated import plans & Markdown reports (`plan`)
- Stage 1 Preflight checks & DDI-C -> DDI-L upgrade (`preflight`)
- Stage 2 Pure deterministic loading & atomic rollback (`loader`)
- End-to-end pure import orchestrator (`pipeline`)
"""

from __future__ import annotations

from fairwddi.importer.detector import (
    MetadataFormatInfo,
    compute_file_sha256,
    detect_metadata_format,
)
from fairwddi.importer.loader import (
    compute_resource_hashes,
    execute_import,
    get_import_batch_status,
    list_import_batches,
    parse_ddi_urn,
    plan_import,
    undo_import,
)
from fairwddi.importer.pipeline import run_import
from fairwddi.importer.plan import (
    ImportActionItem,
    ImportPlan,
    PlanActionItem,
    PlanIssue,
    ReviewGate,
)
from fairwddi.importer.preflight import run_preflight_check, upgrade_ddic_to_ddil
from fairwddi.importer.profiles import (
    ImportProfile,
    ImportStrategies,
    list_available_profiles,
    load_profile,
)
from fairwddi.importer.streaming import (
    RawResourceNode,
    extract_referenced_urns_from_json,
    extract_referenced_urns_from_xml,
    resource_to_json,
    stream_resources,
    xml_elem_to_dict,
    xml_to_json_dict,
)

__all__ = [
    "MetadataFormatInfo",
    "compute_file_sha256",
    "detect_metadata_format",
    "ImportProfile",
    "ImportStrategies",
    "load_profile",
    "list_available_profiles",
    "RawResourceNode",
    "resource_to_json",
    "xml_to_json_dict",
    "xml_elem_to_dict",
    "extract_referenced_urns_from_xml",
    "extract_referenced_urns_from_json",
    "stream_resources",
    "ReviewGate",
    "PlanIssue",
    "ImportActionItem",
    "PlanActionItem",
    "ImportPlan",
    "run_preflight_check",
    "upgrade_ddic_to_ddil",
    "parse_ddi_urn",
    "compute_resource_hashes",
    "plan_import",
    "execute_import",
    "undo_import",
    "list_import_batches",
    "get_import_batch_status",
    "run_import",
]
