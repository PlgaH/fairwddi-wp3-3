Project Deliverables & Research Reports
=========================================

The **FAIRwDDI Lifecycle** project (WP3 ST3) produced comprehensive technical deliverables, architectural specifications, and benchmark research for the Sciences Po Centre des Données Socio-Politiques (CDSP).

Core Deliverables
-----------------

1. Phase I Deliverable Report (Rapport d'audit technique)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Path**: ``deliverables/phase1_report.md``
* **Scope**: Complete technical audit of the current ReQuest platform, gap analysis against DDI standards, and validated standard-agnostic DDI database architecture.
* **Portal Link**: Accessible via the `FAIRwDDI Architecture Portal <../index.html#deliverables/phase1_report>`_.

2. Target Database Model Specification
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Path**: ``deliverables/research/database.md``
* **Scope**: Formal specification of the 30-model PostgreSQL 17 schema, ER diagrams, ``DDIIdentifiable`` base mixin, and zero-data-loss Django migration path from legacy ReQuest.

3. Automated Normalization & Ingestion Pipeline
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Path**: ``deliverables/research/normalization.md``
* **Scope**: 4-phase normalization cascade, 2-stage ingestion pipeline, format adapters, and multilingual dictionary merging.

Specialized Technical Research Papers
-------------------------------------

* **Multi-Algorithm Content Fingerprinting & Deduplication** (``deliverables/research/hashing_algorithms.md``): Cryptographic benchmarking of SHA-256 and BLAKE3, deterministic 16-character URN synthesis, and set-theoretic matching.
* **PostgreSQL 17 JSONB & Multilingual Architecture** (``deliverables/research/postgres_django_json.md``): In-depth examination of JSONB faceted string arrays, JSONPath/JSON_TABLE queries, Django ORM key transforms (KT), and GIN indexing.
* **Variable Cascade Standards Alignment** (``deliverables/research/variable_cascade_gsim_cdi_vs_ddi_lifecycle.md``): Cross-standard comparison of the variable cascade across GSIM, DDI-CDI, and DDI-Lifecycle 3.3.
* **DDI-Lifecycle 3.3 to DDI 4.0 Streaming Crosswalk** (``deliverables/research/ddi_lifecycle_33_to_40_streaming_crosswalk.md``): Analysis of fragment streaming, namespace unification, substitution group mapping, and instruction wrapping.

Interactive Exploration
-----------------------

All deliverables, SVG architecture diagrams, and the interactive 28-model database explorer can be viewed online at the `FAIRwDDI Architecture Portal <../index.html>`_.
