"""Harmonization policy, action plan, and Markdown report models (`fairwddi.harmonize.plan`)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field

from fairwddi.compare.models import CodeListQualification, CorrespondenceLevel
from fairwddi.importer.plan import ReviewGate


class AutoApproveHighPolicy(BaseModel):
    """Explicit definition of what counts as ``high`` for ``--approve-high`` auto-approval."""

    min_confidence: float = Field(default=0.90, ge=0.0, le=1.0)
    allowed_levels: list[str] = Field(default_factory=lambda: ["syntactic"])
    allowed_match_types: list[str] = Field(
        default_factory=lambda: [
            "EXACT_IDENTICAL",
            "NORMALIZED_EXACT",
            "SUBSTANTIVE_EXACT",
            "NEAR_EXACT",
            "INCLUSIVE_WRITING_VARIANT",
            "TYPOGRAPHICAL_VARIANT",
            "PHRASING_VARIANT",
        ]
    )
    allowed_codelist_qualifications: list[str] = Field(
        default_factory=lambda: ["IDENTICAL", "MISSING_VALUES_ONLY", "NOT_APPLICABLE"]
    )
    allowed_actions: list[str] = Field(
        default_factory=lambda: ["link_existing", "generate_harmonized"]
    )
    non_high_behavior: Literal["pending_review", "skip"] = "pending_review"


class GuardrailPolicy(BaseModel):
    """Safety guardrails preventing invalid structural merges."""

    downgrade_scale_cardinality_diff_to_semantic_link: bool = True
    downgrade_dimension_mismatch_to_semantic_link: bool = True
    downgrade_uncoded_to_semantic_link: bool = True
    group_shared_stem_grids: bool = True


HarmonizationGuardrails = GuardrailPolicy


class HarmonizationPolicy(BaseModel):
    """Policy governing conversion of comparison candidates into harmonization actions."""

    name: str = "default"
    description: str = ""
    auto_approve_high: AutoApproveHighPolicy = Field(default_factory=AutoApproveHighPolicy)
    guardrails: GuardrailPolicy = Field(default_factory=GuardrailPolicy)

    def qualifies_as_high(
        self,
        item: HarmonizationActionItem,
        *,
        high_threshold_override: float | None = None,
    ) -> bool:
        """Return True iff `item` satisfies every criterion in `auto_approve_high`."""
        cfg = self.auto_approve_high
        eff_min = (
            high_threshold_override if high_threshold_override is not None else cfg.min_confidence
        )
        if item.action not in cfg.allowed_actions:
            return False
        if item.confidence < eff_min:
            return False
        lvl_str = (
            item.level.value if isinstance(item.level, CorrespondenceLevel) else str(item.level)
        )
        if lvl_str not in cfg.allowed_levels:
            return False
        if item.match_type not in cfg.allowed_match_types:
            return False
        qual_str = (
            item.codelist_qualification.value
            if isinstance(item.codelist_qualification, CodeListQualification)
            else str(item.codelist_qualification)
        )
        if qual_str not in cfg.allowed_codelist_qualifications:
            return False
        return True


def _harmonize_profile_dirs() -> list[Path]:
    return [
        Path.cwd() / "profiles" / "harmonize",
        Path(__file__).parent.parent.parent.parent / "profiles" / "harmonize",
    ]


def load_harmonization_policy(name_or_path: str | Path | None = None) -> HarmonizationPolicy:
    """Load a HarmonizationPolicy from a built-in preset name or YAML file."""
    if name_or_path is None:
        name = "default"
    else:
        cand = Path(str(name_or_path))
        if cand.is_file():
            raw = yaml.safe_load(cand.read_text(encoding="utf-8")) or {}
            return HarmonizationPolicy.model_validate(raw)
        name = str(name_or_path).strip()

    for pdir in _harmonize_profile_dirs():
        for ext in (".yaml", ".yml", ".json"):
            fpath = pdir / f"{name}{ext}"
            if fpath.is_file():
                raw = yaml.safe_load(fpath.read_text(encoding="utf-8")) or {}
                raw.setdefault("name", name)
                return HarmonizationPolicy.model_validate(raw)

    if name == "default":
        return HarmonizationPolicy()

    raise FileNotFoundError(
        f"Harmonization policy '{name_or_path}' not found in profiles/harmonize or on disk."
    )


class HarmonizationActionItem(BaseModel):
    """Planned or approved harmonization write action derived from a comparison candidate."""

    id: str
    candidate_id: str | None = None
    action: Literal["link_existing", "generate_harmonized", "link_semantic", "group", "skip"]
    resource_type: str
    source_urn: str
    target_urn: str
    generated_urn: str | None = None
    level: CorrespondenceLevel = CorrespondenceLevel.SYNTACTIC
    match_type: str
    confidence: float
    codelist_qualification: CodeListQualification = CodeListQualification.NOT_APPLICABLE
    approval_tier: Literal["high", "review_required"] = "review_required"
    approved: bool = False
    requires_review: bool = True
    details: dict[str, Any] = Field(default_factory=dict)
    notes: str = ""

    @property
    def correspondence_level(self) -> str:
        """Canonical string value for the candidate's correspondence level."""
        return self.level.value if isinstance(self.level, CorrespondenceLevel) else str(self.level)

    @property
    def is_high_confidence(self) -> bool:
        """True if this action qualified under the policy's ``auto_approve_high`` tier."""
        return self.approval_tier == "high"


