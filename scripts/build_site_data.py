#!/usr/bin/env python3
"""
FAIRwDDI Lifecycle - Site Data Generator & Build Orchestrator
Builds a static JSON/JS manifest containing all documents, metadata, headings, diagrams,
and search indices for the GitHub Pages static website, and ensures bundle files are in sync.
"""

import json
import os
import re
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent

DOCUMENTS_CONFIG = [
    # Deliverables & Research
    {
        "id": "deliverables/phase1_report",
        "file": "deliverables/phase1_report.md",
        "title": "Phase I Deliverable Report (Rapport d'audit technique et spécifications)",
        "shortTitle": "Phase I Deliverable Report",
        "category": "Deliverables",
        "badge": "v1.0.0-RC1",
        "icon": "file-text",
        "featured": True,
        "description": "Comprehensive technical audit of the current ReQuest platform and validated standard-agnostic DDI database architecture."
    },
    {
        "id": "research/summary",
        "file": "deliverables/research/summary.md",
        "title": "Executive Summary — Standard-Agnostic DDI Architecture",
        "shortTitle": "Executive Summary",
        "category": "Research Reports",
        "badge": "Overview",
        "icon": "compass",
        "featured": True,
        "description": "Master executive summary capturing all architectural decisions, design patterns, database schemas, and ingestion workflows."
    },
    {
        "id": "research/database",
        "file": "deliverables/research/database.md",
        "title": "Target Database Model & PostgreSQL 17 Schema Specification",
        "shortTitle": "Database Model Specification",
        "category": "Research Reports",
        "badge": "28 Models",
        "icon": "database",
        "featured": True,
        "description": "Complete 28-model standard-agnostic PostgreSQL 17 schema, ER diagrams, DDIIdentifiable mixin, staging nodes, and migration path."
    },
    {
        "id": "research/database_diagram",
        "file": "deliverables/research/database_diagram.md",
        "title": "Database ER Diagram & Architecture Schemes",
        "shortTitle": "Database ER Diagram",
        "category": "Research Reports",
        "badge": "ERD & Schemas",
        "icon": "git-merge",
        "featured": False,
        "description": "Visual Entity-Relationship diagram, layer breakdown, scheme hierarchies, and schema relationships."
    },
    {
        "id": "research/normalization",
        "file": "deliverables/research/normalization.md",
        "title": "Automated Normalization & Ingestion Pipeline Specification",
        "shortTitle": "Normalization & Ingestion",
        "category": "Research Reports",
        "badge": "4-Phase Cascade",
        "icon": "sliders",
        "featured": True,
        "description": "4-phase normalization cascade, 2-stage ingestion pipeline, pluggable format adapters, and multilingual dictionary merging."
    },
    {
        "id": "research/hashing_algorithms",
        "file": "deliverables/research/hashing_algorithms.md",
        "title": "Multi-Algorithm Content Fingerprinting & Deduplication",
        "shortTitle": "Content Fingerprinting & Hashing",
        "category": "Research Reports",
        "badge": "SHA-256 / BLAKE3",
        "icon": "shield",
        "featured": True,
        "description": "Simple vs Compound hashing, deterministic 16-char URN hashes, set-theoretic matching, and BLAKE3 benchmarks."
    },
    {
        "id": "research/postgres_django_json",
        "file": "deliverables/research/postgres_django_json.md",
        "title": "PostgreSQL 17 JSONB & Multilingual Architecture",
        "shortTitle": "PostgreSQL JSONB & Django",
        "category": "Research Reports",
        "badge": "JSONB / ICU",
        "icon": "code",
        "featured": False,
        "description": "Deep-dive into JSONB faceted string arrays, JSONPath/JSON_TABLE queries, Django ORM key transforms (KT), and GIN indexing."
    },
    {
        "id": "research/variable_cascade",
        "file": "deliverables/research/variable_cascade_gsim_cdi_vs_ddi_lifecycle.md",
        "title": "Variable Cascade Comparison (GSIM vs DDI-CDI vs DDI-Lifecycle 3.3)",
        "shortTitle": "Variable Cascade Comparison",
        "category": "Research Reports",
        "badge": "Standards Alignment",
        "icon": "layers",
        "featured": False,
        "description": "Cross-standard comparison of the variable cascade across GSIM, DDI-CDI, and DDI-Lifecycle 3.3."
    },
    {
        "id": "research/variable_question_relationships",
        "file": "deliverables/research/variable_question_relationships.md",
        "title": "Variable & Question Relationships in DDI-Lifecycle and ReQuest",
        "shortTitle": "Variable & Question Relationships",
        "category": "Research Reports",
        "badge": "6 Relationship Paths",
        "icon": "help-circle",
        "featured": False,
        "description": "Architectural analysis of the 6 canonical relationship paths connecting variables, questions, instruments, and studies."
    },
    {
        "id": "research/cli_user_guide",
        "file": "deliverables/research/cli_user_guide.md",
        "title": "fairwddi CLI User Guide & Administration Manual",
        "shortTitle": "CLI User Guide",
        "category": "Research Reports",
        "badge": "CLI & Python API",
        "icon": "terminal",
        "featured": True,
        "description": "Comprehensive manual for the fairwddi CLI tool: database setup, vocabulary seeding, staging inspection, and ingestion."
    },
    {
        "id": "research/glossary",
        "file": "deliverables/research/glossary.md",
        "title": "Canonical DDI Terminology & Glossary Reference",
        "shortTitle": "Canonical DDI Glossary",
        "category": "Research Reports",
        "badge": "Domain Glossary",
        "icon": "book-open",
        "featured": False,
        "description": "Authoritative reference mapping DDI-L entities, URN classifications, hashing terminology, and staging concepts."
    },
    # Documentation & Background
    {
        "id": "docs/request_overview",
        "file": "docs/request_overview.md",
        "title": "ReQuest Platform Overview & Architecture",
        "shortTitle": "ReQuest Platform Overview",
        "category": "Documentation",
        "badge": "Current Platform",
        "icon": "info",
        "featured": False,
        "description": "Technical architecture, data model, ETL pipeline, and search mechanics of the legacy request-ddi codebase."
    },
    {
        "id": "docs/request_upgrade",
        "file": "docs/request_upgrade.md",
        "title": "ReQuest Upgrade Roadmap & Specifications",
        "shortTitle": "ReQuest Upgrade Roadmap",
        "category": "Documentation",
        "badge": "Migration Roadmap",
        "icon": "trending-up",
        "featured": False,
        "description": "Full DDI migration specification: schema evolution, URN identification, Pydantic schemas, and search indexing."
    },
    {
        "id": "docs/sow",
        "file": "docs/sow.md",
        "title": "Statement of Work (SOW) — WP3 ST3",
        "shortTitle": "Statement of Work",
        "category": "Documentation",
        "badge": "WP3 ST3",
        "icon": "briefcase",
        "featured": False,
        "description": "Official Statement of Work with deliverables, risk matrix, milestone definitions, and phase timelines."
    },
    {
        "id": "docs/activities",
        "file": "docs/activities.md",
        "title": "Project Activity Log & Task Tracking",
        "shortTitle": "Project Activity Log",
        "category": "Documentation",
        "badge": "Task Logs",
        "icon": "calendar",
        "featured": False,
        "description": "Detailed log of completed activities, meetings, schema iterations, and deliverable submissions."
    },
    {
        "id": "docs/meeting_notes",
        "file": "docs/20260909_meeting.md",
        "title": "Kickoff & Architecture Meeting Presentation Notes",
        "shortTitle": "Kickoff Presentation Notes",
        "category": "Documentation",
        "badge": "Sep 9, 2026",
        "icon": "presentation",
        "featured": False,
        "description": "Presentation notes, architectural discussion points, and slide deck outline from the September 2026 meeting."
    },
    {
        "id": "docs/readme",
        "file": "README.md",
        "title": "FAIRwDDI Lifecycle Repository README",
        "shortTitle": "Repository README",
        "category": "Documentation",
        "badge": "Project Core",
        "icon": "github",
        "featured": False,
        "description": "Overview of the FAIRwDDI Lifecycle repository, installation, quick start, and development guidelines."
    },
]

