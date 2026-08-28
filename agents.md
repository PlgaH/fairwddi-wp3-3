# FAIRwDDI Lifecycle — Agent Rules

> **Project:** FAIRwDDI WP3 ST3 — Implementation of DDI Architecture for ReQuest
> **Organization:** Centre des Données Socio-Politiques (CDSP), Sciences Po / CNRS
> **Duration:** July 20 – December 18, 2026 (25 days)

## Purpose

Transform the CDSP **ReQuest** question-bank database from a pseudo-DDI model (DDI-Codebook 2.5 with custom Django abstractions) to a **standard-agnostic DDI architecture** aligned with **DDI 4.0 (COGS model)** and **DDI-CDI (Cross-Domain Integration)**, with full compatibility for **DDI-Lifecycle 3.3** and multi-standard ingestion. This upgrade ensures FAIR interoperability with European social-science archives (CESSDA), adds native multilingual support (`xml:lang`), and implements the DDI variable cascade (`ConceptualVariable → RepresentedVariable → InstanceVariable`).

> **⚠️ Lightweight Profile — Do NOT import monolithic specification bloat.** We implement the core DDI entities needed for the ReQuest question bank (listed in the glossary below). The full DDI specifications cover hundreds of classes; our core model is standard-agnostic, lightweight, and focused. When in doubt, leave it out.

---

## Background & Key References

