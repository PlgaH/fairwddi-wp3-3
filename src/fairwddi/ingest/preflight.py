"""Stage 1 (Preflight): Readiness inspection, profile QA, URN audit, and DDI-C to DDI-L upgrade."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Literal

from fairwddi.ingest.detector import compute_file_sha256, detect_metadata_format
from fairwddi.ingest.plan import IngestPlan, PlanActionItem, PlanIssue, ReviewGate
from fairwddi.ingest.profiles import ImportProfile, load_profile
from fairwddi.ingest.streaming import stream_resources


def _check_existing_batch(file_sha256: str) -> int | None:
    """Check if a file with this SHA-256 has already been ingested."""
    try:
        from fairwddi.models import IngestBatch

        batch = (
            IngestBatch.objects.filter(file_sha256=file_sha256)
            .exclude(status__in=["failed", "undone"])
            .order_by("-id")
            .first()
        )
        if batch:
            return batch.id
    except Exception:
        pass
    return None


def _resolve_external_urns_in_db(external_urns: set[str]) -> tuple[set[str], set[str]]:
    """Return (resolved_in_db, unresolved) for a set of external URNs."""
    if not external_urns:
        return set(), set()
    try:
        from fairwddi.models import URNAlias, UrnRegistry

        in_registry = set(
            UrnRegistry.objects.filter(urn__in=external_urns).values_list("urn", flat=True)
        )
        in_aliases = set(
            URNAlias.objects.filter(alias_urn__in=external_urns).values_list("alias_urn", flat=True)
        )
        resolved = in_registry | in_aliases
        return resolved, external_urns - resolved
    except Exception:
        return set(), set(external_urns)


def run_preflight_check(
    file_path: str | Path,
    profile: str | Path | ImportProfile = "request",
    output_dir: str | Path | None = None,
    auto_approve: bool = False,
) -> IngestPlan:
    """Run Stage 1 preflight readiness checks on an incoming DDI-C or DDI-L file.

    Performs:
    1. Format & version detection + SHA-256 duplicate batch check.
    2. Specification & ReQuest profile QA (using dartfx-ddi profilers).
    3. URN readiness audit (explicit vs. synthesized vs. anonymous).
    4. Internal & external reference resolution audit against UrnRegistry.
    """
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    resolved_profile = profile if isinstance(profile, ImportProfile) else load_profile(profile)
    fmt = detect_metadata_format(path)
    file_sha256 = compute_file_sha256(path)
    existing_batch_id = _check_existing_batch(file_sha256)

    job_id = f"preflight-{path.stem}-{uuid.uuid4().hex[:8]}"
    issues: list[PlanIssue] = []
    actions: list[PlanActionItem] = []
    summary: dict[str, Any] = {
        "specification": fmt.specification,
        "version": fmt.version,
        "serialization": fmt.serialization,
        "flavor": fmt.flavor or "Generic",
        "canonical_slug": fmt.canonical_slug,
        "existing_batch_id": existing_batch_id,
    }

    if existing_batch_id is not None:
        issues.append(
            PlanIssue(
                severity="warning",
                code="PRE-DUP-001",
                message=(
                    f"File with identical SHA-256 was already ingested in "
                    f"IngestBatch #{existing_batch_id}."
                ),
                requires_review=True,
            )
        )

    if fmt.specification == "Unknown":
        issues.append(
            PlanIssue(
                severity="error",
                code="PRE-FMT-001",
                message=f"Unrecognized metadata format for file '{path.name}'.",
                requires_review=True,
            )
        )

    # Branch 1: DDI-Codebook (classic or multilingual)
    if fmt.specification == "DDI-C":
        try:
            from dartfx.ddi import ddicodebook as codebook
            from dartfx.ddi.ddicodebook.profiler import analyze_ddic_profile

            cb = codebook.loadxml(str(path))
            ddic_prof = analyze_ddic_profile(path)
            langs = list(ddic_prof.summary.languages.keys())
            is_multilingual = len(langs) > 1
            var_count = len(cb.search_variables())
            file_count = len(cb.fileDscr or [])

            summary.update(
                {
                    "is_multilingual": is_multilingual,
                    "languages": langs or [cb.xml_lang or "en"],
                    "variable_count": var_count,
                    "datafile_count": file_count,
                    "total_elements": ddic_prof.summary.total_elements,
                    "requires_ddic_upgrade": True,
                }
            )

            if var_count == 0:
                issues.append(
                    PlanIssue(
                        severity="warning",
                        code="PRE-DDIC-001",
                        message="DDI-Codebook contains 0 variables (<var>).",
                        requires_review=True,
                    )
                )

            target_ddil = path.with_suffix(".ddi40.json").name
            actions.append(
                PlanActionItem(
                    id="act-upgrade-001",
                    stage="preflight",
                    action="upgrade",
                    resource_type="CodeBook",
                    source_urn=path.name,
                    target_urn=target_ddil,
                    confidence=1.0,
                    requires_review=False,
                    details={
                        "is_multilingual": is_multilingual,
                        "languages": langs,
                        "variable_count": var_count,
                    },
                    notes="Upgrade DDI-Codebook to DDI-Lifecycle 4.0 prior to staging.",
                )
            )
        except Exception as exc:
            issues.append(
                PlanIssue(
                    severity="error",
                    code="PRE-DDIC-ERR",
                    message=f"Failed to parse or profile DDI-Codebook XML: {exc}",
                    requires_review=True,
                )
            )

    # Branch 2: DDI-Lifecycle (3.x XML or 4.0 JSON/JSONL/XML)
    elif fmt.specification == "DDI-L":
        if fmt.serialization == "xml":
            try:
                from dartfx.ddi.ddilifecycle.utils import analyze_ddil_profile

                ddil_prof = analyze_ddil_profile(path)
                summary.update(
                    {
                        "quality_score": ddil_prof.summary.quality_score,
                        "quality_grade": ddil_prof.summary.quality_grade,
                        "urn_coverage_rate": ddil_prof.summary.urn_coverage_rate,
                        "resolution_rate": ddil_prof.summary.resolution_rate,
                        "languages": list(ddil_prof.summary.languages.keys()),
                        "is_multilingual": ddil_prof.summary.unique_languages > 1,
                    }
                )
                for qf in ddil_prof.summary.qa_findings:
                    sev: Literal["error", "warning", "info"] = (
                        "error"
                        if qf.severity == "error"
                        else ("warning" if qf.severity == "warning" else "info")
                    )
                    issues.append(
                        PlanIssue(
                            severity=sev,
                            code=qf.code,
                            resource_type=qf.class_name,
                            message=qf.message,
                            requires_review=(sev == "error"),
                            samples=qf.samples,
                        )
                    )
            except Exception as exc:
                issues.append(
                    PlanIssue(
                        severity="warning",
                        code="PRE-DDIL-PROF",
                        message=f"Could not run full XML profile analysis: {exc}",
                    )
                )

        # Stream resources to check profile filtering, URN quality, and external links
        all_nodes = list(stream_resources(path, resolved_profile, fmt))
        defined_urns = {n.raw_urn for n in all_nodes}
        all_referenced_urns: set[str] = set()
        anonymous_urns: list[str] = []
        included_counts: dict[str, int] = {}
        excluded_counts: dict[str, int] = {}

        for n in all_nodes:
            all_referenced_urns.update(n.referenced_urns)
            if ":anonymous:" in n.raw_urn or ":unknown.agency:" in n.raw_urn:
                anonymous_urns.append(n.raw_urn)

        for n in all_nodes:
            is_ref = n.raw_urn in all_referenced_urns
            if resolved_profile.should_include(n.resource_type, is_referenced=is_ref):
                included_counts[n.resource_type] = included_counts.get(n.resource_type, 0) + 1
            else:
                excluded_counts[n.resource_type] = excluded_counts.get(n.resource_type, 0) + 1

        external_urns = {
            u for u in all_referenced_urns if u not in defined_urns and u.startswith("urn:ddi:")
        }
        resolved_ext, unresolved_ext = _resolve_external_urns_in_db(external_urns)

        summary.update(
            {
                "total_streamed_resources": len(all_nodes),
                "total_included_resources": sum(included_counts.values()),
                "total_excluded_resources": sum(excluded_counts.values()),
                "included_by_type": included_counts,
                "excluded_by_type": excluded_counts,
                "anonymous_or_partial_urn_count": len(anonymous_urns),
                "external_reference_count": len(external_urns),
                "external_resolved_in_db_count": len(resolved_ext),
                "external_unresolved_count": len(unresolved_ext),
            }
        )

        if anonymous_urns:
            issues.append(
                PlanIssue(
                    severity="warning",
                    code="PRE-URN-002",
                    message=(
                        f"{len(anonymous_urns)} resource(s) have synthesized/anonymous URNs "
                        f"due to missing agency or ID."
                    ),
                    requires_review=True,
                    samples=anonymous_urns[:5],
                )
            )

        if unresolved_ext:
            issues.append(
                PlanIssue(
                    severity="warning",
                    code="PRE-REF-002",
                    message=(
                        f"{len(unresolved_ext)} external reference(s) are not present in "
                        f"this file or in UrnRegistry."
                    ),
                    requires_review=False,
                    samples=sorted(unresolved_ext)[:5],
                )
            )

    plan = IngestPlan(
        stage="preflight",
        job_id=job_id,
        source_file=path.name,
        source_path=str(path),
        file_sha256=file_sha256,
        source_format=fmt.canonical_slug,
        batch_id=existing_batch_id,
        profile=resolved_profile.name,
        summary=summary,
        issues=issues,
        actions=actions,
        review_gate=ReviewGate(approved=auto_approve),
    )
    if plan.is_ready_to_execute(auto_approve=auto_approve):
        plan.review_gate.approved = True

    if output_dir is not None:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        plan.to_yaml(out_dir / f"{path.stem}.preflight.plan.yaml")
        plan.to_markdown(out_dir / f"{path.stem}.preflight.report.md")

    return plan


def upgrade_ddic_to_ddil(
    file_path: str | Path,
    output_path: str | Path | None = None,
    output_format: Literal["ddi4-json", "ddi4-jsonl", "ddi4-xml", "ddi33-xml"] = "ddi4-json",
    agency: str | None = None,
    version: str | None = None,
    identifier: str | None = None,
    id_strategy: str = "hierarchical",
    harmonize_codes: bool = True,
    report_path: str | Path | None = None,
) -> dict[str, Any]:
    """Explicitly upgrade a DDI-Codebook (classic or multilingual) file to DDI-Lifecycle on disk.

    Uses dartfx-ddi CodebookToLifecycleConverter with automatic code list deduplication
    and deterministic URN generation.
    """
    from dartfx.ddi import ddicodebook as codebook
    from dartfx.ddi.ddicodebook import utils as cb_utils

    src_path = Path(file_path).resolve()
    if not src_path.exists():
        raise FileNotFoundError(f"DDI-Codebook file not found: {src_path}")

    ext_map = {
        "ddi4-json": ".ddi40.json",
        "ddi4-jsonl": ".ddi40.jsonl",
        "ddi4-xml": ".ddi40.xml",
        "ddi33-xml": ".ddi33.xml",
    }
    if output_format not in ext_map:
        raise ValueError(
            f"Unsupported output_format '{output_format}'. Expected one of {list(ext_map)}."
        )

    target_path = (
        Path(output_path).resolve()
        if output_path is not None
        else src_path.with_suffix(ext_map[output_format])
    )
    target_path.parent.mkdir(parents=True, exist_ok=True)

    cb = codebook.loadxml(str(src_path))
    converter = cb_utils.codebook_to_lifecycle(
        cb,
        agency=agency,
        version=version,
        identifier=identifier,
        id_strategy=id_strategy,
        harmonize_codes=harmonize_codes,
    )

    if output_format == "ddi4-json":
        content = converter.to_ddi4_json(indent=2)
    elif output_format == "ddi4-jsonl":
        content = converter.to_ddi4_jsonl()
    elif output_format == "ddi4-xml":
        content = converter.to_ddi4_xml()
    else:
        content = converter.to_ddi33_xml(pretty=True)

    target_path.write_text(content, encoding="utf-8")
    summary = converter.get_summary()

    # Build upgrade report
    rep_file = (
        Path(report_path).resolve()
        if report_path is not None
        else target_path.with_suffix(".upgrade.report.md")
    )
    report_lines = [
        f"# DDI-Codebook to DDI-Lifecycle Upgrade Report — `{src_path.name}`",
        "",
        f"- **Source DDI-C File:** `{src_path}`",
        f"- **Output DDI-L File:** `{target_path}`",
        f"- **Target Format:** `{output_format}`",
        f"- **ID Strategy:** `{id_strategy}`",
        f"- **CodeList Harmonization:** `{harmonize_codes}`",
        f"- **Resolved Agency:** `{summary['agency']}`",
        f"- **Version:** `{summary['version']}`",
        f"- **Study ID:** `{summary['codebook_id']}`",
        f"- **Study Title:** {summary['title']}",
        "",
        "## Converted Resource Counts",
        "",
        "| Resource Type | Count |",
        "| :--- | ---: |",
        f"| `Variable` | {summary['variable_count']:,} |",
        f"| `CodeList` | {summary['codelist_count']:,} |",
        f"| `Category` | {summary['category_count']:,} |",
        f"| `QuestionItem` | {summary['question_count']:,} |",
        f"| `VariableGroup` | {summary['variable_group_count']:,} |",
        f"| `PhysicalInstance` | {summary['physical_instance_count']:,} |",
        "",
    ]
    if converter.document.diagnostics:
        report_lines.extend(
            [
                "## Conversion Diagnostics",
                "",
                "| Level | Code | Message |",
                "| :--- | :--- | :--- |",
            ]
        )
        for diag in converter.document.diagnostics:
            lvl = diag.get("level", "info")
            cd = diag.get("code", "-")
            msg = diag.get("message", "")
            report_lines.append(f"| `{lvl}` | `{cd}` | {msg} |")
        report_lines.append("")

    rep_file.write_text("\n".join(report_lines), encoding="utf-8")

    return {
        "source_file": str(src_path),
        "output_file": str(target_path),
        "report_file": str(rep_file),
        "output_format": output_format,
        "id_strategy": id_strategy,
        "harmonize_codes": harmonize_codes,
        **summary,
    }
