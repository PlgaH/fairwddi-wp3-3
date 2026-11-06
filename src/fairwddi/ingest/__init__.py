"""FAIRwDDI Phase 2 Ingestion Package (`fairwddi.ingest`).

Provides a direct file-to-core-tables, review-gated ingestion and harmonization pipeline:
1. `preflight`: Readiness check (`run_preflight_check`), profiles, and DDI-C -> DDI-L upgrade.
2. `ingest` (`loader`): Direct streaming ingestion (`plan_ingestion`, `apply_ingestion`),
   `IngestBatch` receipts (`list_ingest_batches`, `get_ingest_batch_status`), and `undo_ingestion`.
3. `compare`: Cross-survey similarity (`compare_batch`) and discovery (`discover_candidates`).
4. `harmonize`: Review-gated harmonization (`plan_harmonization`, `apply_harmonization`, `undo`).
5. `pipeline`: End-to-end convenience runner (`run_ingestion_pipeline`).
"""

from __future__ import annotations

from fairwddi.ingest.comparator import compare_batch, discover_candidates
from fairwddi.ingest.detector import MetadataFormatInfo, compute_file_sha256, detect_metadata_format
from fairwddi.ingest.harmonizer import (
    apply_harmonization,
    plan_harmonization,
    undo_harmonization,
)
from fairwddi.ingest.loader import (
    apply_ingestion,
    compute_resource_hashes,
    execute_ingestion,
    get_ingest_batch_status,
    list_ingest_batches,
    parse_ddi_urn,
    plan_ingestion,
    undo_ingestion,
)
from fairwddi.ingest.pipeline import run_ingestion_pipeline
from fairwddi.ingest.plan import IngestPlan, PlanActionItem, PlanIssue, ReviewGate
from fairwddi.ingest.preflight import run_preflight_check, upgrade_ddic_to_ddil
from fairwddi.ingest.profiles import (
    ImportProfile,
    ImportStrategies,
    list_available_profiles,
    load_profile,
)
from fairwddi.ingest.streaming import (
    RawResourceNode,
    stream_ddi_c_xml,
    stream_ddi_l_json,
    stream_ddi_l_jsonl,
    stream_ddi_l_xml,
    stream_resources,
)

__all__ = [
    "IngestPlan",
    "PlanActionItem",
    "PlanIssue",
    "ReviewGate",
    "MetadataFormatInfo",
    "detect_metadata_format",
    "compute_file_sha256",
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
    "parse_ddi_urn",
    "compute_resource_hashes",
    "plan_ingestion",
    "apply_ingestion",
    "execute_ingestion",
    "undo_ingestion",
    "list_ingest_batches",
    "get_ingest_batch_status",
    "compare_batch",
    "discover_candidates",
    "plan_harmonization",
    "apply_harmonization",
    "undo_harmonization",
    "run_ingestion_pipeline",
]