DIAGRAMS_CONFIG = [
    {
        "id": "cascade_diagram",
        "file": "docs/assets/diagrams/cascade_diagram.svg",
        "title": "Three-Tier Variable Cascade",
        "category": "Architecture",
        "description": "ConceptualVariable → RepresentedVariable → InstanceVariable mapping with CESSDA ELSST thesaurus anchoring and question text decoupling."
    },
    {
        "id": "database_architecture",
        "file": "docs/assets/diagrams/database_architecture.svg",
        "title": "Five-Layer Database Architecture",
        "category": "Database",
        "description": "Modular 5-layer schema organization: Concept Layer, Representation Layer, Dataset Layer, Organization Layer, and Staging & Infrastructure Layer."
    },
    {
        "id": "database_er_diagram",
        "file": "docs/assets/diagrams/database_er_diagram.svg",
        "title": "Database Entity-Relationship Model",
        "category": "Database",
        "description": "Complete relational layout of all 28 core tables with foreign keys, polymorphic URN registry relations, and shortcut lookup tables."
    },
    {
        "id": "ingestion_pipeline",
        "file": "docs/assets/diagrams/ingestion_pipeline.svg",
        "title": "Multi-Standard Ingestion & Staging Pipeline",
        "category": "Ingestion",
        "description": "Two-stage decoupled ingestion architecture: Stage 1 Fast Raw File & Resource Staging → Stage 2 Asynchronous Normalization Worker."
    },
    {
        "id": "hashing_strategy",
        "file": "docs/assets/diagrams/hashing_strategy.svg",
        "title": "Multi-Algorithm Content Fingerprinting",
        "category": "Hashing",
        "description": "Two-tier hashing (Tier 1 Simple Text vs Tier 2 Compound URN), Preferred Algorithm pattern, and set-theoretic unordered hashing."
    },
    {
        "id": "skos_elsst",
        "file": "docs/assets/diagrams/skos_elsst.svg",
        "title": "SKOS / CESSDA ELSST Concept Anchoring",
        "category": "Semantic",
        "description": "Anchoring of ConceptualVariable entities to external controlled vocabularies and multilingual thesauri (ELSST, DDI-CV)."
    },
    {
        "id": "toolchain_cogs_ddi",
        "file": "docs/assets/diagrams/toolchain_cogs_ddi.svg",
        "title": "COGS Model & DDI Toolchain Integration",
        "category": "Standards",
        "description": "DDI 4.0 COGS model pipeline and compatibility with DDI-Lifecycle 3.3, DDI-CDI, and Dartfx-DDI toolkits."
    },
    {
        "id": "roadmap_timeline",
        "file": "docs/assets/diagrams/roadmap_timeline.svg",
        "title": "Project Roadmap & Milestone Timeline",
        "category": "Management",
        "description": "Phase I (Audit & Modeling), Phase II (Python Library Development), and Phase III (CDSP Integration & Support) milestones."
    }
]

