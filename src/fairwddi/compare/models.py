"""Structured data models for three-layer DDI resource comparison and qualification."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field


class CorrespondenceLevel(StrEnum):
    """Canonical DDI correspondence discovery level aligned with CDSP ReQuest framing."""

    SYNTACTIC = "syntactic"
    SEMANTIC = "semantic"
    CONCEPTUAL = "conceptual"


class CodeListQualification(StrEnum):
    """Independent response-domain qualification attached to variable/question comparisons."""

    IDENTICAL = "IDENTICAL"
    MISSING_VALUES_ONLY = "MISSING_VALUES_ONLY"
    LABELS_SLIGHT_DIFF = "LABELS_SLIGHT_DIFF"
    SCALE_CARDINALITY_DIFF = "SCALE_CARDINALITY_DIFF"
    RECODED_SAME_CATEGORIES = "RECODED_SAME_CATEGORIES"
    DIMENSION_MISMATCH_SUSPECTED = "DIMENSION_MISMATCH_SUSPECTED"
    UNCOMPARABLE_OR_UNCODED = "UNCOMPARABLE_OR_UNCODED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class QualificationReport(BaseModel):
    """Response-scale, missing-value, and administration-context qualification for a candidate."""

    codelist_qualification: CodeListQualification = CodeListQualification.NOT_APPLICABLE
    source_codelist_urn: str | None = None
    target_codelist_urn: str | None = None
    substantive_count_source: int = 0
    substantive_count_target: int = 0
    missing_count_source: int = 0
    missing_count_target: int = 0
    missing_values_excluded: list[str] = Field(default_factory=list)
    codelist_similarity: float | None = None
    dimension_note: str | None = None
    administration_context_caveat: str | None = None
    notes: list[str] = Field(default_factory=list)
    compatible_for_merge: bool = True


class CandidateCorrespondence(BaseModel):
    """Single discovered correspondence candidate between a source and target resource."""

    id: str
    level: CorrespondenceLevel
    resource_type: str
    source_urn: str
    target_urn: str
    source_origin: str = "imported"
    target_origin: str = "imported"
    match_type: str
    confidence: float
    recommended_action: Literal[
        "link_existing",
        "generate_harmonized",
        "link_semantic",
        "group",
        "review",
    ] = "review"
    requires_review: bool = True
    rationale: str = ""
    source_text: dict[str, str] = Field(default_factory=dict)
    target_text: dict[str, str] = Field(default_factory=dict)
    qualification: QualificationReport = Field(default_factory=QualificationReport)
    details: dict[str, Any] = Field(default_factory=dict)


class ComparisonResultSet(BaseModel):
    """Serializable comparison output consumed by analysts and `harmonize plan`."""

    comparison_version: str = "1.0"
    job_id: str
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    source_spec: str
    target_spec: str
    config_name: str = "default"
    levels: list[CorrespondenceLevel] = Field(default_factory=list)
    resource_types: list[str] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    candidates: list[CandidateCorrespondence] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain JSON-compatible dictionary."""
        return self.model_dump(mode="json")

    def to_yaml(self, path: Path | str | None = None) -> str:
        """Serialize comparison result set to YAML and optionally write to disk."""
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
        """Serialize comparison result set to JSON and optionally write to disk."""
        content = self.model_dump_json(indent=indent)
        if path is not None:
            out_path = Path(path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(content, encoding="utf-8")
        return content

    @classmethod
    def load(cls, path_or_str: Path | str) -> ComparisonResultSet:
        """Load a ComparisonResultSet from a YAML or JSON file path or string."""
        if isinstance(path_or_str, Path) or (
            isinstance(path_or_str, str) and "\n" not in path_or_str and Path(path_or_str).exists()
        ):
            raw_text = Path(path_or_str).read_text(encoding="utf-8")
        else:
            raw_text = str(path_or_str)
        data = yaml.safe_load(raw_text) or {}
        return cls.model_validate(data)

    @classmethod
    def from_yaml(cls, path_or_str: Path | str) -> ComparisonResultSet:
        """Load a ComparisonResultSet from YAML/JSON."""
        return cls.load(path_or_str)

    def to_markdown(self, path: Path | str | None = None) -> str:
        """Render a detailed analytical comparison report grouped by correspondence level."""
        lines: list[str] = [
            f"# FAIRwDDI Three-Layer Comparison Report — `{self.job_id}`",
            "",
            "## Scope & Configuration",
            "",
            f"- **Source Set:** `{self.source_spec}`",
            f"- **Target Set:** `{self.target_spec}`",
            f"- **Configuration:** `{self.config_name}`",
            f"- **Levels:** {', '.join(f'`{lvl.value}`' for lvl in self.levels) or '-'}",
            f"- **Resource Types:** {', '.join(f'`{rt}`' for rt in self.resource_types) or '-'}",
            f"- **Created At:** `{self.created_at}`",
            f"- **Total Candidates:** `{len(self.candidates)}`",
        ]

        if self.summary:
            lines.extend(["", "## Summary Metrics", "", "| Metric | Value |", "| :--- | :--- |"])
            for k, v in self.summary.items():
                lines.append(f"| `{k}` | `{v}` |")

        for lvl in CorrespondenceLevel:
            lvl_cands = [c for c in self.candidates if c.level == lvl]
            if not lvl_cands:
                continue
            lines.extend(
                [
                    "",
                    f"## Level: `{lvl.value.upper()}` ({len(lvl_cands)} candidates)",
                    "",
                    "| ID | Type | Source URN | Target URN | Match Type | Conf | "
                    "CodeList Qualification | Action |",
                    "| :--- | :--- | :--- | :--- | :--- | :---: | :--- | :--- |",
                ]
            )
            for c in lvl_cands[:150]:
                lines.append(
                    f"| `{c.id}` | `{c.resource_type}` | `{c.source_urn}` | `{c.target_urn}` | "
                    f"`{c.match_type}` | {c.confidence:.2f} | "
                    f"`{c.qualification.codelist_qualification.value}` | "
                    f"`{c.recommended_action}` |"
                )
            if len(lvl_cands) > 150:
                lines.append(
                    f"\n*... and {len(lvl_cands) - 150} additional `{lvl.value}` candidates.*"
                )

        divergent = [
            c
            for c in self.candidates
            if c.qualification.codelist_qualification
            in (
                CodeListQualification.SCALE_CARDINALITY_DIFF,
                CodeListQualification.DIMENSION_MISMATCH_SUSPECTED,
            )
        ]
        if divergent:
            lines.extend(
                [
                    "",
                    "## Qualification Warnings (Scale & Dimension Divergence)",
                    "",
                    "> [!WARNING]",
                    (
                        f"> **{len(divergent)} candidate pair(s)** exhibit response-scale "
                        "cardinality differences or suspected dimension mismatch and should not "
                        "be merged automatically."
                    ),
                    "",
                    "| ID | Source URN | Target URN | Qualification | Notes |",
                    "| :--- | :--- | :--- | :--- | :--- |",
                ]
            )
            for c in divergent[:50]:
                note_txt = "; ".join(c.qualification.notes) or (
                    c.qualification.dimension_note or "-"
                )
                lines.append(
                    f"| `{c.id}` | `{c.source_urn}` | `{c.target_urn}` | "
                    f"`{c.qualification.codelist_qualification.value}` | {note_txt} |"
                )

        lines.append("")
        content = "\n".join(lines)
        if path is not None:
            out_path = Path(path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(content, encoding="utf-8")
        return content
