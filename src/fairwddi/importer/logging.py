"""Per-session structured file logging for metadata import jobs.

Writes comprehensive audit trails to logs/imports/import_<id>.log.
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any

from fairwddi.importer.detector import MetadataFormatInfo
from fairwddi.importer.profiles import ImportProfile


class ImportSessionLogger:
    """Dedicated structured file logger for an individual import session."""

    def __init__(
        self,
        import_id: int | str,
        log_dir: str | Path | None = None,
        dry_run: bool = False,
    ) -> None:
        self.import_id = import_id
        self.dry_run = dry_run

        resolved_log_dir = Path(log_dir) if log_dir else Path.cwd() / "logs" / "imports"
        resolved_log_dir.mkdir(parents=True, exist_ok=True)

        prefix = "import_dryrun" if dry_run else "import"
        timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d_%H%M%S")
        self.log_file = resolved_log_dir / f"{prefix}_{import_id}_{timestamp}.log"
        self._file = open(self.log_file, "w", encoding="utf-8")

    @property
    def path(self) -> Path:
        """Return the absolute or relative Path to the session log file."""
        return self.log_file

    def _write_line(self, line: str) -> None:
        ts = datetime.datetime.now(datetime.UTC).isoformat()
        self._file.write(f"[{ts}] {line}\n")
        self._file.flush()

    def log_header(
        self,
        file_path: Path,
        format_info: MetadataFormatInfo,
        profile: ImportProfile,
        file_sha256: str,
        import_task_id: str | None = None,
    ) -> None:
        """Write session initialization metadata header."""
        self._write_line("=" * 80)
        mode = "DRY RUN (NO DB WRITES)" if self.dry_run else "LIVE STAGING"
        self._write_line(f"FAIRwDDI METADATA IMPORT SESSION — #{self.import_id} [{mode}]")
        self._write_line("=" * 80)
        self._write_line(f"Source File: {file_path.resolve()}")
        self._write_line(f"File Size: {file_path.stat().st_size:,} bytes")
        self._write_line(f"File SHA-256: {file_sha256}")
        self._write_line(
            f"Detected Format: {format_info.specification} {format_info.version} "
            f"({format_info.serialization}) [Flavor: {format_info.flavor or 'Generic'}]"
        )
        self._write_line(f"Canonical Slug: {format_info.canonical_slug}")
        self._write_line(f"Active Profile: {profile.name} — {profile.description}")
        self._write_line(f"Include Types: {profile.include_types or 'ALL'}")
        self._write_line(f"Exclude Types: {profile.exclude_types or 'NONE'}")
        self._write_line(f"Include Referenced Resources: {profile.include_referenced_resources}")
        self._write_line(
            f"Strategies: file={profile.strategies.on_duplicate_file}, "
            f"existing={profile.strategies.on_existing_resource}, "
            f"drift={profile.strategies.on_content_drift}"
        )
        if import_task_id:
            self._write_line(f"Task ID: {import_task_id}")
        self._write_line("-" * 80)
        self._write_line("STREAMING & EXTRACTION LOG:")

    def log_info(self, message: str) -> None:
        """Write an informational event."""
        self._write_line(f"INFO: {message}")

    def log_warning(self, message: str) -> None:
        """Write a warning event."""
        self._write_line(f"WARNING: {message}")

    def log_duplicate_skip(self, raw_urn: str, resource_type: str) -> None:
        """Log a duplicate resource skip."""
        self._write_line(
            f"DUPLICATE_SKIP: [{resource_type}] {raw_urn} (identical content already staged)"
        )

    def log_drift_quarantine(
        self,
        raw_urn: str,
        resource_type: str,
        conflict_reason: str,
        existing_hash: str | None = None,
        incoming_hash: str | None = None,
    ) -> None:
        """Log a content drift quarantine event."""
        self._write_line(
            f"DRIFT_QUARANTINE: [{resource_type}] {raw_urn} -> "
            f"Conflict: {conflict_reason} (old_hash={existing_hash}, new_hash={incoming_hash})"
        )

    def log_batch_commit(self, batch_index: int, batch_count: int, cumulative: int) -> None:
        """Log a bulk database batch insertion."""
        self._write_line(
            f"BATCH_COMMIT: Batch #{batch_index} ({batch_count:,} nodes, "
            f"cumulative: {cumulative:,})"
        )

    def log_summary(self, summary: dict[str, Any]) -> None:
        """Write final execution summary."""
        self._write_line("-" * 80)
        self._write_line("EXECUTION SUMMARY:")
        self._write_line(f"Total Resources Staged: {summary.get('total_staged', 0):,}")
        self._write_line(f"Skipped Duplicates: {summary.get('skipped_duplicates', 0):,}")
        self._write_line(f"Quarantined Drift Items: {summary.get('quarantined_count', 0):,}")
        self._write_line(f"Elapsed Time: {summary.get('elapsed_seconds', 0):.2f}s")
        self._write_line(f"Throughput: {summary.get('throughput_per_sec', 0):.1f} resources/sec")
        self._write_line("Breakdown by Resource Type:")
        for r_type, count in summary.get("counts_by_type", {}).items():
            self._write_line(f"  • {r_type}: {count:,}")
        self._write_line("=" * 80)
        self._write_line("IMPORT SESSION FINISHED SUCCESSFULLY")

    def close(self) -> None:
        """Close the file handle safely."""
        if not self._file.closed:
            self._file.close()

    def __enter__(self) -> ImportSessionLogger:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
