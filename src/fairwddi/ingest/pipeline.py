"""End-to-end ingestion pipeline orchestrator (`fairwddi ingest run`)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fairwddi.ingest.harmonizer import apply_harmonization, plan_harmonization
from fairwddi.ingest.preflight import run_preflight_check, upgrade_ddic_to_ddil
from fairwddi.ingest.promoter import apply_promotion, plan_promotion
from fairwddi.ingest.staging import stage_metadata_file


def run_ingestion_pipeline(
    file_path: str | Path,
    profile: str = "request",
    output_dir: str | Path | None = None,
    agency: str | None = None,
    id_strategy: str = "hierarchical",
    stage_only: bool = False,
    harmonize: bool = False,
    compact_after_promote: bool = False,
    force_reload: bool = False,
    auto_approve: bool = False,
) -> dict[str, Any]:
    """Execute the multi-stage FAIRwDDI ingestion pipeline on a metadata file.

    Stages:
    1. Preflight check (and explicit DDI-C -> DDI-L 4.0 upgrade on disk if input is DDI-C).
    2. Stage into StagedImport + StagedResourceNode.
    3. Plan & apply core promotion (unless stage_only=True).
    4. Optional comparison & harmonization (when harmonize=True).
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

    target_stage_file = src_path
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
        )
        target_stage_file = Path(upgrade_result["output_file"])

    stage_result = stage_metadata_file(
        file_path=target_stage_file,
        profile=profile,
        force_reload=force_reload,
    )
    import_id = stage_result.get("staged_import_id")
    if stage_only or import_id is None:
        return {
            "status": "staged_only",
            "stage": "stage",
            "staged_import_id": import_id,
            "upgrade_result": upgrade_result,
            "stage_result": stage_result,
        }

    promo_plan = plan_promotion(
        import_id=import_id,
        output_dir=output_dir,
        auto_approve=auto_approve,
    )
    if not promo_plan.is_ready_to_execute(auto_approve=auto_approve):
        return {
            "status": "halted_at_promote_plan",
            "stage": "promote",
            "staged_import_id": import_id,
            "job_id": promo_plan.job_id,
            "pending_review_count": promo_plan.pending_review_count,
            "promote_plan": promo_plan,
        }

    promo_result = apply_promotion(
        promo_plan,
        auto_approve=auto_approve,
        compact=compact_after_promote,
    )

    harmonize_result: dict[str, Any] | None = None
    if harmonize:
        harm_plan = plan_harmonization(
            import_id=import_id,
            output_dir=output_dir,
            auto_approve=auto_approve,
        )
        if harm_plan.is_ready_to_execute(auto_approve=auto_approve):
            harmonize_result = apply_harmonization(harm_plan, auto_approve=auto_approve)
        else:
            return {
                "status": "halted_at_harmonize_plan",
                "stage": "harmonize",
                "staged_import_id": import_id,
                "promote_result": promo_result,
                "harmonize_plan": harm_plan,
            }

    return {
        "status": "completed",
        "staged_import_id": import_id,
        "upgrade_result": upgrade_result,
        "stage_result": stage_result,
        "promote_result": promo_result,
        "harmonize_result": harmonize_result,
    }
