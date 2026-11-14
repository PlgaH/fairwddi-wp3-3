Developer Guide
===============

This guide provides in-depth technical documentation for developers building applications, extensions, or integration bridges on top of the **FAIRwDDI Lifecycle** architecture.

Architectural Principles
------------------------

1. **Standard-Agnostic Core Model**: The database architecture decouples internal representations from format-specific nuances of DDI-Codebook, DDI-Lifecycle, and DDI-CDI, ensuring zero vendor lock-in.
2. **Canonical Variable Cascade**: Separation of abstract measurement concepts, standardized question wordings/code lists, and physical survey dataset columns.
3. **Universal Referential Integrity**: All identifiable entities register in ``UrnRegistry``, establishing clean polymorphic foreign keys and guaranteed cascade deletions.
4. **Deterministic Fingerprinting**: Content hashes (SHA-256 and BLAKE3) detect metadata drift across survey iterations and power deduplication.
5. **Native Multilingualism**: First-class JSONB dictionaries for all descriptive strings, normalized with Unicode NFKC and French typography.

Table of Contents
-----------------

.. toctree::
   :maxdepth: 2

   variable_cascade
   data_model
   urn_registry
   multilingual_jsonb
   fingerprinting
   ingest_engine
   api_service
   dartfx_integration
