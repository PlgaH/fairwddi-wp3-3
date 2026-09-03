"""Metadata import orchestrator for FAIRwDDI.

Coordinates format detection, profile filtering, duplicate/drift collision handling,
streaming extraction, bulk database staging, and structured session logging.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fairwddi.importer.detector import MetadataFormatInfo, detect_metadata_format
from fairwddi.importer.logging import ImportSessionLogger
from fairwddi.importer.profiles import ImportProfile, load_profile
from fairwddi.importer.streaming import RawResourceNode, stream_resources


def compute_file_sha256(file_path: Path, chunk_size: int = 65536) -> str:
    """Compute SHA-256 digest of a physical file."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def import_metadata_file(
    file_path: str | Path,
    profile: str | Path | ImportProfile | None = None,
    import_options: dict[str, Any] | None = None,
    source_format: str | None = None,
    batch_size: int = 1000,
    dry_run: bool = False,
    force_reload: bool = False,
    import_task_id: str | None = None,
    log_dir: str | Path | None = None,
    progress_callback: Callable[[str, int, int | None, str | None], None] | None = None,
) -> dict[str, Any]:
    """Import and stage a metadata document (DDI-L, DDI-C, DDI-CDI, etc.) into the database.

    Args:
        file_path: Path to the metadata document on disk.
        profile: Profile name, path, or ImportProfile instance (defaults to 'request').
        import_options: Optional dictionary of options and configuration metadata.
        source_format: Optional explicit format override.
        batch_size: Number of resource nodes to bulk insert in each database transaction.
        dry_run: If True, parses and validates without writing to the database.
        force_reload: If True, replaces previous staged records if this file was already imported.
        import_task_id: Optional background task identifier (e.g. from django-tasks-db).
        log_dir: Optional custom directory for session log files.
        progress_callback: Optional callback receiving (stage, current, total, message).

    Returns:
        Comprehensive execution summary dictionary.
    """

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    from django.db import transaction

    from fairwddi.models import MetadataQuarantine, StagedImport, StagedResourceNode

    start_time = time.time()

    # 1. Resolve Profile
    if isinstance(profile, ImportProfile):
        active_profile = profile
    else:
        active_profile = load_profile(profile)

    if force_reload:
        active_profile.strategies.on_duplicate_file = "force_reload"

    # 2. Detect Format
    format_info = detect_metadata_format(path)
    if source_format:
        format_info = MetadataFormatInfo(
            specification=format_info.specification,
            version=format_info.version,
            serialization=format_info.serialization,
            flavor=format_info.flavor,
            root_tag_or_type=format_info.root_tag_or_type,
            canonical_slug=source_format,
        )

    # 3. Compute File Hash & Check Duplicate File
    file_sha256 = compute_file_sha256(path)
    existing_import = (
        StagedImport.objects.filter(
            file_name=path.name,
            import_options__file_sha256=file_sha256,
        ).first()
        if not dry_run
        else None
    )

    if existing_import and not dry_run:
        strategy = active_profile.strategies.on_duplicate_file
        if strategy == "skip":
            elapsed = time.time() - start_time
            return {
                "status": "already_staged",
                "staged_import_id": existing_import.id,
                "file_name": path.name,
                "file_sha256": file_sha256,
                "format_info": format_info.model_dump(),
                "profile": active_profile.name,
                "total_staged": existing_import.total_resources,
                "skipped_duplicates": 0,
                "quarantined_count": 0,
                "counts_by_type": {},
                "elapsed_seconds": elapsed,
                "throughput_per_sec": 0.0,
                "log_file": existing_import.import_options.get("log_file"),
                "message": (
                    f"File '{path.name}' was already imported "
                    f"(StagedImport #{existing_import.id}). "
                    f"Skipped per on_duplicate_file='skip'."
                ),
            }
        elif strategy == "fail":
            raise ValueError(
                f"Duplicate file import rejected: '{path.name}' (matching SHA-256) "
                f"was previously imported as StagedImport #{existing_import.id}."
            )
        elif strategy == "force_reload":
            existing_import.delete()

    # 4. Initialize Session Logger & StagedImport Record
    options_payload = dict(import_options or {})
    options_payload["file_sha256"] = file_sha256
    options_payload["profile"] = active_profile.name

    staged_import: StagedImport | None = None
    import_id_str = "dryrun"

    if not dry_run:
        staged_import = StagedImport.objects.create(
            source_format=format_info.canonical_slug,
            file_name=path.name,
            file_path=str(path),
            import_options=options_payload,
            import_task_id=import_task_id,
            status="staged",
        )
        import_id_str = str(staged_import.id)

    logger = ImportSessionLogger(import_id=import_id_str, log_dir=log_dir, dry_run=dry_run)
    logger.log_header(
        file_path=path,
        format_info=format_info,
        profile=active_profile,
        file_sha256=file_sha256,
        import_task_id=import_task_id,
    )

    if staged_import:
        staged_import.import_options["log_file"] = str(logger.path)
        staged_import.save(update_fields=["import_options"])

    # 5. First pass: Collect all referenced URNs in document if referential integrity is on
    referenced_urn_pool: set[str] = set()
    node_buffer: list[RawResourceNode] = []

    for raw_node in stream_resources(path, active_profile, format_info):
        node_buffer.append(raw_node)
        referenced_urn_pool.update(raw_node.referenced_urns)
        if progress_callback and (len(node_buffer) % 100 == 0 or len(node_buffer) < 50):
            progress_callback(
                "parse",
                len(node_buffer),
                None,
                f"Extracting {raw_node.resource_type} ({len(node_buffer):,} items)",
            )

    if progress_callback:
        progress_callback(
            "parse_done",
            len(node_buffer),
            len(node_buffer),
            f"Extracted {len(node_buffer):,} resource fragments",
        )

    # 6. Second pass: Filter, Deduplicate, Check Drift & Stage Nodes
    total_staged = 0
    skipped_duplicates = 0
    quarantined_count = 0
    counts_by_type: dict[str, int] = {}
    db_batch: list[StagedResourceNode] = []
    batch_index = 0
    total_nodes = len(node_buffer)

    raw_urns_in_import = [n.raw_urn for n in node_buffer if n.raw_urn]
    existing_nodes_map: dict[str, tuple[int, str, dict[str, Any]]] = {}
    if not dry_run and raw_urns_in_import:
        chunk_size = 900
        for i in range(0, len(raw_urns_in_import), chunk_size):
            chunk = raw_urns_in_import[i : i + chunk_size]
            for node in StagedResourceNode.objects.filter(raw_urn__in=chunk).only(
                "id", "raw_urn", "canonical_urn", "raw_value"
            ):
                existing_nodes_map[node.raw_urn] = (node.id, node.canonical_urn, node.raw_value)

    with transaction.atomic():
        for idx, raw_node in enumerate(node_buffer, 1):
            is_ref = raw_node.raw_urn in referenced_urn_pool

            if not active_profile.should_include(raw_node.resource_type, is_referenced=is_ref):
                if progress_callback and (idx % 200 == 0 or idx == total_nodes):
                    progress_callback(
                        "stage",
                        idx,
                        total_nodes,
                        f"{total_staged:,} staged, {skipped_duplicates:,} skipped",
                    )
                continue

            if raw_node.raw_urn in existing_nodes_map:
                existing_id, existing_canon_urn, existing_raw_val = existing_nodes_map[
                    raw_node.raw_urn
                ]
                is_identical = existing_raw_val == raw_node.raw_value

                if is_identical:
                    exist_strat = active_profile.strategies.on_existing_resource
                    if exist_strat == "insert_new_only":
                        skipped_duplicates += 1
                        logger.log_duplicate_skip(raw_node.raw_urn, raw_node.resource_type)
                        if progress_callback and (idx % 200 == 0 or idx == total_nodes):
                            progress_callback(
                                "stage",
                                idx,
                                total_nodes,
                                f"{total_staged:,} staged, {skipped_duplicates:,} skipped",
                            )
                        continue
                    elif exist_strat == "fail":
                        logger.close()
                        raise ValueError(
                            f"Collision error: Resource URN '{raw_node.raw_urn}' already staged."
                        )
                    elif exist_strat == "replace":
                        if not dry_run:
                            StagedResourceNode.objects.filter(id=existing_id).update(
                                staged_import=staged_import,
                                raw_value=raw_node.raw_value,
                            )
                        logger.log_info(
                            f"Replaced staged node #{existing_id} with new import payload"
                        )
                else:
                    drift_strat = active_profile.strategies.on_content_drift
                    if drift_strat == "quarantine":
                        quarantined_count += 1
                        logger.log_drift_quarantine(
                            raw_urn=raw_node.raw_urn,
                            resource_type=raw_node.resource_type,
                            conflict_reason="content_drift_without_version_increment",
                        )
                        if not dry_run:
                            MetadataQuarantine.objects.create(
                                entity_type=raw_node.resource_type,
                                incoming_urn=raw_node.raw_urn,
                                existing_content=existing_raw_val,
                                incoming_content=raw_node.raw_value,
                                conflict_type="staged_urn_drift",
                                source_file=path.name,
                                import_task_id=import_task_id,
                            )
                            db_batch.append(
                                StagedResourceNode(
                                    staged_import=staged_import,
                                    resource_type=raw_node.resource_type,
                                    raw_urn=raw_node.raw_urn,
                                    raw_value=raw_node.raw_value,
                                    status="quarantined",
                                )
                            )
                        if progress_callback and (idx % 200 == 0 or idx == total_nodes):
                            progress_callback(
                                "stage",
                                idx,
                                total_nodes,
                                f"{total_staged:,} staged, {quarantined_count:,} quarantined",
                            )
                        continue
                    elif drift_strat == "reject":
                        logger.close()
                        raise ValueError(
                            "Metadata drift error: Content mismatch detected for "
                            f"'{raw_node.raw_urn}'."
                        )
                    elif drift_strat == "overwrite":
                        if not dry_run:
                            StagedResourceNode.objects.filter(id=existing_id).update(
                                staged_import=staged_import,
                                raw_value=raw_node.raw_value,
                            )
                        logger.log_warning(f"Overwrote staged node #{existing_id} (content drift)")

            if not dry_run and staged_import:
                db_batch.append(
                    StagedResourceNode(
                        staged_import=staged_import,
                        resource_type=raw_node.resource_type,
                        raw_urn=raw_node.raw_urn,
                        raw_value=raw_node.raw_value,
                        status="staged",
                    )
                )

            total_staged += 1
            counts_by_type[raw_node.resource_type] = (
                counts_by_type.get(raw_node.resource_type, 0) + 1
            )

            if not dry_run and len(db_batch) >= batch_size:
                batch_index += 1
                StagedResourceNode.objects.bulk_create(db_batch, batch_size=batch_size)
                logger.log_batch_commit(batch_index, len(db_batch), total_staged)
                db_batch.clear()

            if progress_callback and (idx % 200 == 0 or idx == total_nodes):
                progress_callback(
                    "stage",
                    idx,
                    total_nodes,
                    f"{total_staged:,} staged, {skipped_duplicates:,} skipped",
                )

        if not dry_run and db_batch:
            batch_index += 1
            StagedResourceNode.objects.bulk_create(db_batch, batch_size=batch_size)
            logger.log_batch_commit(batch_index, len(db_batch), total_staged)
            db_batch.clear()

        if not dry_run and staged_import:
            staged_import.total_resources = total_staged
            staged_import.processed_resources = 0
            staged_import.save(update_fields=["total_resources", "processed_resources"])

    if progress_callback:
        progress_callback("stage_done", total_staged, total_nodes, "Staging completed")


    elapsed = time.time() - start_time
    throughput = total_staged / elapsed if elapsed > 0 else float(total_staged)

    summary = {
        "status": "staged" if not dry_run else "dry_run_success",
        "staged_import_id": staged_import.id if staged_import else None,
        "file_name": path.name,
        "file_sha256": file_sha256,
        "format_info": format_info.model_dump(),
        "profile": active_profile.name,
        "total_staged": total_staged,
        "skipped_duplicates": skipped_duplicates,
        "quarantined_count": quarantined_count,
        "counts_by_type": counts_by_type,
        "elapsed_seconds": round(elapsed, 3),
        "throughput_per_sec": round(throughput, 1),
        "log_file": str(logger.path),
    }

    logger.log_summary(summary)
    logger.close()

    return summary


