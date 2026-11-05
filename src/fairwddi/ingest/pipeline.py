"""End-to-end ingestion pipeline orchestrator (`fairwddi ingest run`)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fairwddi.ingest.harmonizer import apply_harmonization, plan_harmonization
from fairwddi.ingest.loader import apply_ingestion, plan_ingestion
from fairwddi.ingest.preflight import run_preflight_check, upgrade_ddic_to_ddil


def run_ingestion_pipeline(
    file_path: str | Path,
    profile: str = "request",
    output_dir: str | Path | None = None,
    agency: str | None = None,
    id_strategy: str = "hierarchical",
    plan_only: bool = False,
    harmonize: bool = False,
    force_reload: bool = False,
    auto_approve: bool = False,
) -> dict[str, Any]:
    """Execute the multi-stage FAIRwDDI ingestion pipeline on a metadata file.

    Stages:
    1. Preflight check (and explicit DDI-C -> DDI-L 4.0 upgrade on disk if input is DDI-C).
    2. Direct Ingestion Plan (`plan_ingestion`) with zero DB writes.
    3. Direct Ingestion Apply (`apply_ingestion`) into ReQuest core tables + `IngestBatch` receipt
       (unless `plan_only=True`).
    4. Optional comparison & harmonization (when `harmonize=True`).
    """
    src_path = Path(file_path).resolve()
    preflight_plan = run_preflight_check(
        src_path,
        profile=profile,
        output_dir=output_dir,
        auto_approve=auto_approve,
    )

    if not preflight_plan.is_ready_to_execute(auto_approve=auto_approve) and not force_reload:
        return {
            "status": "halted_at_preflight",
            "stage": "preflight",
            "job_id": preflight_plan.job_id,
            "pending_review_count": preflight_plan.pending_review_count,
            "error_count": preflight_plan.error_count,
            "preflight_plan": preflight_plan,
        }

    target_ingest_file = src_path
    upgrade_result: dict[str, Any] | None = None
    if preflight_plan.summary.get("specification") == "DDI-C":
        upgrade_out = (
            Path(output_dir) / f"{src_path.stem}.ddi40.json" if output_dir is not None else None
        )
        upgrade_result = upgrade_ddic_to_ddil(
            src_path,
            output_path=upgrade_out,
            output_format="ddi4-json",
            agency=agency,
            id_strategy=id_strategy,
            harmonize_codes=True,
            harmonize_questions=True,
        )
        target_ingest_file = Path(upgrade_result["output_file"])

    ingest_plan = plan_ingestion(
        file_path=target_ingest_file,
        profile=profile,
        output_dir=output_dir,
        force_reload=force_reload,
        auto_approve=auto_approve,
    )
    if plan_only:
        return {
            "status": "planned_only",
            "stage": "ingest",
            "job_id": ingest_plan.job_id,
            "upgrade_result": upgrade_result,
            "ingest_plan": ingest_plan,
        }

    if not ingest_plan.is_ready_to_execute(auto_approve=auto_approve):
        return {
            "status": "halted_at_ingest_plan",
            "stage": "ingest",
            "job_id": ingest_plan.job_id,
            "pending_review_count": ingest_plan.pending_review_count,
            "error_count": ingest_plan.error_count,
            "upgrade_result": upgrade_result,
            "ingest_plan": ingest_plan,
        }

    ingest_result = apply_ingestion(
        ingest_plan,
        profile=profile,
        force_reload=force_reload,
        auto_approve=auto_approve,
    )
    batch_id = ingest_result.get("batch_id")

    harmonize_result: dict[str, Any] | None = None
    if harmonize and batch_id is not None:
        harm_plan = plan_harmonization(
            batch_id=batch_id,
            output_dir=output_dir,
            auto_approve=auto_approve,
        )
        if harm_plan.is_ready_to_execute(auto_approve=auto_approve):
            harmonize_result = apply_harmonization(harm_plan, auto_approve=auto_approve)
        else:
            return {
                "status": "halted_at_harmonize_plan",
                "stage": "harmonize",
                "batch_id": batch_id,
                "ingest_result": ingest_result,
                "harmonize_plan": harm_plan,
            }

    return {
        "status": "completed",
        "batch_id": batch_id,
        "upgrade_result": upgrade_result,
        "ingest_result": ingest_result,
        "harmonize_result": harmonize_result,
    }
