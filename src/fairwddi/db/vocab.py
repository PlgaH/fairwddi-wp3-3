"""Generic SKOS / XKOS controlled vocabulary loader and inspector for FAIRwDDI.

Supports standard-agnostic ingestion of any SKOS / SKOS-XL / XKOS RDF vocabulary
in Turtle (.ttl), RDF/XML (.rdf, .xml), JSON-LD (.jsonld, .json), N-Triples (.nt),
and Notation3 (.n3) formats (e.g., CESSDA ELSST, CESSDA Topics, DDI-CV, UNESCO,
Eurostat RAMON, Agrovoc, STW, custom project taxonomies).
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from django.db import transaction


def check_vocabulary_loaded(vocabulary: str | None = None) -> dict[str, Any]:
    """Check if concepts for a given vocabulary (or any vocabularies) are loaded.

    Returns status summary dictionary.
    """
    from django.db.models import Count

    from fairwddi.models import Concept

    if vocabulary:
        # Match exact or case-insensitive prefix / contains
        qs = Concept.objects.filter(vocabulary__icontains=vocabulary)
        total_count = qs.count()
        top_count = qs.filter(parent__isnull=True).count()

        matched_vocab_name = (
            qs.values_list("vocabulary", flat=True).first() if total_count > 0 else vocabulary
        )

        return {
            "loaded": total_count > 0,
            "vocabulary": matched_vocab_name,
            "total_concepts": total_count,
            "top_concepts": top_count,
        }

    # Summary of all loaded vocabularies
    vocab_groups = list(
        Concept.objects.values("vocabulary").annotate(total=Count("urn")).order_by("vocabulary")
    )
    total_all = Concept.objects.count()

    return {
        "loaded": total_all > 0,
        "vocabulary": None,
        "vocabularies": vocab_groups,
        "total_concepts": total_all,
    }


def extract_urn(
    subject: Any,
    graph: Any,
    fallback_prefix: str = "concept",
    default_agency: str = "fr.sciencespo",
) -> str:
    """Extract authoritative/original URN from RDF node, or synthesize fallback DDI URN.

    Priority:
    1. If the subject URI itself starts with 'urn:', use it directly.
    2. Search dct:identifier, dc:identifier, and skos:notation for values starting with 'urn:'.
    3. Fallback: synthesize 'urn:ddi:{agency}:{fallback_prefix}-{id}:1.0.0'.
    """
    subj_str = str(subject).strip()
    if subj_str.startswith("urn:"):
        return subj_str

    from rdflib.namespace import DC, DCTERMS, SKOS

    for pred in (DCTERMS.identifier, DC.identifier, SKOS.notation):
        for obj in graph.objects(subject, pred):
            val = str(obj).strip()
            if val.startswith("urn:"):
                return val

    # Fallback synthesis
    notation_val = None
    for pred in (SKOS.notation, DCTERMS.identifier, DC.identifier):
        for obj in graph.objects(subject, pred):
            val = str(obj).strip()
            if val and not val.startswith("http://") and not val.startswith("https://"):
                notation_val = val
                break
        if notation_val:
            break

    raw_id = (
        (notation_val or subj_str.split("/")[-1].split("#")[-1])
        .lower()
        .replace("_", "-")
        .replace(":", "-")
    )
    return f"urn:ddi:{default_agency}:{fallback_prefix}-{raw_id}:1.0.0"


def load_skos_vocabulary(
    file_path: str | Path,
    max_levels: int | None = None,
    reload: bool = False,
    vocabulary_name: str | None = None,
    rdf_format: str | None = None,
) -> dict[str, Any]:
    """Load any SKOS / XKOS vocabulary into the Concept table from an RDF file.

    Parameters:
    - file_path: Path to the RDF file (.ttl, .rdf, .xml, .jsonld, .nt, etc.).
    - max_levels: Optional depth limit (1 for top concepts, 2 for top + level 1, None for all).
    - reload: If True, clears existing concepts for this vocabulary before loading.
    - vocabulary_name: Name of vocabulary (if None, infers from scheme or file stem).
    - rdf_format: RDF format (if None, auto-detected from file extension).

    Returns summary dictionary.
    """
    import hashlib
    import json
    import os

    import rdflib
    from rdflib.namespace import DC, DCTERMS, RDF, RDFS, SKOS
    from rdflib.util import guess_format

    from fairwddi.models import Concept, ConceptScheme

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Vocabulary file not found: {path}")

    start_time = time.perf_counter()
    agency = os.getenv("DDI_AGENCY", "fr.sciencespo")

    # 1. Detect format and parse RDF graph
    fmt = rdf_format or guess_format(str(path)) or "turtle"
    graph = rdflib.Graph()
    graph.parse(path, format=fmt)

    # 2. Determine / infer vocabulary name if not supplied
    if not vocabulary_name:
        # Prefer concise name: file stem prefix, e.g. "ELSST" from "ELSST_R6.ttl"
        vocabulary_name = path.stem.split("_")[0].upper()

    vocab_slug = vocabulary_name.lower().replace(" ", "-")

    # Helper to extract multilingual properties with fallback
    def extract_multilingual(
        subject: rdflib.URIRef, predicates: list[rdflib.URIRef]
    ) -> list[dict[str, str]]:
        result: list[dict[str, str]] = []
        seen_pairs: set[tuple[str, str]] = set()
        for pred in predicates:
            for lit in graph.objects(subject, pred):
                if isinstance(lit, rdflib.Literal):
                    lang = str(lit.language or "und").strip()
                    val = str(lit).strip()
                    pair = (lang, val)
                    if val and pair not in seen_pairs:
                        seen_pairs.add(pair)
                        result.append({"lang": lang, "value": val})
        return result

    def extract_notation(subject: rdflib.URIRef) -> str | None:
        for lit in graph.objects(subject, SKOS.notation):
            if isinstance(lit, rdflib.Literal):
                val = str(lit).strip()
                if not val.startswith("urn:"):
                    return val
        for lit in graph.objects(subject, DCTERMS.identifier):
            if isinstance(lit, rdflib.Literal):
                val = str(lit).strip()
                if not val.startswith("urn:") and not val.startswith("http"):
                    return val
        return None

    # 3. Identify / create parent ConceptScheme(s) for the vocabulary
    scheme_nodes = list(graph.subjects(RDF.type, SKOS.ConceptScheme))
    schemes_by_uri: dict[str, ConceptScheme] = {}

    if scheme_nodes:
        for s_node in scheme_nodes:
            s_uri_str = str(s_node)
            s_urn = extract_urn(
                s_node, graph, fallback_prefix=f"cs-{vocab_slug}", default_agency=agency
            )
            s_labels = extract_multilingual(
                s_node, [SKOS.prefLabel, RDFS.label, DCTERMS.title, DC.title]
            )
            s_descriptions = extract_multilingual(
                s_node, [DCTERMS.description, RDFS.comment, SKOS.scopeNote, DC.description]
            )
            if not s_labels:
                s_labels = [{"lang": "und", "value": vocabulary_name}]

            s_obj, _ = ConceptScheme.objects.update_or_create(
                urn=s_urn,
                defaults={
                    "name": s_labels,
                    "description": s_descriptions,
                },
            )
            schemes_by_uri[s_uri_str] = s_obj
        default_scheme_obj = schemes_by_uri[str(scheme_nodes[0])]
    else:
        scheme_urn = f"urn:ddi:{agency}:cs-{vocab_slug}:1.0.0"
        scheme_labels = [{"lang": "und", "value": vocabulary_name}]
        scheme_descriptions = [
            {"lang": "und", "value": f"Controlled vocabulary imported from {path.name}"}
        ]
        default_scheme_obj, _ = ConceptScheme.objects.update_or_create(
            urn=scheme_urn,
            defaults={
                "name": scheme_labels,
                "description": scheme_descriptions,
            },
        )
        schemes_by_uri["default"] = default_scheme_obj

    # 4. Identify all concepts in the RDF graph
    all_concepts_in_graph = set(graph.subjects(RDF.type, SKOS.Concept))
    for s in graph.subjects(SKOS.prefLabel, None):
        if isinstance(s, rdflib.URIRef) and s not in scheme_nodes:
            all_concepts_in_graph.add(s)

    all_concept_uri_strs = [str(c) for c in all_concepts_in_graph]

    # 5. Check if already loaded by vocabulary name OR matching URIs
    status = check_vocabulary_loaded(vocabulary=vocabulary_name)
    existing_by_uri_count = (
        Concept.objects.filter(uri__in=all_concept_uri_strs[:50]).count()
        if all_concept_uri_strs
        else 0
    )
    is_already_present = status["loaded"] or (existing_by_uri_count > 0)

    if is_already_present and not reload:
        found_count = (
            status["total_concepts"] or Concept.objects.filter(uri__in=all_concept_uri_strs).count()
        )
        return {
            "status": "already_loaded",
            "message": (
                f"Vocabulary '{vocabulary_name}' (or concepts from {path.name}) is already "
                f"loaded in the database ({found_count} concepts found). "
                f"Use --reload / -r to overwrite."
            ),
            **status,
        }

    # 6. If reload or existing concepts with these URIs exist, clean them up
    if reload or is_already_present:
        from django.db.models import Q

        Concept.objects.filter(
            Q(vocabulary=vocabulary_name)
            | Q(uri__in=all_concept_uri_strs)
            | Q(scheme__in=list(schemes_by_uri.values()))
        ).delete()

    # 7. Identify Top Concepts (Level 1)
    top_concept_uris = set(graph.subjects(SKOS.topConceptOf, None)) | set(
        graph.objects(None, SKOS.hasTopConcept)
    )

    # Fallback: concepts that have no broader relation are root/top concepts
    if not top_concept_uris:
        for c in all_concepts_in_graph:
            if not list(graph.objects(c, SKOS.broader)):
                top_concept_uris.add(c)

    # Filter to only URIRefs in the graph
    top_concept_uris = {c for c in top_concept_uris if c in all_concepts_in_graph}

    # If flat vocabulary with no hierarchy, all concepts are level 1
    if not top_concept_uris and all_concepts_in_graph:
        top_concept_uris = set(all_concepts_in_graph)

    # 8. Build Level Tree supporting bidirectional broader/narrower navigation
    level_nodes: dict[int, list[tuple[rdflib.URIRef, rdflib.URIRef | None]]] = {}
    visited_uris: set[rdflib.URIRef] = set()

    # Level 1
    level_1 = [(c, None) for c in top_concept_uris]
    level_nodes[1] = level_1
    for c, _ in level_1:
        visited_uris.add(c)

    current_level = 1
    while True:
        if max_levels is not None and current_level >= max_levels:
            break

        next_level: list[tuple[rdflib.URIRef, rdflib.URIRef | None]] = []
        for parent_uri, _ in level_nodes[current_level]:
            # Forward navigation via skos:narrower
            for child_uri in graph.objects(parent_uri, SKOS.narrower):
                if isinstance(child_uri, rdflib.URIRef) and child_uri not in visited_uris:
                    next_level.append((child_uri, parent_uri))
                    visited_uris.add(child_uri)

            # Reverse navigation via skos:broader (if narrower was not explicitly asserted)
            for child_uri in graph.subjects(SKOS.broader, parent_uri):
                if isinstance(child_uri, rdflib.URIRef) and child_uri not in visited_uris:
                    next_level.append((child_uri, parent_uri))
                    visited_uris.add(child_uri)

        if not next_level:
            break

        current_level += 1
        level_nodes[current_level] = next_level

    # If all levels requested and some orphaned concepts exist, add them at bottom level
    if max_levels is None:
        orphans = all_concepts_in_graph - visited_uris
        if orphans:
            current_level += 1
            orphan_nodes = [(c, None) for c in orphans]
            level_nodes[current_level] = orphan_nodes
            for c, _ in orphan_nodes:
                visited_uris.add(c)

    # 9. Insert concepts level by level inside a database transaction
    created_concepts_by_uri: dict[str, Concept] = {}
    total_inserted = 0

    with transaction.atomic():
        for lvl in sorted(level_nodes.keys()):
            for c_uri, parent_uri in level_nodes[lvl]:
                uri_str = str(c_uri)
                labels = extract_multilingual(c_uri, [SKOS.prefLabel, RDFS.label])
                descriptions = extract_multilingual(
                    c_uri, [SKOS.scopeNote, SKOS.altLabel, DCTERMS.description, RDFS.comment]
                )
                definitions = extract_multilingual(
                    c_uri,
                    [
                        SKOS.definition,
                        rdflib.URIRef(
                            "http://rdf-vocabulary.ddialliance.org/xkos#additionalContentNote"
                        ),
                    ],
                )
                notation_val = extract_notation(c_uri)

                # Fallback if no label found
                if not labels:
                    labels = [{"lang": "und", "value": uri_str.split("/")[-1].split("#")[-1]}]

                parent_model = None
                if parent_uri is not None:
                    parent_model = created_concepts_by_uri.get(str(parent_uri))

                c_urn = extract_urn(
                    c_uri, graph, fallback_prefix=f"concept-{vocab_slug}", default_agency=agency
                )

                # Determine associated ConceptScheme
                concept_scheme_obj = default_scheme_obj
                for scheme_ref in graph.objects(c_uri, SKOS.inScheme):
                    if str(scheme_ref) in schemes_by_uri:
                        concept_scheme_obj = schemes_by_uri[str(scheme_ref)]
                        break
                if concept_scheme_obj == default_scheme_obj:
                    for scheme_ref in graph.objects(c_uri, SKOS.topConceptOf):
                        if str(scheme_ref) in schemes_by_uri:
                            concept_scheme_obj = schemes_by_uri[str(scheme_ref)]
                            break

                c_bytes = json.dumps(
                    {"urn": c_urn, "uri": uri_str, "label": labels, "notation": notation_val},
                    sort_keys=True,
                ).encode()
                c_hash = hashlib.sha256(c_bytes).hexdigest()

                concept_obj, _ = Concept.objects.update_or_create(
                    urn=c_urn,
                    defaults={
                        "scheme": concept_scheme_obj,
                        "uri": uri_str,
                        "vocabulary": vocabulary_name,
                        "notation": notation_val,
                        "label": labels,
                        "description": descriptions,
                        "definition": definitions,
                        "parent": parent_model,
                        "concept_type": "top_concept" if lvl == 1 else "concept",
                        "hashes": {"sha256": c_hash},
                    },
                )
                created_concepts_by_uri[uri_str] = concept_obj
                total_inserted += 1

    elapsed = time.perf_counter() - start_time

    return {
        "status": "success",
        "vocabulary": vocabulary_name,
        "format": fmt,
        "source_file": str(path),
        "total_concepts": total_inserted,
        "top_concepts": len(level_nodes.get(1, [])),
        "levels_loaded": len(level_nodes),
        "max_levels_limit": max_levels,
        "elapsed_seconds": round(elapsed, 2),
    }


# Backwards-compatible alias for ELSST
load_elsst_vocabulary = load_skos_vocabulary