class ProtectedImportError(Exception):
    """Raised when attempting to delete an import whose resources are in active downstream use."""

    def __init__(
        self,
        message: str,
        import_id: int,
        normalized_count: int,
        alias_count: int,
    ) -> None:
        super().__init__(message)
        self.import_id = import_id
        self.normalized_count = normalized_count
        self.alias_count = alias_count

    @property
    def harmonized_count(self) -> int:
        """Alias for backwards compatibility."""
        return self.normalized_count


def delete_staged_import(
    import_id: int,
    force: bool = False,
    delete_log_file: bool = False,
) -> dict[str, Any]:
    """Delete a StagedImport and its child StagedResourceNode records with dependency safety.

    Safety Check:
        If any resources from this import have been normalized (status='normalized'
        or canonical_urn assigned) or have active URNAlias entries, deletion will
        raise ProtectedImportError unless force=True is explicitly specified.

    Args:
        import_id: Primary key of StagedImport.
        force: If True, bypasses downstream protection checks.
        delete_log_file: If True, also deletes the session audit log file from disk.

    Returns:
        Summary dictionary of the deletion operation.
    """
    from fairwddi.models import StagedImport, StagedResourceNode, URNAlias

    staged_import = StagedImport.objects.filter(id=import_id).first()
    if not staged_import:
        raise ValueError(f"StagedImport #{import_id} does not exist.")

    nodes = StagedResourceNode.objects.filter(staged_import=staged_import)
    total_nodes = nodes.count()
    raw_urns = list(nodes.values_list("raw_urn", flat=True))

    # Downstream Dependency Checks
    normalized_nodes = nodes.filter(status="normalized").count()
    nodes_with_canonical = (
        nodes.exclude(canonical_urn__isnull=True).exclude(canonical_urn="").count()
    )
    active_normalized_count = max(normalized_nodes, nodes_with_canonical)

    alias_count = URNAlias.objects.filter(alias_urn__in=raw_urns).count() if raw_urns else 0

    if (active_normalized_count > 0 or alias_count > 0) and not force:
        raise ProtectedImportError(
            f"Cannot delete StagedImport #{import_id}: {active_normalized_count} resource(s) are "
            f"already normalized and {alias_count} active URN alias(es) exist downstream. "
            "Use force=True / --force to delete anyway.",
            import_id=import_id,
            normalized_count=active_normalized_count,
            alias_count=alias_count,
        )

    # Optional Log file deletion
    log_deleted = False
    log_file_str = staged_import.import_options.get("log_file")
    if delete_log_file and log_file_str:
        log_path = Path(log_file_str)
        if log_path.exists():
            log_path.unlink()
            log_deleted = True

    # Perform Deletion
    file_name = staged_import.file_name
    nodes.delete()
    staged_import.delete()

    return {
        "staged_import_id": import_id,
        "file_name": file_name,
        "deleted_nodes_count": total_nodes,
        "was_forced": force,
        "log_file_deleted": log_deleted,
    }
