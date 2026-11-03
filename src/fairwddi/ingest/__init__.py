"""FAIRwDDI Phase 2 Ingestion Package (`fairwddi.ingest`).

Provides a multi-stage, review-gated ingestion and harmonization pipeline:
1. `preflight`: Readiness check (`run_preflight_check`) and DDI-C -> DDI-L upgrade.
2. `stage`: Database staging (`stage_metadata_file`) and JSONB compaction (`cleanup_staged_import`).
3. `promote`: Core table promotion (`plan_promotion`, `apply_promotion`) and `undo_promotion`.
4. `compare`: Cross-survey similarity (`compare_batch`) and discovery (`discover_candidates`).
5. `harmonize`: Review-gated harmonization (`plan_harmonization`, `apply_harmonization`, `undo`).
6. `pipeline`: End-to-end convenience runner (`run_ingestion_pipeline`).
"""

from __future__ import annotations

from fairwddi.importer.detector import MetadataFormatInfo, detect_metadata_format
from fairwddi.importer.profiles import (
    ImportProfile,
    ImportStrategies,
    list_available_profiles,
    load_profile,
)
from fairwddi.importer.streaming import (
    RawResourceNode,
    stream_ddi_c_xml,
    stream_ddi_l_json,
    stream_ddi_l_jsonl,
    stream_ddi_l_xml,
    stream_resources,
)
from fairwddi.ingest.comparator import compare_batch, discover_candidates
from fairwddi.ingest.harmonizer import (
    apply_harmonization,
    plan_harmonization,
    undo_harmonization,
)
from fairwddi.ingest.pipeline import run_ingestion_pipeline
from fairwddi.ingest.plan import IngestPlan, PlanActionItem, PlanIssue, ReviewGate
from fairwddi.ingest.preflight import run_preflight_check, upgrade_ddic_to_ddil
from fairwddi.ingest.promoter import (
    apply_promotion,
    compute_resource_hashes,
    parse_ddi_urn,
    plan_promotion,
    undo_promotion,
)
from fairwddi.ingest.staging import (
    ProtectedImportError,
    cleanup_staged_import,
    compute_file_sha256,
    delete_staged_import,
    get_import_statistics,
    get_import_statistics_as_json,
    get_import_statistics_as_markdown,
    list_staged_imports,
    query_staged_resources,
    stage_metadata_file,
)

__all__ = [
    "IngestPlan",
    "PlanActionItem",
    "PlanIssue",
    "ReviewGate",
    "MetadataFormatInfo",
    "detect_metadata_format",
    "ImportProfile",
    "ImportStrategies",
    "load_profile",
    "list_available_profiles",
    "RawResourceNode",
    "stream_resources",
    "stream_ddi_l_xml",
    "stream_ddi_l_json",
    "stream_ddi_l_jsonl",
    "stream_ddi_c_xml",
    "run_preflight_check",
    "upgrade_ddic_to_ddil",
    "stage_metadata_file",
    "cleanup_staged_import",
    "delete_staged_import",
    "ProtectedImportError",
    "compute_file_sha256",
    "get_import_statistics",
    "get_import_statistics_as_json",
    "get_import_statistics_as_markdown",
    "list_staged_imports",
    "query_staged_resources",
    "parse_ddi_urn",
    "compute_resource_hashes",
    "plan_promotion",
    "apply_promotion",
    "undo_promotion",
    "compare_batch",
    "discover_candidates",
    "plan_harmonization",
    "apply_harmonization",
    "undo_harmonization",
    "run_ingestion_pipeline",
]
