FAIRwDDI Lifecycle Documentation
================================

.. image:: https://img.shields.io/badge/DDI-4.0%20%7C%20CDI%20%7C%20Lifecycle%203.3-blue
   :alt: DDI Standards

.. image:: https://img.shields.io/badge/Python-3.12%2B-blue?logo=python
   :alt: Python Version

.. image:: https://img.shields.io/badge/Database-PostgreSQL%2017%20%2B%20ICU-336791?logo=postgresql
   :alt: PostgreSQL 17

.. image:: https://img.shields.io/badge/Sciences%20Po-CDSP%20%2F%20CNRS-red
   :alt: CDSP Sciences Po

Welcome to the technical documentation for **FAIRwDDI Lifecycle**, the standard-agnostic DDI architecture and metadata exchange platform developed for the Sciences Po Centre des Données Socio-Politiques (CDSP) **ReQuest** question bank.

This project transforms the legacy question-bank model into a **standard-agnostic DDI architecture** aligned with **DDI 4.0 (COGS model)**, **DDI-CDI 1.0 (Cross-Domain Integration)**, and **DDI-Lifecycle 3.3**, ensuring full FAIR interoperability with European social science archives (CESSDA), native multilingual metadata storage (JSONB), deterministic content fingerprinting, and the canonical DDI variable cascade.

.. note::
   This documentation is written for **system administrators**, **backend developers**, and **open-source contributors**. If you are looking for executive summaries, interactive deliverable viewers, and the visual database explorer, visit the `FAIRwDDI Architecture Portal <../index.html>`_.

Core Capabilities
-----------------

* **Canonical Variable Cascade**: Implements the three-tier harmonization hierarchy:
  ``ConceptualVariable`` (concept layer) → ``RepresentedVariable`` (representation layer) → ``InstanceVariable`` (dataset layer), decoupling survey wording from dataset physical realizations.
* **Supertype Master Registry**: Universal ``UrnRegistry`` master table guaranteeing universal referential integrity across all 30 entities, :math:`O(1)` type resolution, and clean polymorphic foreign key cascades.
* **Multilingual JSONB Architecture**: Native support for multilingual labels, descriptions, and interviewer instructions stored as ISO 639-1 dictionary payloads (e.g., ``{"fr": "...", "en": "..."}``) indexed with PostgreSQL GIN and normalized with Unicode NFKC and French typographical rules.
* **Multi-Algorithm Content Fingerprinting**: Cryptographic fingerprinting combining SHA-256 and BLAKE3 over canonical JSON representations to detect metadata drift, generate deterministic 16-character URN hashes, and quarantine conflicting updates.
* **Pluggable Ingestion Pipeline**: 2-stage ingestion engine featuring low-memory streaming XML parsing (``lxml.etree.iterparse``), automatic format detection (DDI-Codebook 2.5/2.6, DDI-Lifecycle 3.2/3.3, DDI 4.0), and 4-phase comparison planning (Create, Link, Re-version, Quarantine).
* **Controlled Vocabulary & SKOS Anchoring**: Vocabulary-agnostic concept hierarchy supporting CESSDA ELSST, DDI-CV, and custom taxonomies.
* **Django Ninja REST API & Interactive Explorer**: Modern async-ready REST API with auto-generated OpenAPI 3.0 documentation and an interactive client-side 28-model architecture explorer.
* **Data Artifex Integration**: Deep integration with the Data Artifex DDI Toolkit (``dartfx-ddi``) for DDI-Lifecycle streaming and crosswalks.

Architecture at a Glance
------------------------

The FAIRwDDI architecture organizes metadata into 5 logical layers:

.. list-table::
   :widths: 20 25 55
   :header-rows: 1

   * - Layer
     - Primary Entities
     - Role & Responsibility
   * - **Concept Layer**
     - ``Concept``, ``ConceptualVariable``, ``ConceptScheme``
     - Abstract measurement intent; anchors variables to controlled vocabularies (e.g., ELSST).
   * - **Representation Layer**
     - ``RepresentedVariable``, ``QuestionItem``, ``CodeList``, ``Category``
     - Reusable questions, interviewer instructions, response codes, and category labels.
   * - **Dataset Layer**
     - ``StudyUnit``, ``InstanceVariable``, ``DataFile``
     - Physical realization of questions and variables in specific survey waves and data files.
   * - **Organization Layer**
     - ``VariableGroup``, ``Organization``, ``Individual``
     - Thematic grouping of variables, research agencies, data creators, and contributors.
   * - **Infrastructure Layer**
     - ``UrnRegistry``, ``IngestBatch``, ``IngestionPlan``, ``EventLog``
     - Referential integrity, batch receipts, audit logs, and deduplication records.

Quick Start
-----------

Installation
~~~~~~~~~~~~

Using `uv <https://github.com/astral-sh/uv>`_ (recommended)::

   # Clone repository
   git clone https://github.com/DataArtifex/fairwddi-lifecycle.git
   cd fairwddi-lifecycle

   # Install core dependencies and development tools
   uv sync

   # Run tests to verify installation
   uv run pytest

CLI Administration
~~~~~~~~~~~~~~~~~~

The ``fairwddi`` CLI provides complete operational tooling::

   # Check database connectivity and schema status
   uv run fairwddi db status

   # Apply migrations or initialize schema
   uv run fairwddi db init

   # Preflight check an incoming DDI-Lifecycle or DDI-Codebook XML file
   uv run fairwddi preflight check sample_study.xml

   # Generate a 4-phase comparison plan before importing
   uv run fairwddi ingest plan sample_study.xml --report-out plan.yaml

   # Execute batch ingestion
   uv run fairwddi ingest execute plan.yaml

   # Start the REST API server with live Swagger documentation
   uv run fairwddi serve --port 8000

Python API
~~~~~~~~~~

Query the database and traverse the variable cascade programmatically::

   import django
   django.setup()

   from fairwddi.models import ConceptualVariable, RepresentedVariable, InstanceVariable

   # Fetch conceptual variable with its multilingual label
   concept_var = ConceptualVariable.objects.get(name="POLITICAL_ORIENTATION")
   print(concept_var.label.get("fr"), concept_var.label.get("en"))

   # Traverse downward to all survey-specific instance realizations
   for rep_var in concept_var.represented_variables.all():
       print(f"Question: {rep_var.question_item.question_text.get('fr')}")
       for inst_var in rep_var.instance_variables.all():
           print(f"  → Survey: {inst_var.study_unit.name}, Column: {inst_var.name}")

Table of Contents
-----------------

.. toctree::
   :maxdepth: 2
   :caption: Documentation

   admin/index
   developer/index
   contributor/index
   api/index
   reference/index

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
