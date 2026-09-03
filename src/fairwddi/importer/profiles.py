"""Import profile definitions and YAML/JSON loader for FAIRwDDI.

Governs resource filtering, referential integrity traversal, and duplicate/drift strategies.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field


class ImportStrategies(BaseModel):
    """Collision and duplicate resolution strategies for an import session."""

    on_duplicate_file: Literal["skip", "force_reload", "fail"] = Field(
        default="skip",
        description="Action when exact same file (matching SHA-256) is imported again.",
    )
    on_existing_resource: Literal["insert_new_only", "fail", "replace"] = Field(
        default="insert_new_only",
        description="Action when incoming resource URN already exists with identical content.",
    )
    on_content_drift: Literal["quarantine", "reject", "overwrite"] = Field(
        default="quarantine",
        description="Action when incoming resource URN exists with differing content.",
    )


class ImportProfile(BaseModel):
    """Configuration profile defining resource filtering and collision rules for metadata import."""

    name: str = Field(..., description="Unique profile identifier.")
    description: str = Field(
        default="", description="Human-readable description of profile intent."
    )
    include_types: list[str] = Field(
        default_factory=list,
        description="List of target resource types to stage. If empty, all types are included.",
    )
    exclude_types: list[str] = Field(
        default_factory=list,
        description="Hard blocklist of resource types to never stage, even if referenced.",
    )
    include_referenced_resources: bool = Field(
        default=True,
        description="If True, retain unlisted resources that are referenced by included elements.",
    )
    strategies: ImportStrategies = Field(
        default_factory=ImportStrategies,
        description="Configured duplicate and drift strategies.",
    )

    def should_include(self, resource_type: str, is_referenced: bool = False) -> bool:
        """Evaluate if a resource type should be included for staging.

        Precedence rules:
        1. If in exclude_types: Always False (hard block).
        2. If include_types is empty: True (include all).
        3. If in include_types: True.
        4. If is_referenced and include_referenced_resources: True.
        5. Otherwise: False.
        """
        if resource_type in self.exclude_types:
            return False

        if not self.include_types:
            return True

        if resource_type in self.include_types:
            return True

        if is_referenced and self.include_referenced_resources:
            return True

        return False


def _find_profile_file(name_or_path: str | Path) -> Path | None:
    """Find a profile file from path or search directories."""
    path = Path(name_or_path)
    if path.is_file():
        return path

    candidate_dirs = [
        Path.cwd() / "profiles",
        Path(__file__).parent.parent.parent.parent / "profiles",
        Path.cwd(),
    ]

    for c_dir in candidate_dirs:
        for ext in (".yaml", ".yml", ".json"):
            candidate = c_dir / f"{name_or_path}{ext}"
            if candidate.is_file():
                return candidate

    return None


def load_profile(name_or_path: str | Path | None = None) -> ImportProfile:
    """Load an ImportProfile from a YAML/JSON file or preset name.

    Args:
        name_or_path: Profile preset name (e.g. 'request', 'all_ddi') or file path.
                      Defaults to 'request'.

    Returns:
        Configured ImportProfile instance.
    """
    target = name_or_path or "request"
    profile_path = _find_profile_file(target)

    if profile_path and profile_path.exists():
        text = profile_path.read_text(encoding="utf-8")
        if profile_path.suffix.lower() == ".json":
            data = json.loads(text)
        else:
            data = yaml.safe_load(text) or {}
        return ImportProfile(**data)

    if str(target).lower() in ("request", "request_core", "default"):
        return ImportProfile(
            name="request",
            description="CDSP ReQuest question-bank profile (built-in default)",
            include_types=[
                "QuestionItem",
                "QuestionGrid",
                "QuestionConstruct",
                "QuestionGroup",
                "QuestionScheme",
                "StatementItem",
                "Instruction",
                "InterviewerInstruction",
                "InterviewerInstructionScheme",
                "Category",
                "CategorySet",
                "CategoryGroup",
                "CategoryScheme",
                "CodeList",
                "CodeListScheme",
                "CodeItem",
                "ManagedMissingValuesRepresentation",
                "ManagedRepresentationScheme",
                "StatisticalClassification",
                "ClassificationFamily",
                "ClassificationSeries",
                "ClassificationLevel",
                "ClassificationItem",
                "Variable",
                "InstanceVariable",
                "RepresentedVariable",
                "RepresentedVariableGroup",
                "RepresentedVariableScheme",
                "ConceptualVariable",
                "ConceptualVariableGroup",
                "ConceptualVariableScheme",
                "VariableGroup",
                "VariableScheme",
                "Concept",
                "ConceptGroup",
                "ConceptScheme",
                "ConceptualComponent",
                "Universe",
                "UniverseScheme",
                "StudyUnit",
                "Group",
                "DataCollection",
                "DataRelationship",
                "Organization",
                "OrganizationScheme",
            ],
            exclude_types=[
                "Instrument",
                "InstrumentScheme",
                "ControlConstructScheme",
                "Sequence",
                "IfThenElse",
                "Loop",
                "ComputationItem",
                "Archive",
                "DDIInstance",
                "ResourcePackage",
                "PhysicalInstance",
                "PhysicalDataSet",
                "Methodology",
                "ProcessingEvent",
                "ProcessingEventScheme",
                "OtherMaterial",
                "QualityStandard",
                "QualityStatement",
                "VariableStatistics",
            ],
            include_referenced_resources=True,
            strategies=ImportStrategies(),
        )

    return ImportProfile(
        name=str(target),
        description=f"Profile '{target}'",
        include_types=[],
        exclude_types=[],
        include_referenced_resources=True,
        strategies=ImportStrategies(),
    )


def list_available_profiles() -> list[dict[str, Any]]:
    """Scan and list available profiles in the profiles/ directory."""
    profiles = []
    candidate_dirs = [
        Path.cwd() / "profiles",
        Path(__file__).parent.parent.parent.parent / "profiles",
    ]

    seen = set()
    for c_dir in candidate_dirs:
        if c_dir.is_dir():
            for f in sorted(c_dir.glob("*.*")):
                if f.suffix.lower() in (".yaml", ".yml", ".json") and f.stem not in seen:
                    seen.add(f.stem)
                    try:
                        p = load_profile(f)
                        profiles.append(
                            {
                                "name": p.name,
                                "file": str(f),
                                "description": p.description,
                                "include_types_count": len(p.include_types),
                                "exclude_types_count": len(p.exclude_types),
                                "include_referenced_resources": p.include_referenced_resources,
                            }
                        )
                    except Exception:
                        pass
    return profiles
