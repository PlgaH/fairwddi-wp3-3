"""Declarative configuration schema and YAML loader for three-layer DDI comparison."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import AliasChoices, BaseModel, Field

from fairwddi.compare.models import CorrespondenceLevel


class SyntacticRuleConfig(BaseModel):
    """Configuration rules for Level 1 syntactic/textual comparison."""

    enabled: bool = True
    threshold: float = Field(
        default=0.80,
        ge=0.0,
        le=1.0,
        validation_alias=AliasChoices("threshold", "min_score"),
    )
    near_exact_threshold: float = Field(default=0.90, ge=0.0, le=1.0)
    multilingual_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    detect_typos: bool = Field(
        default=True,
        validation_alias=AliasChoices("detect_typos", "enable_typo_variants"),
    )
    detect_inclusive: bool = Field(
        default=True,
        validation_alias=AliasChoices("detect_inclusive", "enable_inclusive_markers"),
    )
    detect_wording: bool = Field(
        default=True,
        validation_alias=AliasChoices("detect_wording", "enable_wording_variants"),
    )
    detect_shared_stems: bool = Field(
        default=True,
        validation_alias=AliasChoices("detect_shared_stems", "enable_stem_grids"),
    )
    min_stem_length: int = Field(
        default=12,
        ge=4,
        validation_alias=AliasChoices("min_stem_length", "min_stem_len"),
    )
    enable_token_blocking: bool = True
    use_character_ngrams: bool = True
    min_shared_tokens: int = Field(default=1, ge=1)
    language: str = "fr"
    weight_label: float = Field(default=0.7, ge=0.0, le=1.0)
    weight_codelist: float = Field(default=0.3, ge=0.0, le=1.0)


class SemanticRuleConfig(BaseModel):
    """Configuration rules for Level 2 vector/embedding & agent-assisted semantic comparison."""

    enabled: bool = True
    threshold: float = Field(
        default=0.72,
        ge=0.0,
        le=1.0,
        validation_alias=AliasChoices("threshold", "min_score"),
    )
    provider: str = Field(
        default="tfidf",
        validation_alias=AliasChoices("provider", "embedding_provider"),
    )
    model_name: str | None = None
    ngram_range: tuple[int, int] = (1, 2)
    top_k: int = Field(default=5, ge=1)
    agent_backend: Literal["none", "mock"] = "none"
    detect_dimension_mismatch: bool = True


class ConceptualRuleConfig(BaseModel):
    """Configuration rules for Level 3 controlled-vocabulary / concept-graph comparison."""

    enabled: bool = True
    threshold: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        validation_alias=AliasChoices("threshold", "min_score"),
    )
    require_shared_concept: bool = True
    allow_hierarchy_ancestors: bool = True
    max_hierarchy_hops: int = Field(default=2, ge=0, le=6)
    vocabularies: list[str] = Field(default_factory=list)
    auto_assign_concepts: bool = False


class QualificationRuleConfig(BaseModel):
    """Rules for independent response-scale (CodeList) and missing-value qualification."""

    enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices("enabled", "evaluate_codelists"),
    )
    exclude_missing_from_scale_diff: bool = Field(
        default=True,
        validation_alias=AliasChoices("exclude_missing_from_scale_diff", "isolate_missing_values"),
    )
    warn_on_scale_cardinality_diff: bool = Field(
        default=True,
        validation_alias=AliasChoices("warn_on_scale_cardinality_diff", "flag_scale_differences"),
    )
    warn_on_dimension_mismatch: bool = Field(
        default=True,
        validation_alias=AliasChoices("warn_on_dimension_mismatch", "flag_dimension_mismatch"),
    )
    warn_on_administration_context: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "warn_on_administration_context", "flag_administration_context"
        ),
    )
    allow_recoded_same_categories: bool = True
    codelist_label_threshold: float = Field(default=0.85, ge=0.0, le=1.0)


class ResourceTypeComparisonRule(BaseModel):
    """Per-resource-type comparison configuration combining all three layers + qualification."""

    enabled: bool = True
    fields: list[str] = Field(default_factory=lambda: ["label", "name"])
    languages: list[str] = Field(default_factory=list)
    syntactic: SyntacticRuleConfig = Field(default_factory=SyntacticRuleConfig)
    semantic: SemanticRuleConfig = Field(default_factory=SemanticRuleConfig)
    conceptual: ConceptualRuleConfig = Field(default_factory=ConceptualRuleConfig)
    qualification: QualificationRuleConfig = Field(default_factory=QualificationRuleConfig)


DEFAULT_COMPARISON_TYPES: tuple[str, ...] = (
    "QuestionItem",
    "RepresentedVariable",
    "CodeList",
    "Category",
    "ConceptualVariable",
)


class ComparisonConfig(BaseModel):
    """Top-level declarative configuration governing a two-set DDI comparison run."""

    name: str = "default"
    description: str = ""
    levels: list[CorrespondenceLevel] = Field(
        default_factory=lambda: [
            CorrespondenceLevel.SYNTACTIC,
            CorrespondenceLevel.SEMANTIC,
            CorrespondenceLevel.CONCEPTUAL,
        ]
    )
    resource_types: list[str] = Field(default_factory=lambda: list(DEFAULT_COMPARISON_TYPES))
    exclude_same_urn: bool = True
    max_candidates_per_source: int = Field(default=5, ge=1)
    rules: dict[str, ResourceTypeComparisonRule] = Field(default_factory=dict)

    def rule_for(self, resource_type: str) -> ResourceTypeComparisonRule:
        """Return configured rule for `resource_type`, falling back to canonical defaults."""
        if resource_type in self.rules:
            return self.rules[resource_type]
        default_fields = {
            "QuestionItem": ["question_text", "label"],
            "RepresentedVariable": ["label", "description", "question_text"],
            "CodeList": ["codes", "label"],
            "Category": ["label"],
            "ConceptualVariable": ["label", "description"],
        }.get(resource_type, ["label", "name"])
        return ResourceTypeComparisonRule(fields=default_fields)


def _compare_profile_dirs() -> list[Path]:
    return [
        Path.cwd() / "profiles" / "compare",
        Path(__file__).parent.parent.parent.parent / "profiles" / "compare",
    ]


def load_comparison_config(name_or_path: str | Path | None = None) -> ComparisonConfig:
    """Load a ComparisonConfig from a built-in preset name or YAML/JSON file path."""
    if name_or_path is None:
        name = "default"
    else:
        cand = Path(str(name_or_path))
        if cand.is_file():
            raw = yaml.safe_load(cand.read_text(encoding="utf-8")) or {}
            return ComparisonConfig.model_validate(raw)
        name = str(name_or_path).strip()

    for pdir in _compare_profile_dirs():
        for ext in (".yaml", ".yml", ".json"):
            fpath = pdir / f"{name}{ext}"
            if fpath.is_file():
                raw = yaml.safe_load(fpath.read_text(encoding="utf-8")) or {}
                raw.setdefault("name", name)
                return ComparisonConfig.model_validate(raw)

    if name == "default":
        return ComparisonConfig()

    raise FileNotFoundError(
        f"Comparison config '{name_or_path}' not found in profiles/compare or on disk."
    )


def list_comparison_configs() -> list[dict[str, Any]]:
    """List available comparison presets discovered in ``profiles/compare``."""
    found: dict[str, dict[str, Any]] = {}
    for pdir in _compare_profile_dirs():
        if not pdir.is_dir():
            continue
        for p in sorted(pdir.glob("*.y*ml")):
            try:
                raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
                cfg_name = str(raw.get("name") or p.stem)
                if cfg_name not in found:
                    found[cfg_name] = {
                        "name": cfg_name,
                        "description": str(raw.get("description") or ""),
                        "levels": raw.get("levels") or [],
                        "resource_types": raw.get("resource_types") or [],
                        "path": str(p),
                    }
            except Exception:
                continue
    return list(found.values())