def extract_headings_and_stats(markdown_text: str):
    lines = markdown_text.splitlines()
    headings = []
    word_count = len(re.findall(r'\w+', markdown_text))
    read_time_minutes = max(1, round(word_count / 200))
    
    in_code_block = False
    for line in lines:
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
            
        heading_match = re.match(r'^(#{1,4})\s+(.+)$', line)
        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2).strip()
            clean_text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
            clean_text = re.sub(r'[`*_]', '', clean_text)
            slug = re.sub(r'[^\w\- ]', '', clean_text.lower()).strip().replace(' ', '-')
            headings.append({
                "level": level,
                "text": clean_text,
                "rawText": text,
                "slug": slug
            })
            
    return headings, word_count, read_time_minutes

def build_site_data():
    print(f"Building FAIRwDDI Lifecycle Site Data from {WORKSPACE_ROOT}...")
    
    # Ensure site bundle scripts are run
    try:
        from generate_site_bundle import generate_bundle
        generate_bundle()
    except Exception as e:
        print(f"Note on generate_bundle: {e}")

    try:
        from generate_site_assets import generate_assets
        generate_assets()
    except Exception as e:
        print(f"Note on generate_assets: {e}")

    docs_output = []
    search_index = []
    
    for item in DOCUMENTS_CONFIG:
        file_path = WORKSPACE_ROOT / item["file"]
        if not file_path.exists():
            print(f"⚠️ Warning: File not found: {file_path}")
            continue
            
        content = file_path.read_text(encoding="utf-8")
        headings, word_count, read_time = extract_headings_and_stats(content)
        
        doc_entry = {
            "id": item["id"],
            "file": item["file"],
            "title": item["title"],
            "shortTitle": item.get("shortTitle", item["title"]),
            "category": item["category"],
            "badge": item.get("badge", ""),
            "icon": item.get("icon", "file-text"),
            "featured": item.get("featured", False),
            "description": item.get("description", ""),
            "wordCount": word_count,
            "readTimeMinutes": read_time,
            "headings": headings,
            "content": content
        }
        docs_output.append(doc_entry)
        
        chunks = re.split(r'\n(?=#{1,3}\s+)', content)
        for chunk_idx, chunk in enumerate(chunks):
            chunk_lines = chunk.strip().splitlines()
            if not chunk_lines:
                continue
            first_line = chunk_lines[0]
            section_title = item["title"]
            section_slug = ""
            if first_line.startswith('#'):
                section_title = re.sub(r'^#+\s+', '', first_line).strip()
                section_title_clean = re.sub(r'[`*_]', '', section_title)
                section_slug = re.sub(r'[^\w\- ]', '', section_title_clean.lower()).strip().replace(' ', '-')
            
            chunk_text = " ".join(chunk_lines)
            plain_text = re.sub(r'```[\s\S]*?```', ' ', chunk_text)
            plain_text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', plain_text)
            plain_text = re.sub(r'[#*`_>|]', ' ', plain_text)
            plain_text = re.sub(r'\s+', ' ', plain_text).strip()
            
            if len(plain_text) > 30:
                search_index.append({
                    "docId": item["id"],
                    "docTitle": item["title"],
                    "category": item["category"],
                    "sectionTitle": section_title,
                    "sectionSlug": section_slug,
                    "preview": plain_text[:280] + ("..." if len(plain_text) > 280 else ""),
                    "text": plain_text[:1200]
                })

    diagrams_output = []
    for item in DIAGRAMS_CONFIG:
        file_path = WORKSPACE_ROOT / item["file"]
        svg_content = ""
        if file_path.exists():
            svg_content = file_path.read_text(encoding="utf-8")
        else:
            print(f"⚠️ Warning: Diagram SVG not found: {file_path}")
            
        diagrams_output.append({
            "id": item["id"],
            "file": item["file"],
            "title": item["title"],
            "category": item["category"],
            "description": item["description"],
            "svg": svg_content
        })

    site_data = {
        "metadata": {
            "projectName": "FAIRwDDI Lifecycle",
            "projectSubTitle": "Standard-Agnostic DDI Architecture (DDI 4.0 / DDI-CDI / DDI-L 3.3) for the ReQuest Question Bank",
            "workPackage": "FAIRwDDI WP3 ST3",
            "organization": "Centre des Données Socio-Politiques (CDSP), Sciences Po / CNRS",
            "version": "1.0.0-RC1",
            "generatedAt": "2026-09-29T18:00:00Z",
            "stats": {
                "modelsCount": 28,
                "deliverablesCount": len([d for d in docs_output if d["category"] in ("Deliverables", "Research Reports")]),
                "documentationCount": len([d for d in docs_output if d["category"] == "Documentation"]),
                "diagramsCount": len(diagrams_output),
                "totalWords": sum(d["wordCount"] for d in docs_output)
            }
        },
        "documents": docs_output,
        "diagrams": diagrams_output,
        "searchIndex": search_index
    }
    
    out_dir = WORKSPACE_ROOT / "site_assets"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    json_path = out_dir / "site_data.json"
    js_path = out_dir / "site_data.js"
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(site_data, f, indent=2, ensure_ascii=False)
        
    with open(js_path, "w", encoding="utf-8") as f:
        f.write("/* Auto-generated FAIRwDDI Lifecycle Site Data Manifest */\n")
        f.write("window.FAIRWDDI_DATA = ")
        json.dump(site_data, f, indent=2, ensure_ascii=False)
        f.write(";\n")
        
    print(f"✅ Generated {json_path} ({json_path.stat().st_size:,} bytes)")
    print(f"✅ Generated {js_path} ({js_path.stat().st_size:,} bytes)")
    print(f"Indexed {len(docs_output)} documents, {len(diagrams_output)} diagrams, and {len(search_index)} search chunks.")

if __name__ == "__main__":
    build_site_data()