| Resource                            | Location                                                                                                                                           | Description                                                                                                                                                             |
| :---------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **ReQuest platform overview**       | [request_overview.md](docs/request_overview.md)                                                                                                    | Technical architecture, data model, ETL pipeline, and search mechanics of the current `request-ddi` codebase.                                                           |
| **Upgrade requirements & roadmap**  | [request_upgrade.md](docs/request_upgrade.md)                                                                                                      | Full DDI migration specification: schema evolution, URN identification, Pydantic schemas, harmonization cascade, and Elasticsearch multilingual indexing.               |
| **Statement of work**               | [sow.md](docs/sow.md)                                                                                                                              | Official SOW with deliverables, risk matrix, and phase timeline.                                                                                                        |
| **DDI-Lifecycle 3.3 specification** | [PDF](docs/ddi-lifecycle-technical-guide-readthedocs-io-en-latest.pdf) / [Online](https://ddi-lifecycle-technical-guide.readthedocs.io/en/latest/) | Technical guide for DDI-Lifecycle 3.3.                                                                                                                                  |
| **ReQuest source code**             | `../fairwddi-request-ddi`                                                                                                                          | The `request-ddi` Django app / Python package repository.                                                                                                               |
| **DDI Model (COGS)**                | `../ddialliance_ddimodel`                                                                                                                          | Model-based approach to DDI 4 using Colectica COGS.                                                                                                                     |

---

## DDI Terminology Glossary

Agents **must** use canonical DDI terminology (aligned with DDI 4 / DDI-CDI / DDI-L). The table below maps between the current `request-ddi` model names and the target DDI model names.

| Current `request-ddi` Name         | Target DDI Model Name       | Layer          | Description                                                                                                          |
| :--------------------------------- | :-------------------------- | :------------- | :------------------------------------------------------------------------------------------------------------------- |
| `ConceptualVariable`               | **ConceptualVariable**      | Concept        | Abstract measurement concept (e.g., "Left-Right Political Placement"). Already aligned.                              |
| `RepresentedVariable`              | **RepresentedVariable**     | Representation | Question wording + response code list. Already aligned.                                                              |
| _(new)_                            | **QuestionItem**            | Representation | Standalone reusable question text with interviewer instructions. Extracted from `RepresentedVariable.question_text`. |
| `Category`                         | **Category**                | Representation | Response text label. Already aligned; will gain multilingual JSONB.                                                  |
| _(new)_                            | **CodeList** / **CodeItem** | Representation | Named sets of response codes; decouples numerical codes from category labels.                                        |
| _(new)_                            | **VariableGroup**           | Organization   | Thematic grouping of variables within a study (e.g., "Demographics", "Political Attitudes"). **New entity required.** |
| `Survey`                           | **StudyUnit**               | Dataset        | A specific survey wave or dataset. **Rename required.**                                                              |
| `BindingSurveyRepresentedVariable` | **InstanceVariable**        | Dataset        | Physical realization of a variable in a specific study column. **Rename required.**                                  |

---

## Technology Stack & Conventions

### Core Stack

- **Language:** Python 3.12+ (managed via `uv`)
- **Framework:** Django ≥ 6.0, `django-ninja` 1.3.0 (API layer)
- **CLI:** Typer & Rich (`fairwddi = "fairwddi.cli:app"`)
- **DDI Integration:** `dartfx-ddi` (Data Artifex DDI Toolkit)
- **Database:** PostgreSQL 17 with ICU collations (via `psycopg` v3 driver)
- **Search:** Elasticsearch 9.4.x, `django-elasticsearch-dsl` 9.0.0
- **Validation & Serialization:** Pydantic v2 (shared across import, API, and ES indexing)
- **XML Parsing (target):** `lxml.etree.iterparse` (streaming; replaces BeautifulSoup)
- **Task Queue:** `django-tasks-db` ≥ 0.12.0 (background ETL)
- **Testing:** Pytest, `pytest-django`, `pytest-cov`; SQLite in-memory for unit tests
- **Build:** `hatchling`, `hatch-vcs`; Vite for frontend JS bundles

### Coding Conventions

- Use **type hints** throughout Python code.
- Pydantic v2 schemas go in `request_ddi/core/schemas.py`.
- Django model renames use `migrations.RenameModel` (zero-data-loss).
- Text fields that support multilingual content use PostgreSQL `JSONB` with ISO 639-1 language keys (e.g., `{"fr": "...", "en": "..."}`).
- All DDI entities carry persistent URN identification: `urn:ddi:{agency}:{identifier}:{version}`.
- Content deduplication uses **SHA-256 content fingerprints** (`content_hash` field).
- String normalization follows `request_ddi/utils/normalize_string.py` patterns: Unicode NFKC, French punctuation rules, whitespace collapsing.
- Always include `tests/conftest.py` with `settings.configure()` and `django.setup()` for isolated pytest testing of Django/Ninja components.
- Configure `[tool.ruff]` with explicit `include` patterns for `src/**/*.py` and `tests/**/*.py` to prevent documentation snippet formatting conflicts.
- When adding direct git URL dependencies in `pyproject.toml`, configure `[tool.hatch.metadata]` `allow-direct-references = true`.
- Typer CLI applications should include a `@app.callback()` root function for eager `--version` handling alongside subcommands (`version`, `info`).

---

## Project Phases

### Phase I: Audit and Modeling (July 20 – Sept 30, 2026)

_Goal: Analyze existing database, define DDI-L profile, and design target architecture._

| Task                                                  | Description                                                                                                                                     |
| :---------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------- |
| **Lancement et Immersion**                            | Conduct kickoff meeting, establish development environments, review existing database schema and sample DDI-L files.                            |
| **Audit of Current Model & DDI-L Profile Definition** | Identify gaps between the current PostgreSQL schema and DDI-L standards; formalize a minimal DDI-L profile for ReQuest.                         |
| **New Schema Design**                                 | Architect a new PostgreSQL schema treating "question" as a reusable object; implement "variable cascade" and multilingual support (JSON/JSONB). |
| **Audit Reporting & Validation**                      | Draft final audit report and recommendations; present to CDSP/partners for validation.                                                          |

**Deliverable:** Technical audit report (`Rapport d'audit`), formal DDI-L profile, validated SQL target schema.

---

### Phase II: Development of Python Library (Aug 17 – Oct 31, 2026)

_Goal: Create the interface for the new database model and manage DDI-L metadata exchange._

| Task                                  | Description                                                                                                                                                             |
| :------------------------------------ | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Project Initialization**            | Configure project infrastructure (GitHub, development agents); define base data structures (Pydantic/Django); integrate DDI-L resources via Data Artifex (DDI-Toolkit). |
| **Import/Export Implementation**      | Develop mapping functions for metadata; ensure strict adherence to DDI-L schema standards.                                                                              |
| **Advanced Feature Development**      | Implement logic for multilingual metadata and "variable cascade" management.                                                                                            |
| **Quality Assurance & Documentation** | Execute unit tests (Pytest) and finalize technical documentation (Sphinx/README).                                                                                       |

**Deliverable:** Python library (`Bibliothèque Python reQuest`) — source code, unit tests, DDI-L import/export scripts, documentation.

---

### Phase III: Finalization and Support (Oct 19 – Dec 18, 2026)

_Goal: Integrate the solution into CDSP infrastructure and close the project._

| Task                              | Description                                                                                     |
| :-------------------------------- | :---------------------------------------------------------------------------------------------- |
| **Delivery and Coordination**     | Deliver and present the DDI-L export script; coordinate migration and integration strategy.     |
| **Technical Integration Support** | Provide guidance on schema refactoring and tool adaptation; assist with pre-production testing. |
| **Project Closure**               | Finalize administrative/technical documentation and hold the wrap-up meeting.                   |

**Deliverable:** Closure dossier (`Dossier de clôture`) — activity summary, technical audit, feedback, strategic roadmap.

---

## Key Architectural Decisions

1. **Variable Cascade:** Three-tier entity hierarchy — `ConceptualVariable → RepresentedVariable → InstanceVariable` — enables cross-survey harmonization where identical questions are reused and conceptual variants are clustered.
2. **URN-First Technical Normalization:** Deterministic URN matching is the primary deduplication mechanism; ICU collation-based heuristic matching serves as fallback for legacy DDI-Codebook files or auto-generated/random URNs.
3. **Decoupled Normalization & Harmonization:** Technical metadata normalization (string cleaning, SHA-256 fingerprinting, URN generation, format adapters) is handled by the automated ingestion pipeline ([`deliverables/normalization.md`](file:///Users/pascal/git-plgah/fairwddi-lifecycle/deliverables/normalization.md)), while semantic harmonization is handled at the Concept Layer via controlled vocabulary/thesaurus anchoring.
4. **Content Fingerprinting:** SHA-256 hashes detect metadata drift (same URN, different content) and trigger quarantine for archivist review.
5. **Multilingual JSONB:** All text fields support multiple languages via JSONB with sorted-key canonical hashing for deterministic fingerprints.
6. **Streaming XML Parsing:** `lxml.etree.iterparse` replaces BeautifulSoup for DDI-Lifecycle XML to minimize memory footprint on large files.
7. **Pydantic v2 Unified Schemas:** Single schema layer shared across file import validation, `django-ninja` API serialization, and Elasticsearch bulk indexing.
8. **Controlled Vocabulary & Thesaurus Anchoring:** The `Concept` entity is vocabulary-agnostic (`uri`, `vocabulary`, `notation`, `parent_id`, `concept_type`) and supports arbitrary controlled vocabularies and classifications (e.g. CESSDA ELSST, CESSDA Topics, DDI-CV, or custom schemes). Sciences Po can use ELSST or other selected thesauri to establish a controlled, multilingual concept hierarchy for clustering `RepresentedVariable` entities across surveys.

---

## Risks & Mitigations

| Risk                               | Impact                            | Mitigation                                                 |
| :--------------------------------- | :-------------------------------- | :--------------------------------------------------------- |
| No source DDI-L profiles available | Divergence from CDSP expectations | Early dialogue with partners; use standard DDI-L examples.                                                |
| Semantic harmonization complexity  | Inconsistent concept mapping      | Anchor `ConceptualVariable` to controlled vocabularies; human-in-the-loop QA for ambiguous variable clustering. |
| Internal support availability      | Delays or schema misalignment     | Designate a dedicated technical point of contact at CDSP.                                                 |
| Over-engineering                   | Increased structural complexity   | Prioritize a lightweight, rigorous schema initially.                                                      |
| ReQuest environment conflicts      | Tech/library incompatibilities    | Early, close collaboration with existing developers.                                                      |
