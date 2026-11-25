"""Level 2 Semantic Vector & Agent-Assisted comparator (`fairwddi.compare.semantic`).

Uses pluggable `EmbeddingProvider` backends (default: `DefaultTfIdfEmbeddingProvider`
from `dartfx.ddi.harmonizer`, optional local/HF `sentence-transformers` hook) and
optional `AgentComparator` qualification (`RuleBasedMockAgentComparator`) to discover
paraphrases and semantic correspondences beyond surface spelling.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from dartfx.ddi.harmonizer import (
    DefaultTfIdfEmbeddingProvider,
    EmbeddingProvider,
    SemanticVectorComparator,
)
from dartfx.ddi.harmonizer.comparators.agent import RuleBasedMockAgentComparator

from fairwddi.compare.config import ResourceTypeComparisonRule
from fairwddi.compare.models import CorrespondenceLevel

ProviderFactory = Callable[[ResourceTypeComparisonRule], EmbeddingProvider]
_EMBEDDING_REGISTRY: dict[str, ProviderFactory] = {}


class SentenceTransformerEmbeddingProvider:
    """Lazy-imported optional dense embedding provider backed by `sentence-transformers`."""

    def __init__(self, model_name: str = "BAAI/bge-m3") -> None:
        self.model_name = model_name
        self._model: Any = None

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """Encode `texts` into dense vectors (requires optional `sentence-transformers`)."""
        if self._model is None:
            try:
                from sentence_transformers import (
                    SentenceTransformer,  # type: ignore[import-not-found]
                )
            except ImportError as exc:
                raise ImportError(
                    "Embedding provider 'sentence-transformers' requires the optional package "
                    "'sentence-transformers' to be installed."
                ) from exc
            self._model = SentenceTransformer(self.model_name)
        vectors = self._model.encode(list(texts), normalize_embeddings=True)
        return [[float(x) for x in row] for row in vectors]


def register_embedding_provider(name: str, factory: ProviderFactory) -> None:
    """Register a custom EmbeddingProvider factory under `name`."""
    _EMBEDDING_REGISTRY[name.strip().lower()] = factory


def get_embedding_provider(rule: ResourceTypeComparisonRule) -> EmbeddingProvider:
    """Resolve an `EmbeddingProvider` instance from a rule's semantic configuration."""
    provider_key = rule.semantic.provider.strip().lower()
    if provider_key in _EMBEDDING_REGISTRY:
        return _EMBEDDING_REGISTRY[provider_key](rule)
    if provider_key == "tfidf":
        return DefaultTfIdfEmbeddingProvider(ngram_range=rule.semantic.ngram_range)
    if provider_key in ("sentence-transformers", "sentence_transformers", "bge"):
        return SentenceTransformerEmbeddingProvider(
            model_name=rule.semantic.model_name or "BAAI/bge-m3"
        )
    raise ValueError(
        f"Unsupported embedding provider '{rule.semantic.provider}'. "
        "Built-in providers: 'tfidf', 'sentence-transformers'."
    )


def _record_semantic_text(rec: dict[str, Any]) -> str:
    parts: list[str] = []
    ml = rec.get("ml_text") or {}
    if ml:
        for txt in ml.values():
            if txt:
                parts.append(str(txt))
    elif rec.get("text"):
        parts.append(str(rec["text"]))
    # Include substantive category labels lightly to enrich variable context
    sub_labels = [lbl for _, lbl, is_miss in (rec.get("codes") or []) if not is_miss and lbl]
    if sub_labels:
        parts.append(" ".join(sub_labels[:8]))
    return " ".join(parts).strip()


def compare_semantic_sets(
    source_records: list[dict[str, Any]],
    target_records: list[dict[str, Any]],
    resource_type: str,
    rule: ResourceTypeComparisonRule,
    *,
    exclude_same_urn: bool = True,
    symmetric_sets: bool = False,
) -> list[dict[str, Any]]:
    """Run Level 2 batch vector similarity + optional agent nuance checks."""
    sem_cfg = rule.semantic
    if not sem_cfg.enabled or not source_records or not target_records:
        return []

    src_texts = [_record_semantic_text(r) for r in source_records]
    tgt_texts = [_record_semantic_text(r) for r in target_records]

    valid_src_idx = [i for i, t in enumerate(src_texts) if t]
    valid_tgt_idx = [j for j, t in enumerate(tgt_texts) if t]
    if not valid_src_idx or not valid_tgt_idx:
        return []

    provider = get_embedding_provider(rule)
    corpus = [src_texts[i] for i in valid_src_idx] + [tgt_texts[j] for j in valid_tgt_idx]
    vectors = provider.embed_texts(corpus)

    src_vecs = vectors[: len(valid_src_idx)]
    tgt_vecs = vectors[len(valid_src_idx) :]

    agent = RuleBasedMockAgentComparator() if sem_cfg.agent_backend == "mock" else None
    candidates: list[dict[str, Any]] = []
    seen_sym_pairs: set[tuple[str, str]] = set()

    for s_pos, src_orig_idx in enumerate(valid_src_idx):
        src = source_records[src_orig_idx]
        s_vec = src_vecs[s_pos]
        scored: list[tuple[float, dict[str, Any], int]] = []

        for t_pos, tgt_orig_idx in enumerate(valid_tgt_idx):
            tgt = target_records[tgt_orig_idx]
            if exclude_same_urn and src["urn"] == tgt["urn"]:
                continue
            if symmetric_sets:
                pair_key = (min(src["urn"], tgt["urn"]), max(src["urn"], tgt["urn"]))
                if pair_key in seen_sym_pairs:
                    continue

            cos_sim = SemanticVectorComparator._cosine_similarity(s_vec, tgt_vecs[t_pos])
            if cos_sim >= sem_cfg.threshold:
                scored.append((cos_sim, tgt, t_pos))

        scored.sort(key=lambda x: x[0], reverse=True)
        for cos_sim, tgt, _ in scored[: sem_cfg.top_k]:
            if symmetric_sets:
                pair_key = (min(src["urn"], tgt["urn"]), max(src["urn"], tgt["urn"]))
                if pair_key in seen_sym_pairs:
                    continue
                seen_sym_pairs.add(pair_key)

            details: dict[str, Any] = {
                "embedding_provider": sem_cfg.provider,
                "cosine_similarity": round(float(cos_sim), 4),
            }
            if agent is not None:
                eval_res = agent.evaluate(
                    src.get("text") or "",
                    tgt.get("text") or "",
                    prompt_context=f"DDI {resource_type} semantic comparison",
                )
                details["agent_decision"] = eval_res.decision
                details["agent_reasoning"] = eval_res.reasoning
                if eval_res.subtle_differences:
                    details["subtle_differences"] = eval_res.subtle_differences

            candidates.append(
                {
                    "level": CorrespondenceLevel.SEMANTIC,
                    "resource_type": resource_type,
                    "source_rec": src,
                    "target_rec": tgt,
                    "match_type": "SEMANTIC_VECTOR_MATCH",
                    "confidence": round(min(1.0, float(cos_sim)), 4),
                    "requires_review": True,
                    "details": details,
                }
            )

    return candidates
