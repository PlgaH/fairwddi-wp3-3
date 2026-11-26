"""Review-gated Plan and Report models for the FAIRwDDI deterministic import pipeline.

Every import stage (``preflight`` and ``import``) emits a deterministic YAML plan
and a human-readable Markdown report governed by a :class:`ReviewGate`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field


class ReviewGate(BaseModel):
    """Approval gate governing whether a plan with pending review items may execute."""

    approved: bool = Field(
        default=False,
        description="Set to true after human review to authorize execution of pending items.",
    )
    reviewer: str | None = Field(
        default=None,
        description="Name or identifier of the reviewer who approved the plan.",
    )
    reviewed_at: str | None = Field(
        default=None,
        description="ISO-8601 timestamp when the plan was reviewed.",
    )
    comments: str = Field(
        default="",
        description="Optional reviewer notes or rationale.",
    )


class PlanIssue(BaseModel):
    """Diagnostic or QA finding recorded during preflight or import."""

    severity: Literal["error", "warning", "info"] = "warning"
    code: str
    message: str
    resource_type: str | None = None
    resource_urn: str | None = None
    requires_review: bool = False
    samples: list[str] = Field(default_factory=list)


class ImportActionItem(BaseModel):
    """Planned or executed deterministic import operation on a metadata resource."""

    id: str
    stage: Literal["preflight", "import"] = "import"
    action: Literal[
        "create",
        "reuse",
        "quarantine",
        "upgrade",
        "skip",
    ]
    resource_type: str
    source_urn: str
    target_urn: str | None = None
    confidence: float = 1.0
    requires_review: bool = False
    approved: bool = True
    details: dict[str, Any] = Field(default_factory=dict)
    notes: str = ""


# Intra-package compatibility name for PlanActionItem references in preflight/loader
PlanActionItem = ImportActionItem


class ImportPlan(BaseModel):
    """Serializable, review-gated execution plan and report for metadata import stages."""

    plan_version: str = "2.0"
    stage: Literal["preflight", "import"] = "import"
    job_id: str
    created_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
    )
    source_file: str | None = None
    source_path: str | None = None
    file_sha256: str | None = None
    source_format: str | None = None
    batch_id: int | None = None
    profile: str = "request"
    summary: dict[str, Any] = Field(default_factory=dict)
    review_gate: ReviewGate = Field(default_factory=ReviewGate)
    issues: list[PlanIssue] = Field(default_factory=list)
    actions: list[ImportActionItem] = Field(default_factory=list)

    @property
    def error_count(self) -> int:
        """Count of error-severity issues."""
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        """Count of warning-severity issues."""
        return sum(1 for i in self.issues if i.severity == "warning")

    @property
    def pending_review_count(self) -> int:
        """Count of issues or actions flagged as requiring human review."""
        issue_reviews = sum(1 for i in self.issues if i.requires_review)
        action_reviews = sum(1 for a in self.actions if a.requires_review)
        return issue_reviews + action_reviews

    def is_ready_to_execute(self, auto_approve: bool = False) -> bool:
        """Check whether this plan is clear to execute."""
        if auto_approve or self.review_gate.approved:
            return True
        if self.error_count > 0 or self.pending_review_count > 0:
            return False
        return True

    def to_dict(self) -> dict[str, Any]:
        """Convert plan to a plain dictionary suitable for YAML/JSON serialization."""
        data = self.model_dump(mode="json")
        data["summary"] = {
            **self.summary,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "pending_review_count": self.pending_review_count,
            "total_actions": len(self.actions),
        }
        return data

    def to_yaml(self, path: Path | str | None = None) -> str:
        """Serialize the plan to YAML and optionally write to disk."""
        content = yaml.safe_dump(
            self.to_dict(),
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        )
        if path is not None:
            out_path = Path(path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(content, encoding="utf-8")
        return content

    def to_json(self, path: Path | str | None = None, indent: int = 2) -> str:
        """Serialize the plan to JSON and optionally write to disk."""
        import json

        content = json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
        if path is not None:
            out_path = Path(path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(content, encoding="utf-8")
        return content

    @classmethod
    def from_yaml(cls, path_or_str: Path | str) -> ImportPlan:
        """Load an ImportPlan from a YAML file path or YAML string."""
        if isinstance(path_or_str, Path) or (
            isinstance(path_or_str, str) and "\n" not in path_or_str and Path(path_or_str).exists()
        ):
            raw_text = Path(path_or_str).read_text(encoding="utf-8")
        else:
            raw_text = str(path_or_str)
        data = yaml.safe_load(raw_text) or {}
        return cls.model_validate(data)

    def to_markdown(
        self,
        path: Path | str | None = None,
        max_actions_per_type: int = 15,
    ) -> str:
        """Render a human-readable Markdown report for this plan."""
        gate_status = (
            "APPROVED"
            if self.review_gate.approved
            else ("READY (No Review Needed)" if self.is_ready_to_execute() else "PENDING REVIEW")
        )
        lines: list[str] = [
            f"# FAIRwDDI `{self.stage.upper()}` Report — `{self.job_id}`",
            "",
            "## Overview",
            "",
            f"- **Stage:** `{self.stage}`",
            f"- **Job ID:** `{self.job_id}`",
            f"- **Created At:** `{self.created_at}`",
            f"- **Review Gate Status:** **{gate_status}**",
            f"- **Errors:** `{self.error_count}` | **Warnings:** `{self.warning_count}` | "
            f"**Pending Review Items:** `{self.pending_review_count}`",
        ]
        if self.source_file:
            lines.append(f"- **Source File:** `{self.source_file}`")
        if self.source_format:
            lines.append(f"- **Detected Format:** `{self.source_format}`")
        if self.file_sha256:
            lines.append(f"- **File SHA-256:** `{self.file_sha256}`")
        if self.batch_id is not None:
            lines.append(f"- **Import Batch ID:** `#{self.batch_id}`")

        if self.summary:
            lines.extend(["", "## Summary Metrics", "", "| Metric | Value |", "| :--- | :--- |"])
            for k, v in self.summary.items():
                lines.append(f"| `{k}` | `{v}` |")

        if self.actions:
            action_order = ["create", "reuse", "quarantine", "upgrade", "skip"]
            present_actions = [
                a for a in action_order if any(act.action == a for act in self.actions)
            ]
            crosstab: dict[str, dict[str, int]] = {}
            col_totals: dict[str, int] = {a: 0 for a in present_actions}
            for act in self.actions:
                row = crosstab.setdefault(act.resource_type, {a: 0 for a in present_actions})
                row[act.action] = row.get(act.action, 0) + 1
                col_totals[act.action] = col_totals.get(act.action, 0) + 1

            header_cols = ["Resource Type", *present_actions, "Total"]
            align_cols = [":---", *["---:" for _ in present_actions], "---:"]
            lines.extend(
                [
                    "",
                    "### Actions by Resource Type",
                    "",
                    "| " + " | ".join(header_cols) + " |",
                    "| " + " | ".join(align_cols) + " |",
                ]
            )
            for r_type, counts in crosstab.items():
                row_total = sum(counts.values())
                vals = [f"`{r_type}`", *[f"{counts.get(a, 0):,}" for a in present_actions]]
                vals.append(f"**{row_total:,}**")
                lines.append("| " + " | ".join(vals) + " |")
            total_vals = [
                "**Total**",
                *[f"**{col_totals.get(a, 0):,}**" for a in present_actions],
                f"**{len(self.actions):,}**",
            ]
            lines.append("| " + " | ".join(total_vals) + " |")

        planned_codes = int((self.summary or {}).get("planned_codes") or 0)
        planned_freqs = int((self.summary or {}).get("planned_frequency_rows") or 0)
        planned_stats = int((self.summary or {}).get("planned_summary_stat_variables") or 0)
        if planned_codes or planned_freqs or planned_stats:
            create_actions_cnt = sum(1 for a in self.actions if a.action == "create")
            lines.extend(
                [
                    "",
                    "### Nested & Observation Rows (Expected)",
                    "",
                    "| Category | Count | Notes |",
                    "| :--- | ---: | :--- |",
                    (
                        f"| `Code` (nested in `CodeList`) | {planned_codes:,} | "
                        "Created under parent `CodeList` URNs |"
                    ),
                    (
                        f"| `DatafileVariableFrequency` | {planned_freqs:,} | "
                        "Category frequency observations |"
                    ),
                    (
                        f"| `DatafileVariable` (summary stats) | {planned_stats:,} | "
                        "Variables carrying summary statistics |"
                    ),
                    (
                        f"| **Expected Total Created URNs** | "
                        f"**{create_actions_cnt + planned_codes:,}** | "
                        f"Top-level `create` actions ({create_actions_cnt:,}) + "
                        f"nested `Code`s ({planned_codes:,}) |"
                    ),
                ]
            )

        if self.issues:
            lines.extend(
                [
                    "",
                    "## Findings & Diagnostics",
                    "",
                    "| Severity | Code | Type | URN / Context | Message |",
                    "| :--- | :--- | :--- | :--- | :--- |",
                ]
            )
            for issue in self.issues:
                r_type = f"`{issue.resource_type}`" if issue.resource_type else "-"
                r_urn = f"`{issue.resource_urn}`" if issue.resource_urn else "-"
                lines.append(
                    f"| **{issue.severity.upper()}** | `{issue.code}` | {r_type} | "
                    f"{r_urn} | {issue.message} |"
                )

        reuse_actions = [a for a in self.actions if a.action == "reuse"]
        if reuse_actions:
            lines.extend(
                [
                    "",
                    "## Same-URN Reuse Candidates (Review Flagged)",
                    "",
                    "> [!WARNING]",
                    (
                        f"> **{len(reuse_actions):,} incoming entity/entities** carry URNs that "
                        "already exist in `UrnRegistry` with matching content hashes. Review and "
                        "confirm cross-file URN reuse before executing."
                    ),
                    "",
                    "| Resource Type | URN | Details |",
                    "| :--- | :--- | :--- |",
                ]
            )
            for act in reuse_actions[:50]:
                lines.append(f"| `{act.resource_type}` | `{act.source_urn}` | {act.notes} |")

        quarantine_actions = [a for a in self.actions if a.action == "quarantine"]
        if quarantine_actions:
            lines.extend(
                [
                    "",
                    "## Quarantined Items (Content Drift Detected)",
                    "",
                    "> [!WARNING]",
                    (
                        f"> **{len(quarantine_actions):,} entities** carry URNs that already "
                        "exist in the database with conflicting content hashes. These items "
                        "will be held in `MetadataQuarantine` pending review."
                    ),
                    "",
                    "| Resource Type | URN | Conflict Details |",
                    "| :--- | :--- | :--- |",
                ]
            )
            for act in quarantine_actions:
                lines.append(f"| `{act.resource_type}` | `{act.source_urn}` | {act.notes} |")

        if self.actions:
            actions_by_type: dict[str, list[ImportActionItem]] = {}
            for act in self.actions:
                actions_by_type.setdefault(act.resource_type, []).append(act)

            lines.extend(
                [
                    "",
                    f"## Planned Actions ({len(self.actions):,} total across "
                    f"{len(actions_by_type)} resource type(s))",
                    "",
                    "| ID | Action | Resource Type | URN |",
                    "| :--- | :--- | :--- | :--- |",
                ]
            )
            for r_type, group in actions_by_type.items():
                for act in group[:max_actions_per_type]:
                    urn_col = (
                        f"`{act.source_urn}` → `{act.target_urn}`"
                        if act.target_urn and act.target_urn != act.source_urn
                        else f"`{act.source_urn}`"
                    )
                    lines.append(
                        f"| `{act.id}` | `{act.action}` | `{act.resource_type}` | {urn_col} |"
                    )
                remaining = len(group) - max_actions_per_type
                if remaining > 0:
                    lines.append(
                        f"| `...` | `...` | `{r_type}` | "
                        f"*... and {remaining:,} additional `{r_type}` item(s)* |"
                    )

        lines.append("")
        content = "\n".join(lines)
        if path is not None:
            out_path = Path(path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(content, encoding="utf-8")
        return content