class HarmonizationPlan(BaseModel):
    """Serializable, review-gated harmonization execution plan."""

    plan_version: str = "2.0"
    stage: Literal["harmonize"] = "harmonize"
    job_id: str
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    comparison_job_id: str | None = None
    source_spec: str | None = None
    target_spec: str | None = None
    policy_name: str = "default"
    approve_high_applied: bool = False
    review_gate: ReviewGate = Field(default_factory=ReviewGate)
    summary: dict[str, Any] = Field(default_factory=dict)
    actions: list[HarmonizationActionItem] = Field(default_factory=list)

    @property
    def approved_count(self) -> int:
        """Count of approved non-skip actions."""
        return sum(1 for a in self.actions if a.approved and a.action != "skip")

    @property
    def pending_review_count(self) -> int:
        """Count of non-skip actions awaiting review."""
        return sum(
            1 for a in self.actions if a.requires_review and not a.approved and a.action != "skip"
        )

    @property
    def high_tier_count(self) -> int:
        """Count of actions qualifying as `high` under policy."""
        return sum(1 for a in self.actions if a.approval_tier == "high")

    def is_ready_to_execute(self, auto_approve: bool = False) -> bool:
        """Return True if authorized to execute approved actions."""
        if auto_approve or self.review_gate.approved:
            return True
        return self.approved_count > 0 and self.pending_review_count == 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize plan to JSON-safe dictionary with live summary counts."""
        data = self.model_dump(mode="json")
        data["summary"] = {
            **self.summary,
            "total_actions": len(self.actions),
            "approved_count": self.approved_count,
            "pending_review_count": self.pending_review_count,
            "high_tier_count": self.high_tier_count,
        }
        return data

    def to_yaml(self, path: Path | str | None = None) -> str:
        """Serialize plan to YAML and optionally write to disk."""
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
    def from_yaml(cls, path_or_str: Path | str) -> HarmonizationPlan:
        """Load a HarmonizationPlan from YAML file path or string."""
        if isinstance(path_or_str, Path) or (
            isinstance(path_or_str, str) and "\n" not in path_or_str and Path(path_or_str).exists()
        ):
            raw_text = Path(path_or_str).read_text(encoding="utf-8")
        else:
            raw_text = str(path_or_str)
        data = yaml.safe_load(raw_text) or {}
        return cls.model_validate(data)

    def to_markdown(self, path: Path | str | None = None) -> str:
        """Render human-readable Markdown summary for this harmonization plan."""
        gate_label = (
            "APPROVED"
            if self.review_gate.approved
            else ("READY" if self.is_ready_to_execute() else "PENDING REVIEW")
        )
        lines: list[str] = [
            f"# FAIRwDDI `HARMONIZE` Plan — `{self.job_id}`",
            "",
            "## Overview",
            "",
            f"- **Job ID:** `{self.job_id}`",
            f"- **Comparison Job:** `{self.comparison_job_id or '-'}`",
            f"- **Source Set:** `{self.source_spec or '-'}`",
            f"- **Target Set:** `{self.target_spec or '-'}`",
            f"- **Policy:** `{self.policy_name}`",
            f"- **`--approve-high` Applied:** `{self.approve_high_applied}`",
            f"- **Review Gate:** **{gate_label}**",
            (
                f"- **Approved Actions:** `{self.approved_count}` | "
                f"**Pending Review:** `{self.pending_review_count}` | "
                f"**High-Tier Qualifying:** `{self.high_tier_count}`"
            ),
        ]

        if self.actions:
            lines.extend(
                [
                    "",
                    f"## Planned Actions ({len(self.actions)} total)",
                    "",
                    (
                        "| ID | Action | Type | Level | Qual | Conf | "
                        "Tier | Approved? | Source -> Target |"
                    ),
                    "| :--- | :--- | :--- | :--- | :--- | :---: | :--- | :---: | :--- |",
                ]
            )
            for act in self.actions[:200]:
                app_str = "Yes" if act.approved else "No"
                pair = f"`{act.source_urn}` -> `{act.target_urn}`"
                if act.generated_urn:
                    pair += f" (new `{act.generated_urn}`)"
                lines.append(
                    f"| `{act.id}` | `{act.action}` | `{act.resource_type}` | "
                    f"`{act.level.value}` | `{act.codelist_qualification.value}` | "
                    f"{act.confidence:.2f} | `{act.approval_tier}` | {app_str} | {pair} |"
                )

        lines.append("")
        content = "\n".join(lines)
        if path is not None:
            out_path = Path(path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(content, encoding="utf-8")
        return content
