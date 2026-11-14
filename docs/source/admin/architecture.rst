System Architecture & Prerequisites
====================================

FAIRwDDI is architected as an asynchronous, schema-strict metadata platform designed for high referential integrity, deterministic deduplication, and low-latency multilingual search.

Hardware & Operating System Recommendations
-------------------------------------------

.. list-table::
   :widths: 25 35 40
   :header-rows: 1

   * - Component
     - Minimum Specification
     - Production Recommended
   * - **CPU**
     - 2 Cores (x86_64 or aarch64)
     - 4+ Cores (for parallel XML streaming)
   * - **RAM**
     - 4 GB
     - 8 GB+ (allows in-memory hash indexing)
   * - **Storage**
     - 20 GB SSD
     - NVMe SSD with WAL isolation
   * - **Operating System**
     - Linux (Debian 12+, Ubuntu 24.04+), macOS 14+
     - Linux (Debian / Ubuntu LTS)

Software Dependencies
---------------------

* **Python**: Version 3.12 or newer. Managed via `uv <https://astral.sh/uv>`_ or containerized.
* **PostgreSQL**: Version 17.0+ (required for native JSON_TABLE, ICU collation improvements, and JSONB enhancements).
* **Database Driver**: `psycopg v3 <https://www.psycopg.org/psycopg3/>`_ with binary extensions enabled.
* **C Libraries**: ``libxml2`` and ``libxslt`` (for streaming XML parsing with ``lxml``).

Database Architecture
---------------------

PostgreSQL 17 is the core storage engine. Several PostgreSQL-specific features are mandatory for production operation:

1. International Components for Unicode (ICU) Collations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Traditional OS-level locales (e.g., ``fr_FR.UTF-8`` or ``en_US.UTF-8``) depend on underlying C library glibc versions, which can lead to index corruption during operating system upgrades.

FAIRwDDI mandates PostgreSQL 17 ICU collations for all text and JSONB operations::

   CREATE COLLATION IF NOT EXISTS "und-x-icu" (
       provider = icu,
       locale = 'und'
   );

This guarantees byte-exact, deterministic string comparison and sorting across Linux, macOS, and container environments.

2. Generalized Inverted Indexes (GIN) on JSONB
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

All textual entities (e.g., ``label``, ``description``, ``question_text``) are stored as JSONB dictionaries mapping ISO 639-1 language codes to strings::

   {"fr": "Orientation politique", "en": "Political orientation"}

To ensure fast key-existence and JSONPath lookups, tables use GIN indexes with the ``jsonb_path_ops`` operator class::

   CREATE INDEX idx_rep_var_label_gin ON request_ddi_representedvariable USING gin (label jsonb_path_ops);
   CREATE INDEX idx_question_text_gin ON request_ddi_questionitem USING gin (question_text jsonb_path_ops);

3. Universal Referential Integrity & Cascades
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

All 30 DDI entities inherit from ``DDIIdentifiable`` and register their canonical URN in the central supertype master table ``request_ddi_urnregistry``.

* Foreign keys connecting child entities to ``request_ddi_urnregistry`` enforce ``ON DELETE CASCADE``.
* Polymorphic relationships (such as ``URNAlias``, ``SemanticRelationship``, and ``EventLog``) point to ``request_ddi_urnregistry(urn)``, ensuring no dangling pointer can exist in the system.
