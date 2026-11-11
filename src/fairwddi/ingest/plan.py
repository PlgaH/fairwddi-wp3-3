"""Review-gated Plan and Report models for the FAIRwDDI multi-stage ingestion pipeline.

Modeled after the dartfx-ddi i18n MergePlan & ReviewGate pattern, every stage
(preflight, ingest, compare, harmonize) can emit a deterministic YAML plan
and a human-readable Markdown report.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import yaml
from dartfx.ddi.harmonizer import MatchType
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
    """Diagnostic or QA finding recorded during preflight, staging, promotion, or comparison."""

    severity: Literal["error", "warning", "info"] = "warning"
    code: str
    message: str
    resource_type: str | None = None
    resource_urn: str | None = None
    requires_review: bool = False
    samples: list[str] = Field(default_factory=list)


class PlanActionItem(BaseModel):
    """Planned or executed operation on a resource or pair of resources."""

    id: str
    stage: Literal["preflight", "ingest", "compare", "harmonize"]
    action: Literal[
        "create",
        "reuse",
        "alias",
        "quarantine",
        "harmonize",
        "merge_multilingual",
        "link_semantic",
        "elevate",
        "absorb",
        "group",
        "upgrade",
        "skip",
    ]
    resource_type: str
    source_urn: str
    target_urn: str | None = None
    confidence: float = 1.0
    match_type: MatchType | str | None = None
    requires_review: bool = False
    approved: bool = True
    details: dict[str, Any] = Field(default_factory=dict)
    notes: str = ""


class IngestPlan(BaseModel):
    """Serializable, review-gated execution plan and report for any ingestion stage."""

    plan_version: str = "1.0"
    stage: Literal["preflight", "ingest", "compare", "harmonize"]
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
    actions: list[PlanActionItem] = Field(default_factory=list)

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
        """Check if this plan is clear to execute."""
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

    @classmethod
    def from_yaml(cls, path_or_str: Path | str) -> IngestPlan:
        """Load an IngestPlan from a YAML file path or YAML string."""
        if isinstance(path_or_str, Path) or (
            isinstance(path_or_str, str) and "\n" not in path_or_str and Path(path_or_str).exists()
        ):
            raw_text = Path(path_or_str).read_text(encoding="utf-8")
        else:
            raw_text = str(path_or_str)
        data = yaml.safe_load(raw_text) or {}
        return cls.model_validate(data)

    def to_markdown(self, path: Path | str | None = None) -> str:
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
            lines.append(f"- **Ingest Batch ID:** `#{self.batch_id}`")

        if self.summary:
            lines.extend(["", "## Summary Metrics", "", "| Metric | Value |", "| :--- | :--- |"])
            for k, v in self.summary.items():
                lines.append(f"| `{k}` | `{v}` |")

        if self.issues:
            lines.extend(
                [
                    "",
                    "## Findings & Diagnostics",
                    "",
                    "| Severity | Code | Type | URN / Context | Review? | Message |",
                    "| :--- | :--- | :--- | :--- | :---: | :--- |",
                ]
            )
            for issue in self.issues:
                r_type = f"`{issue.resource_type}`" if issue.resource_type else "-"
                r_urn = f"`{issue.resource_urn}`" if issue.resource_urn else "-"
                rev = "Yes" if issue.requires_review else "No"
                lines.append(
                    f"| **{issue.severity.upper()}** | `{issue.code}` | {r_type} | "
                    f"{r_urn} | {rev} | {issue.message} |"
                )

        alias_actions = [a for a in self.actions if a.action == "alias"]
        if alias_actions:
            from collections import Counter

            by_type = Counter(a.resource_type for a in alias_actions)
            summary_parts = [f"**{t}:** {cnt:,}" for t, cnt in by_type.most_common()]
            lines.extend(
                [
                    "",
                    "## Cross-Survey Deduplication (URN Aliases)",
                    "",
                    "> [!TIP]",
                    (
                        f"> **{len(alias_actions):,} incoming entities** match pre-existing "
                        f"canonical resources in PostgreSQL ({', '.join(summary_parts)}). "
                        "Instead of inserting duplicate database records, the engine will "
                        "link these resources to existing canonical URNs via `URNAlias` "
                        "records, ensuring multi-study harmonization and zero database bloat."
                    ),
                    "",
                    "| Type | Source URN (Incoming) | Target Canonical URN | Match Basis |",
                    "| :--- | :--- | :--- | :--- |",
                ]
            )
            # Display up to 20 examples per type so all resource types are clearly visible
            actions_by_type: dict[str, list[PlanActionItem]] = {}
            for act in alias_actions:
                actions_by_type.setdefault(act.resource_type, []).append(act)

            for r_type, act_list in actions_by_type.items():
                for act in act_list[:20]:
                    note = act.notes.replace("will register URNAlias.", "").strip()
                    lines.append(
                        f"| `{act.resource_type}` | `{act.source_urn}` | "
                        f"`{act.target_urn}` | {note} |"
                    )
                if len(act_list) > 20:
                    extra_cnt = len(act_list) - 20
                    lines.append(
                        f"| *...* | *({extra_cnt} additional `{r_type}` aliases omitted)* | | |"
                    )

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

        near_or_variant_actions = [
            a
            for a in self.actions
            if a.match_type
            in (
                MatchType.NEAR_EXACT.value,
                MatchType.INCLUSIVE_WRITING_VARIANT.value,
                MatchType.PHRASING_VARIANT.value,
                MatchType.TYPOGRAPHICAL_VARIANT.value,
                "NEAR_EXACT",
                "INCLUSIVE_WRITING_VARIANT",
                "PHRASING_VARIANT",
                "TYPOGRAPHICAL_VARIANT",
            )
        ]
        if near_or_variant_actions:
            lines.extend(
                [
                    "",
                    "## High-Similarity & Wording Variant Candidates (Review Flagged)",
                    "",
                    "> [!IMPORTANT]",
                    (
                        f"> **{len(near_or_variant_actions):,} candidate pairs** exhibit "
                        "near-exact equivalence, punctuation variance, inclusive writing, or "
                        "minor phrasing/typo shifts. Review and confirm `alias`, `absorb`, or "
                        "`elevate` actions."
                    ),
                    "",
                    "| ID | Match Type | Action | Type | Source URN | Target URN | Conf |",
                    "| :--- | :--- | :--- | :--- | :--- | :--- | :---: |",
                ]
            )
            for act in near_or_variant_actions[:50]:
                tgt = f"`{act.target_urn}`" if act.target_urn else "-"
                lines.append(
                    f"| `{act.id}` | `{act.match_type}` | `{act.action}` | `{act.resource_type}` | "
                    f"`{act.source_urn}` | {tgt} | {act.confidence:.2f} |"
                )

        group_actions = [
            a
            for a in self.actions
            if a.action == "group"
            or a.match_type
            in (
                MatchType.SHARED_STEM.value,
                "SHARED_STEM",
                MatchType.SHARED_STEM_GRID.value,
                "SHARED_STEM_GRID",
            )
        ]
        if group_actions:
            lines.extend(
                [
                    "",
                    "## Shared-Stem Grids & Resource Groups (Review Flagged)",
                    "",
                    "> [!NOTE]",
                    (
                        f"> **{len(group_actions):,} candidate pairs** share a common "
                        "question/category stem with distinct sub-items and are proposed for "
                        "grouping (`Group` with `group_type='question_grid'`)."
                    ),
                    "",
                    "| ID | Group Type | Type | Source URN | Target URN | Shared Stem |",
                    "| :--- | :--- | :--- | :--- | :--- | :--- |",
                ]
            )
            for act in group_actions[:50]:
                g_type = act.details.get("group_type", "question_grid")
                stem = str(act.details.get("shared_stem", "-"))
                if len(stem) > 60:
                    stem = stem[:57] + "..."
                tgt = f"`{act.target_urn}`" if act.target_urn else "-"
                lines.append(
                    f"| `{act.id}` | `{g_type}` | `{act.resource_type}` | "
                    f"`{act.source_urn}` | {tgt} | {stem} |"
                )

        scale_divergent_actions = [
            a
            for a in self.actions
            if a.match_type
            in (
                MatchType.SAME_CONCEPT_DIVERGENT_DOMAIN.value,
                "SAME_CONCEPT_DIVERGENT_DOMAIN",
                MatchType.SAME_CONCEPT_DIFFERENT_SCALE.value,
                "SAME_CONCEPT_DIFFERENT_SCALE",
            )
        ]
        if scale_divergent_actions:
            lines.extend(
                [
                    "",
                    "## Divergent Response Scale Candidates (Review Flagged)",
                    "",
                    "> [!WARNING]",
                    (
                        f"> **{len(scale_divergent_actions):,} candidate pairs** share variable "
                        "labels but use divergent response scales (`CodeList`). Action is "
                        "downgraded to `link_semantic` to preserve value domain integrity."
                    ),
                    "",
                    "| ID | Type | Source URN | Target URN | Source CodeList | Target CodeList |",
                    "| :--- | :--- | :--- | :--- | :--- | :--- |",
                ]
            )
            for act in scale_divergent_actions[:50]:
                tgt = f"`{act.target_urn}`" if act.target_urn else "-"
                src_cl = act.details.get("source_codelist_urn") or "-"
                tgt_cl = act.details.get("target_codelist_urn") or "-"
                lines.append(
                    f"| `{act.id}` | `{act.resource_type}` | `{act.source_urn}` | {tgt} | "
                    f"`{src_cl}` | `{tgt_cl}` |"
                )

        if self.actions:
            lines.extend(
                [
                    "",
                    f"## Planned Actions ({len(self.actions)} total)",
                    "",
                    "| ID | Action | Resource Type | Source URN | Target URN | Conf | Review? |",
                    "| :--- | :--- | :--- | :--- | :--- | :---: | :---: |",
                ]
            )
            for act in self.actions[:200]:
                tgt = f"`{act.target_urn}`" if act.target_urn else "-"
                rev = "Yes" if act.requires_review else "No"
                lines.append(
                    f"| `{act.id}` | `{act.action}` | `{act.resource_type}` | "
                    f"`{act.source_urn}` | {tgt} | {act.confidence:.2f} | {rev} |"
                )
            if len(self.actions) > 200:
                lines.append(f"\n*... and {len(self.actions) - 200} additional action items.*")

        lines.append("")
        content = "\n".join(lines)
        if path is not None:
            out_path = Path(path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(content, encoding="utf-8")
        return content
