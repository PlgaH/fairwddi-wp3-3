# FAIRwDDI Lifecycle

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![DDI-Lifecycle 3.3](https://img.shields.io/badge/DDI--Lifecycle-3.3-orange.svg)](https://ddialliance.org/Specification/DDI-Lifecycle/3.3/)
[![Framework](https://img.shields.io/badge/framework-Django%20%7C%20Django%20Ninja-green.svg)](https://django-ninja.rest-framework.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CDSP / Sciences Po](https://img.shields.io/badge/Organization-CDSP%20%2F%20CNRS%20%2F%20Sciences%20Po-8b0000.svg)](https://cdsp.sciences-po.fr/)

**FAIRwDDI WP3 ST3** — Implementation of **DDI-Lifecycle 3.3** for the CDSP [ReQuest](https://request.sciencespo.fr/) Question Bank.

---

## 📌 Context & Objectives

The **Centre de Données Socio-Politiques (CDSP, UAR 828 CNRS / Sciences Po)** preserves, documents, and disseminates high-quality research data for the social sciences. As part of this mission, CDSP operates **[ReQuest](https://request.sciencespo.fr/)**, an open platform exploring over 65,000 questions and variables across longitudinal and cross-sectional survey collections (including the ELIPSS panel and CEVIPOF French electoral surveys).

As part of the **FAIRwDDI** research infrastructure initiative (Work Package 3, Subtask 3), this project modernizes the ReQuest database and ingestion pipelines from a pseudo-DDI architecture (DDI-Codebook 2.5 with custom Django abstractions) into a fully compliant **DDI-Lifecycle (DDI-L) 3.3** standard.

### Key Project Objectives

1. **FAIR Interoperability:** Align ReQuest metadata models with European social science data infrastructures (CESSDA, Dataverse, Colectica) and international DDI standards.
2. **Native Multilingual Support:** Implement multi-language metadata handling (`xml:lang`) across all question wording, response categories, and variable concepts using PostgreSQL `JSONB`.
3. **Harmonization & Variable Cascade:** Establish the 3-tier DDI-Lifecycle variable cascade (`ConceptualVariable` → `RepresentedVariable` → `InstanceVariable`) anchored to the CESSDA [ELSST](https://elsst.cessda.eu/) multilingual thesaurus.
4. **Lightweight & Maintainable Profile:** Deliver a focused, robust DDI-L profile specifically tailored for question banks without importing unneeded specification bloat.
5. **Streaming Ingestion & Content Deduplication:** Implement high-performance streaming XML parsing (`lxml.etree.iterparse`), canonical URN identification, and SHA-256 fingerprinting for drift detection and deduplication.

> [!NOTE]
> **DDI Document Availability & Licensing Notice:**  
> The raw DDI XML corpus documents and reference metadata harvested from external repositories (e.g., CLOSER, Ireland CSO, MIDUS, EQB) are not tracked in this public repository due to their large file size (multi-gigabyte payloads with tens of millions of resources) and, in some cases, upstream licensing and redistribution constraints. Testing and development pipelines utilize synthetic fixtures and localized mock fragments.

---

## 🏛️ Architectural Overview

### 1. The DDI-Lifecycle 3.3 Variable Cascade

The upgrade introduces a clear separation between conceptual definitions, question representations, and physical survey dataset bindings:

```
[ Concept Layer ]
  └── ConceptualVariable (anchored to CESSDA ELSST Thesaurus)
        │
[ Representation Layer ]
  ├── QuestionItem (reusable question text & interviewer instructions)
  ├── CodeList / CodeItem (structured numerical codes & category values)
  └── RepresentedVariable (synthesizes QuestionItem + CodeList)
        │
[ Dataset / Physical Layer ]
  └── InstanceVariable (realization of variable in a specific survey column / wave)
```

### 2. Terminology & Model Mapping

| Legacy `request-ddi` Model | DDI-Lifecycle 3.3 Model | Layer | Description |
| :--- | :--- | :--- | :--- |
| `ConceptualVariable` | **ConceptualVariable** | Concept | Abstract measurement concept (anchored to ELSST vocabulary) |
| `RepresentedVariable` | **RepresentedVariable** | Representation | Question representation + code list association |
| _(implicit / inline)_ | **QuestionItem** | Representation | Standalone reusable question text & interviewer instructions |
| `Category` | **Category** | Representation | Canonical response text label with multilingual JSONB |
| _(new entity)_ | **CodeList** / **CodeItem** | Representation | Decoupled numerical codes and category value bindings |
| _(new entity)_ | **VariableGroup** | Organization | Thematic grouping of variables within a survey study |
| `Survey` | **StudyUnit** | Dataset | Specific survey wave, collection, or study |
| `BindingSurveyRepresentedVariable` | **InstanceVariable** | Dataset | Physical realization of a variable in a specific survey dataset column |

### 3. Core Technical Decisions

- **Deterministic URN Identification:** Canonical URN generation (`urn:ddi:{agency}:{identifier}:{version}`) provides stable identifiers across all entities.
- **SHA-256 Content Fingerprinting:** Canonical JSON hashing of normalized text detects metadata drift (same URN, differing content) and routes ambiguous records to archivist quarantine.
- **Multilingual `JSONB` Storage:** PostgreSQL `JSONB` fields store ISO 639-1 language dictionaries (e.g., `{"fr": "...", "en": "..."}`) with sorted-key canonical serialization.
- **Streaming XML Parsing:** `lxml.etree.iterparse` streams large DDI-Lifecycle XML instances with minimal memory overhead, replacing DOM-based parsing.
- **Unified Pydantic v2 Schemas:** Shared validation models between ingestion pipelines, `django-ninja` REST APIs, and multilingual Elasticsearch indexing.

---

## 🗓️ Project Roadmap & Deliverables

The work is organized across three phases under the FAIRwDDI WP3 ST3 Statement of Work:

```mermaid
gantt
    title FAIRwDDI WP3 ST3 Roadmap
    dateFormat  YYYY-MM-DD
    section Phase I: Audit & Modeling
    Immersion & Audit          :p1_1, 2026-07-20, 2026-08-31
    Target Schema & Profile    :p1_2, 2026-08-15, 2026-09-30
    section Phase II: Python Library
    Pydantic & Base Library    :p2_1, 2026-08-17, 2026-09-20
    Import/Export & Cascade    :p2_2, 2026-09-15, 2026-10-31
    section Phase III: Finalization
    CDSP Integration & Support :p3_1, 2026-10-19, 2026-12-05
    Project Closure & Roadmap  :p3_2, 2026-12-01, 2026-12-18
```

| Phase | Milestone | Expected Deliverable |
| :--- | :--- | :--- |
| **Phase I**<br>*(Jul 20 – Sep 30, 2026)* | **Audit and Modeling** | • Technical Audit Report (`Rapport d'audit`)<br>• Formal DDI-Lifecycle 3.3 ReQuest Profile<br>• Validated PostgreSQL target schema & Django migration plan |
| **Phase II**<br>*(Aug 17 – Oct 31, 2026)* | **Python Library (`fairwddi`)** | • Source library with DDI-L import/export pipelines (`dartfx-ddi`)<br>• Unified Pydantic v2 schemas and cascade managers<br>• Automated Pytest test suite and API documentation |
| **Phase III**<br>*(Oct 19 – Dec 18, 2026)* | **Integration and Support** | • Deployment and integration into CDSP ReQuest infrastructure<br>• Pre-production migration scripts and verification<br>• Final closure dossier (`Dossier de clôture`) and strategic roadmap |

---

## 🛠️ Technology Stack

| Category | Technology / Tool | Description |
| :--- | :--- | :--- |
| **Language** | [Python 3.12+](https://www.python.org/) | Core language runtime |
| **Package Management** | [uv](https://github.com/astral-sh/uv) | Fast package resolution and environment management |
| **Build System** | [hatchling](https://hatch.pypa.io/) / `hatch-vcs` | PEP 517 build backend with dynamic versioning |
| **Framework** | [Django](https://www.djangoproject.com/) ≥ 5.0 / [Django Ninja](https://django-ninja.rest-framework.com/) | Web framework & high-performance OpenAPI REST interface |
| **DDI Toolkit** | [dartfx-ddi](https://github.com/DataArtifex/ddi-toolkit) | Data Artifex DDI Lifecycle toolkit |
| **Database** | [PostgreSQL 17](https://www.postgresql.org/) via [`psycopg3`](https://www.psycopg.org/psycopg3/) | Relational database with JSONB and ICU multilingual collations |
| **Search Engine** | [Elasticsearch 9.x](https://www.elastic.co/) | Multilingual full-text indexing and faceted search |
| **Validation** | [Pydantic v2](https://docs.pydantic.dev/) | High-speed schema validation and serialization |
| **XML Processing** | [lxml](https://lxml.de/) (`iterparse`) | Streaming XML parsing for large DDI instances |
| **CLI & Formatting** | [Typer](https://typer.tiangolo.com/) & [Rich](https://rich.readthedocs.io/) | Interactive terminal command-line interface |
| **Quality & Tests** | [pytest](https://pytest.org/), [Ruff](https://astral.sh/ruff), [Pyrefly](https://github.com/facebook/pyrefly) | Testing, linting, formatting, and static type checking |

---

## 🚀 Getting Started

### 1. Environment Setup

Clone the repository and initialize the virtual environment using `uv`:

```bash
# Clone the repository
git clone https://github.com/PlgaH/fairwddi-wp3-3.git
cd fairwddi-wp3-3

# Create virtual environment and install dependencies
uv venv --python 3.12
uv sync --all-extras
```

### 2. Command Line Interface (CLI)

The `fairwddi` CLI provides tools for inspecting versions, running DDI validations, and orchestrating imports/exports:

```bash
# Display CLI help
uv run fairwddi --help

# Check package version
uv run fairwddi version

# Display system and environment information
uv run fairwddi info
```

### 3. Running Tests

```bash
# Run unit and integration tests
uv run pytest

# Run tests with test coverage reporting
uv run pytest --cov=fairwddi
```

### 4. Code Quality & Formatting

```bash
# Linting checks
uv run ruff check .

# Code formatting check
uv run ruff format --check .

# Static type checking
uv run pyrefly check
```

---

## 📚 Key References & Documentation

- **Project Activities & Progress Log:** [docs/activities.md](docs/activities.md) — Live log of completed tasks, ongoing work, planned milestones, and pending items.
- **ReQuest Platform Overview:** [docs/request_overview.md](docs/request_overview.md) — Architecture, ETL mechanics, and search design of the current `request-ddi` codebase.
- **Migration & Upgrade Specification:** [docs/request_upgrade.md](docs/request_upgrade.md) — Comprehensive technical roadmap, Pydantic schemas, and Elasticsearch indexing.
- **Statement of Work (SOW):** [docs/sow.md](docs/sow.md) — Task breakdown, deliverables matrix, and risk mitigation plan.
- **Architecture Deliverables:**
  - Database target model: [deliverables/database.md](deliverables/database.md)
  - Metadata normalization & deduplication: [deliverables/normalization.md](deliverables/normalization.md)
  - Hashing algorithms & drift quarantine: [deliverables/hashing_algorithms.md](deliverables/hashing_algorithms.md)
  - Terminology glossary: [deliverables/glossary.md](deliverables/glossary.md)
- **Official Specification:** [DDI-Lifecycle 3.3 Technical Guide](https://ddi-lifecycle-technical-guide.readthedocs.io/en/latest/)

---

## 📄 License & Attribution

This project is licensed under the [MIT License](LICENSE).

Developed for **Centre des Données Socio-Politiques (CDSP)** — Sciences Po / CNRS as part of the **FAIRwDDI** research infrastructure initiative.
