# Project Activities & Progress Report

> **Project:** FAIRwDDI WP3 ST3 — Implementation of DDI-Lifecycle for ReQuest  
> **Organization:** Centre des Données Socio-Politiques (CDSP), Sciences Po / CNRS  
> **Document Purpose:** Status tracking report organizing project work across Ongoing, Planned, Barriers, and Completed activities.

---

## 🔄 Ongoing Activities

- [ ] **Data Model Iteration:** Review and produce Data Model v0.2 incorporating CDSP feedback and lightweight question bank profile.
- [ ] **Database Scaffolding:** Generate Python (Django / SQLAlchemy) and SQL DDL code to initialize the target PostgreSQL database.
- [ ] **Ingestion Utilities:** Implement lightweight DDI 4.0 import utility pipeline.

---

## 📅 Planned Activities

- [ ] **Corpus Expansion:** Collect additional DDI-Lifecycle collections (European Question Bank, UK Data Service, Sikt Norway).
- [ ] **Team Checkpoint:** Schedule and run progress checkpoint meeting with the CDSP project team.

---

## ⚠️ Barriers & Dependencies

- [ ] **External System Access:** Awaiting account credentials and access permissions for the [European Question Bank (EQB)](https://eqb.cessda.eu/) Colectica server.

---

## ✅ Completed Activities

- **Early R&D & Schema Design:**
  - Early R&D and draft of DDI-L4 PostgreSQL data model.
  - Deep research around metadata normalization challenges, methodologies, and hashing algorithms (canonical JSON serialization, ICU collation rules).
  - Designed a generic approach supporting DDI-L, DDI-C, DDI-CDI, and other specifications using lifecycle adapters, with built-in versioning support (e.g., `4.0-rc1`, `4.0`, `4.1`, etc.).
  - Formalized URN categorization and resolution strategies: Curated, Canonical, Random, and Alias URNs.
- **Corpus & Sample DDI-L Collection:**
  *(Note: Harvested DDI corpus files are maintained locally under `ddi/` and excluded from the public git repository due to file size constraints [multi-GB] and upstream redistribution/licensing terms)*
  - Collected DDI-L metadata packages from [MIDUS (Midlife in the United States)](https://midus.colectica.org/).
  - Collected DDI-L metadata from [Ireland Central Statistics Office (CSO)](https://metadataddi.cso.ie/):
    - 5 projects, 23 series, 67 studies, 210 instruments, 6,044 questions.
  - Collected DDI-L from the [CLOSER](https://discovery.closer.ac.uk/) repository:
    - 12 longitudinal projects, 2+ GB of XML, 50M+ resources.
  - Ingested CLOSER DDI-L into BaseX XML database for high-volume querying, exploratory analysis, and exports.
  - Drafted XQueries for automated metadata content reporting.
- **Tooling & Library Development:**
  - Added Python Pydantic serializer to Colectica COGS.
  - Integrated DDI-Lifecycle into Data Artifex DDI-Toolkit (`dartfx-ddi`):
    - Added Pydantic models generated from COGS.
    - Implemented high-performance streaming parser (`lxml.etree.iterparse`).
  - Initialized Python project environment and tooling (`fairwddi` with `uv`, `hatchling`, `pytest`, `ruff`, `pyrefly`).
  - **[MAJOR]** Implemented DDI 3.3 to 4.0 parser.
  - Added related DDI conversion and inspection commands to the Data Artifex CLI.
- **Stakeholder & Expert Engagement:**
  - Conducted technical consultation meeting with Jon Johnson (CLOSER / DDI Alliance) to review question-bank architectures, cross-study harmonization, and practical operational lessons.
