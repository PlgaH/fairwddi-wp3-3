"""Stage 2a (Staging): Database staging, query helpers, and payload compaction/cleanup."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from fairwddi.importer.detector import detect_metadata_format
from fairwddi.importer.importer import (
    ProtectedImportError,
    compute_file_sha256,
    delete_staged_import,
    import_metadata_file,
)
from fairwddi.importer.profiles import ImportProfile
from fairwddi.importer.query import (
    get_import_statistics,
    get_import_statistics_as_json,
    get_import_statistics_as_markdown,
    list_staged_imports,
    query_staged_resources,
)
from fairwddi.ingest.preflight import upgrade_ddic_to_ddil


def stage_metadata_file(
    file_path: str | Path,
    profile: str | Path | ImportProfile | None = None,
    dry_run: bool = False,
    force_reload: bool = False,
    auto_upgrade_ddic: bool = False,
    agency: str | None = None,
    id_strategy: str = "hierarchical",
    log_dir: str | Path | None = None,
    progress_callback: Callable[[str, int, int | None, str | None], None] | None = None,
) -> dict[str, Any]:
    """Load a DDI-Lifecycle (or optionally auto-upgraded DDI-Codebook) file into StagedImport."""
    path = Path(file_path).resolve()
    fmt = detect_metadata_format(path)
    upgraded_info: dict[str, Any] | None = None

    if fmt.specification == "DDI-C" and auto_upgrade_ddic:
        upgraded_info = upgrade_ddic_to_ddil(
            path,
            output_format="ddi4-json",
            agency=agency,
            id_strategy=id_strategy,
            harmonize_codes=True,
        )
        path = Path(upgraded_info["output_file"])

    result = import_metadata_file(
        file_path=path,
        profile=profile,
        dry_run=dry_run,
        force_reload=force_reload,
        log_dir=log_dir,
        progress_callback=progress_callback,
    )
    if upgraded_info is not None:
        result["upgraded_from_ddic"] = upgraded_info["source_file"]
        result["upgraded_ddil_file"] = upgraded_info["output_file"]
    return result


def cleanup_staged_import(
    import_id: int | None = None,
    compact_only: bool = True,
    force: bool = False,
    delete_log_file: bool = False,
) -> dict[str, Any]:
    """Compact or delete staged import batches to prevent database JSONB storage bloat.

    Args:
        import_id: Optional StagedImport PK. Required when compact_only=False.
                   When compact_only=True and import_id is None, compacts all promoted nodes.
        compact_only: If True (default), strips bulky `raw_value` JSONB from promoted/normalized
                      nodes while preserving lightweight lineage rows (`raw_urn`, `canonical_urn`,
                      `status`) needed for `promote undo` and URN alias auditing.
                      If False, permanently deletes the StagedImport and its StagedResourceNodes.
        force: Force deletion even if nodes have been promoted.
        delete_log_file: Delete associated session log file when compact_only=False.
    """
    from fairwddi.models import StagedImport, StagedResourceNode

    if not compact_only:
        if import_id is None:
            raise ValueError("import_id is required when compact_only=False (full deletion).")
        del_res = delete_staged_import(
            import_id=import_id,
            force=force,
            delete_log_file=delete_log_file,
        )
        del_res["mode"] = "deleted"
        return del_res

    qs = StagedResourceNode.objects.filter(status__in=["normalized", "promoted"])
    if import_id is not None:
        if not StagedImport.objects.filter(id=import_id).exists():
            raise ValueError(f"StagedImport #{import_id} does not exist.")
        qs = qs.filter(staged_import_id=import_id)

    compacted_count = 0
    for node in qs.iterator(chunk_size=500):
        if isinstance(node.raw_value, dict) and node.raw_value.get("_compacted") is True:
            continue
        node.raw_value = {"_compacted": True}
        node.save(update_fields=["raw_value"])
        compacted_count += 1

    return {
        "mode": "compacted",
        "staged_import_id": import_id,
        "compacted_nodes_count": compacted_count,
    }


__all__ = [
    "ProtectedImportError",
    "compute_file_sha256",
    "stage_metadata_file",
    "cleanup_staged_import",
    "delete_staged_import",
    "get_import_statistics",
    "get_import_statistics_as_json",
    "get_import_statistics_as_markdown",
    "list_staged_imports",
    "query_staged_resources",
]
