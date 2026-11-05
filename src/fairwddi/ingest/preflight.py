"""Stage 1 (Preflight): Readiness inspection, profile QA, URN audit, and DDI-C to DDI-L upgrade."""

from __future__ import annotations

import os
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


def _resolve_ddic_profile(profile_arg: str | Path | ImportProfile | None) -> Path | str:
    """Resolve the validation profile to use for DDI-Codebook profiling."""
    name = (
        profile_arg.name
        if isinstance(profile_arg, ImportProfile)
        else (str(profile_arg) if profile_arg else "request")
    )

    # 1. Direct path check
    direct_path = Path(name)
    if direct_path.is_file():
        return direct_path

    # 2. Check candidate directories for custom DDI-C profile files
    candidate_dirs = [
        Path.cwd() / "profiles",
        Path(__file__).parent.parent.parent.parent / "profiles",
        Path.cwd(),
    ]
    suffixes = [".ddic.yaml", ".ddic.yml", ".yaml", ".yml"]
    for c_dir in candidate_dirs:
        for sfx in suffixes:
            cand = c_dir / f"{name}{sfx}"
            if cand.is_file():
                return cand
        if name.endswith(".ddic"):
            base = name[:-5]
            for sfx in suffixes:
                cand = c_dir / f"{base}{sfx}"
                if cand.is_file():
                    return cand

    # 3. Built-in DDI-C profiles in dartfx-ddi
    if name.lower() in ("recommended", "cdif", "schema"):
        return name.lower()

    return "recommended"


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
            ddic_profile_ref = _resolve_ddic_profile(profile)
            ddic_prof = analyze_ddic_profile(path, profile=ddic_profile_ref)
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

            if hasattr(ddic_prof, "quality") and ddic_prof.quality:
                summary.update(
                    {
                        "quality_score": ddic_prof.quality.overall_score,
                        "quality_grade": ddic_prof.quality.grade,
                        "profile_id": ddic_prof.quality.profile_id,
                        "profile_name": ddic_prof.quality.profile_name,
                    }
                )
                for qf in ddic_prof.quality.findings:
                    sev_str = (
                        qf.severity.value if hasattr(qf.severity, "value") else str(qf.severity)
                    )
                    sev_norm: Literal["error", "warning", "info"] = (
                        "error"
                        if sev_str == "error"
                        else ("warning" if sev_str == "warning" else "info")
                    )
                    issues.append(
                        PlanIssue(
                            severity=sev_norm,
                            code=qf.rule_id,
                            message=qf.message,
                            requires_review=(sev_norm == "error"),
                        )
                    )
            elif var_count == 0:
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
    harmonize_questions: bool = True,
    report_path: str | Path | None = None,
) -> dict[str, Any]:
    """Explicitly upgrade a DDI-Codebook (classic or multilingual) file to DDI-Lifecycle on disk.

    Uses dartfx-ddi CodebookToLifecycleConverter with automatic code list and question
    deduplication and deterministic URN generation.
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
    target_agency = agency or os.getenv("DDI_AGENCY", "fr.cdsp")
    converter = cb_utils.codebook_to_lifecycle(
        cb,
        agency=target_agency,
        version=version,
        identifier=identifier,
        id_strategy=id_strategy,
        harmonize_codes=harmonize_codes,
        harmonize_questions=harmonize_questions,
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

    # Dedicated secondary file for empirical frequencies & summary statistics
    stats_file: Path | None = None
    has_stats = summary.get("variable_statistics_count", 0) > 0
    if output_format in ("ddi4-json", "ddi4-jsonl") and has_stats:
        stats_name = target_path.name.replace(".ddi40.jsonl", ".stats.ddi40.json").replace(
            ".ddi40.json", ".stats.ddi40.json"
        )
        stats_file = target_path.with_name(stats_name)
        if stats_file == target_path:
            stats_file = target_path.with_suffix(".stats.ddi40.json")
        stats_content = converter.to_ddi4_stats_json(indent=2)
        stats_file.write_text(stats_content, encoding="utf-8")

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
    ]
    if stats_file:
        report_lines.append(f"- **Statistics DDI-L File:** `{stats_file}`")

    raw_cl = summary.get("raw_codelist_count", summary["codelist_count"])
    cl_rem = summary.get("codelist_duplicates_removed", 0)
    cl_pct = summary.get("codelist_reduction_pct", 0.0)

    raw_cat = summary.get("raw_category_count", summary["category_count"])
    cat_rem = summary.get("category_duplicates_removed", 0)
    cat_pct = summary.get("category_reduction_pct", 0.0)

    raw_q = summary.get("raw_question_count", summary["question_count"])
    q_rem = summary.get("question_duplicates_removed", 0)
    q_pct = summary.get("question_reduction_pct", 0.0)

    v_cnt = summary["variable_count"]
    q_cnt = summary["question_count"]
    vg_cnt = summary["variable_group_count"]
    pi_cnt = summary["physical_instance_count"]

    report_lines.extend(
        [
            f"- **Target Format:** `{output_format}`",
            f"- **ID Strategy:** `{id_strategy}`",
            f"- **CodeList Harmonization:** `{harmonize_codes}`",
            f"- **Question Harmonization:** `{harmonize_questions}`",
            f"- **Resolved Agency:** `{summary['agency']}`",
            f"- **Version:** `{summary['version']}`",
            f"- **Study ID:** `{summary['codebook_id']}`",
            f"- **Study Title:** {summary['title']}",
            "",
            "## Converted Resource Counts & Deduplication",
            "",
            "| Resource Type | Raw Count | Deduplicated Count | Duplicates Removed | Reduction |",
            "| :--- | ---: | ---: | ---: | ---: |",
            f"| `CodeList` | {raw_cl:,} | {summary['codelist_count']:,} | "
            f"{cl_rem:,} | {cl_pct:.1f}% |",
            f"| `Category` | {raw_cat:,} | {summary['category_count']:,} | "
            f"{cat_rem:,} | {cat_pct:.1f}% |",
            f"| `QuestionItem` | {raw_q:,} | {q_cnt:,} | {q_rem:,} | {q_pct:.1f}% |",
            f"| `Variable` | {v_cnt:,} | {v_cnt:,} | 0 | 0.0% |",
            f"| `VariableGroup` | {vg_cnt:,} | {vg_cnt:,} | 0 | 0.0% |",
            f"| `PhysicalInstance` | {pi_cnt:,} | {pi_cnt:,} | 0 | 0.0% |",
            "",
        ]
    )

    if stats_file:
        vs_cnt = summary.get("variable_statistics_count", 0)
        f_cnt = summary.get("total_frequencies_count", 0)
        s_cnt = summary.get("total_summary_statistics_count", 0)
        arch_note = (
            "> **Architecture Note:** In accordance with standard DDI 4.0 and DDI-Lifecycle "
            "principles, variable definitions, question items, and code lists represent reusable, "
            "survey-agnostic metadata. Empirical observation statistics (frequencies, weighted "
            "counts, and numeric summaries) are dataset-specific and are preserved in a dedicated "
            "secondary DDI 4.0 file (`*.stats.ddi40.json`) containing native `VariableStatistics` "
            "structures linked to parent variable URNs."
        )
        report_lines.extend(
            [
                "## Empirical Observation Statistics",
                "",
                f"- **Dedicated Secondary File:** `{stats_file}`",
                f"- **Variables with Statistics:** {vs_cnt:,}",
                f"- **Total Category Frequencies:** {f_cnt:,}",
                f"- **Total Summary Statistics:** {s_cnt:,}",
                "",
                arch_note,
                "",
            ]
        )
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
        "stats_file": str(stats_file) if stats_file else None,
        "report_file": str(rep_file),
        "output_format": output_format,
        "id_strategy": id_strategy,
        "harmonize_codes": harmonize_codes,
        "harmonize_questions": harmonize_questions,
        **summary,
    }
