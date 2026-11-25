"""Pure deterministic metadata import orchestrator (`fairwddi import <file>`).

Executes:
1. Preflight format detection and validation.
2. Optional DDI-Codebook -> DDI-Lifecycle 4.0 upgrade on disk (preserving intra-file
   deduplication and selectable CategoryScheme granularity).
3. Deterministic zero-write import plan (`plan_import`).
4. Direct database load (`execute_import`) unless `dry_run=True`.

Contains ZERO harmonization or cross-file comparison logic.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from fairwddi.importer.loader import execute_import, plan_import
from fairwddi.importer.preflight import run_preflight_check, upgrade_ddic_to_ddil


def run_import(
    file_path: str | Path,
    profile: str = "request",
    output_dir: str | Path | None = None,
    agency: str | None = None,
    id_strategy: str = "hierarchical",
    harmonize_codes: bool = True,
    harmonize_questions: bool = True,
    category_scheme_mode: Literal["single", "per_codelist"] = "single",
    dry_run: bool = False,
    force_reload: bool = False,
    auto_approve: bool = False,
) -> dict[str, Any]:
    """Execute the pure deterministic FAIRwDDI import pipeline on a metadata file.

    Stages:

    1. Preflight readiness inspection (and explicit DDI-C -> DDI-L 4.0 upgrade on disk
       when the input file is DDI-Codebook).
    2. Deterministic Import Plan (`plan_import`) with zero DB writes.
    3. Direct Import Execution (`execute_import`) into ReQuest core tables + `IngestBatch`
       receipt (unless `dry_run=True`).
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

    target_import_file = src_path
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
            harmonize_codes=harmonize_codes,
            harmonize_questions=harmonize_questions,
            category_scheme_mode=category_scheme_mode,
        )
        target_import_file = Path(upgrade_result["output_file"])

    import_plan = plan_import(
        file_path=target_import_file,
        profile=profile,
        output_dir=output_dir,
        force_reload=force_reload,
        auto_approve=auto_approve,
    )
    if dry_run:
        return {
            "status": "planned_only",
            "stage": "import",
            "job_id": import_plan.job_id,
            "upgrade_result": upgrade_result,
            "import_plan": import_plan,
        }

    if not import_plan.is_ready_to_execute(auto_approve=auto_approve):
        return {
            "status": "halted_at_import_plan",
            "stage": "import",
            "job_id": import_plan.job_id,
            "pending_review_count": import_plan.pending_review_count,
            "error_count": import_plan.error_count,
            "upgrade_result": upgrade_result,
            "import_plan": import_plan,
        }

    import_result = execute_import(
        import_plan,
        profile=profile,
        force_reload=force_reload,
        auto_approve=auto_approve,
    )
    batch_id = import_result.get("batch_id")

    return {
        "status": "completed",
        "batch_id": batch_id,
        "upgrade_result": upgrade_result,
        "import_result": import_result,
    }
