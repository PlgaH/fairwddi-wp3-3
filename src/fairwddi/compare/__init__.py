"""FAIRwDDI Read-Only Two-Set Three-Layer Comparison Engine (`fairwddi.compare`)."""

from __future__ import annotations

from fairwddi.compare.conceptual import (
    ConceptAssigner,
    compare_conceptual_sets,
    register_concept_assigner,
)
from fairwddi.compare.config import (
    DEFAULT_COMPARISON_TYPES,
    ComparisonConfig,
    ConceptualRuleConfig,
    QualificationRuleConfig,
    ResourceTypeComparisonRule,
    SemanticRuleConfig,
    SyntacticRuleConfig,
    list_comparison_configs,
    load_comparison_config,
)
from fairwddi.compare.engine import run_comparison
from fairwddi.compare.models import (
    CandidateCorrespondence,
    CodeListQualification,
    ComparisonResultSet,
    CorrespondenceLevel,
    QualificationReport,
)
from fairwddi.compare.qualifier import evaluate_qualification
from fairwddi.compare.records import load_records_for_urns
from fairwddi.compare.semantic import (
    SentenceTransformerEmbeddingProvider,
    compare_semantic_sets,
    get_embedding_provider,
    register_embedding_provider,
)
from fairwddi.compare.syntactic import compare_syntactic_sets

__all__ = [
    "CorrespondenceLevel",
    "CodeListQualification",
    "QualificationReport",
    "CandidateCorrespondence",
    "ComparisonResultSet",
    "SyntacticRuleConfig",
    "SemanticRuleConfig",
    "ConceptualRuleConfig",
    "QualificationRuleConfig",
    "ResourceTypeComparisonRule",
    "DEFAULT_COMPARISON_TYPES",
    "ComparisonConfig",
    "load_comparison_config",
    "list_comparison_configs",
    "load_records_for_urns",
    "evaluate_qualification",
    "compare_syntactic_sets",
    "SentenceTransformerEmbeddingProvider",
    "register_embedding_provider",
    "get_embedding_provider",
    "compare_semantic_sets",
    "ConceptAssigner",
    "register_concept_assigner",
    "compare_conceptual_sets",
    "run_comparison",
]
