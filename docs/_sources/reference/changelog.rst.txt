Changelog & Project Roadmap
============================

Project Timeline Overview
-------------------------

* **Phase I: Audit and Modeling** (July 20 – September 30, 2026)
  * Deliverable: Technical audit report, formal DDI profile, validated SQL target schema.
* **Phase II: Python Library Development** (August 17 – October 31, 2026)
  * Deliverable: Python library (``fairwddi``), Pydantic v2 schemas, streaming ETL pipeline, REST API.
* **Phase III: Finalization and Support** (October 19 – December 18, 2026)
  * Deliverable: CDSP infrastructure integration, DDI-Lifecycle export script, closure dossier.

Release History
---------------

Version 0.1.0-RC1 (2026-11-12)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Initial Sphinx Documentation**: Initialized comprehensive documentation for administrators, developers, and contributors deployed under ``/docs``.
* **Standard-Agnostic Schema**: Landed 30 PostgreSQL 17 models with `UrnRegistry` supertype master table.
* **Streaming XML Ingestion**: Implemented low-memory XML fragment streaming using `lxml.etree.iterparse` and `dartfx-ddi`.
* **Multi-Algorithm Hashing**: Implemented SHA-256 and BLAKE3 canonical JSON fingerprinting.
* **Multilingual JSONB**: Implemented ISO 639-1 multilingual text dictionaries with Unicode NFKC normalization.
* **Django Ninja REST API**: Launched async OpenAPI 3.0 endpoints and the interactive 28-model architecture explorer.
* **Automated Harmonization**: Added `fairwddi harmonize` CLI command suite for cross-survey variable clustering.
