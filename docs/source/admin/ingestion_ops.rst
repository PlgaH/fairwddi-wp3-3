Ingestion & Pipeline Operations
================================

FAIRwDDI implements a **plan-first, non-destructive ingestion model**. Incoming survey metadata is never directly loaded into the production database without first passing through preflight validation, 4-phase comparison, and execution plan approval.

The 2-Stage Ingestion Lifecycle
-------------------------------

.. code-block:: text

   ┌───────────────────────────────────────────────────────────────┐
   │ STAGE 1: IN-MEMORY PARSING & EXTRACTION                       │
   │  1. Format Detection (DDI-C 2.5/2.6, DDI-L 3.2/3.3, DDI 4.0)  │
   │  2. Low-Memory Streaming (lxml iterparse via dartfx-ddi)      │
   │  3. String Normalization (NFKC, French punctuation rules)     │
   │  4. Canonical JSON & Multi-Algorithm Hashing (SHA-256/BLAKE3) │
   └───────────────────────────────┬───────────────────────────────┘
                                   │
                                   ▼
   ┌───────────────────────────────────────────────────────────────┐
   │ STAGE 2: DATABASE COMPARISON & EXECUTION PLAN                 │
   │  1. Same-URN Collision Check:                                 │
   │     - REUSE: Identical URN & Hash (Archivist review)          │
   │     - QUARANTINE: Identical URN, drifted content hash         │
   │  2. Strict Two-Tier Resource Matching:                        │
   │     - TIER 1 (generated/instantiated): LINK_EXISTING (W3C     │
   │       prov:wasDerivedFrom + wording_variant enrichment)       │
   │     - TIER 2 (unharmonized imported): GENERATE_HARMONIZED     │
   │       (mints new generated resource uniting both)             │
   │     - CREATE: Standalone new imported resource                │
   └───────────────────────────────┬───────────────────────────────┘
                                   │
                                   ▼
   ┌───────────────────────────────────────────────────────────────┐
   │ TRANSACTIONAL BATCH LOADER                                    │
   │  - Master UrnRegistry upsert with origin='imported'           │
   │  - Child entity persistence (never absorbed / overwritten)    │
   │  - W3C prov:wasDerivedFrom lineage & wording_variant logging   │
   │  - IngestBatch receipt (created, generated, linked, reused)   │
   │  - Deletion protection & cascade-safe rollback                │
   └───────────────────────────────────────────────────────────────┘

The Non-Destructive Ingestion & Two-Tier Matching Architecture
--------------------------------------------------------------

FAIRwDDI enforces non-destructive ingestion where incoming metadata is always preserved:

1. **Origin Classification**:
   Every resource in ``UrnRegistry`` carries an ``origin`` tag:
   * ``imported``: Ingested from external survey files or vocabularies.
   * ``generated``: Synthesized automatically by harmonizer algorithms or agent workflows.
   * ``instantiated``: Created directly by an archivist via CLI, API, or administrative ORM.

2. **Same-URN Collision Gate**:
   * If an incoming URN already exists in ``UrnRegistry`` with an identical content hash, it triggers ``action="reuse"`` (``ING-URN-REUSE-001``). Cross-file reuse requires explicit archivist confirmation.
   * If the existing URN has a different content hash, a content drift collision is flagged and routed to ``action="quarantine"`` (``ING-DRIFT-001``).

3. **Strict Two-Tier Matching for Harmonizable Resources**:
   * **Tier 1 (Harmonized / Bank Targets)**: Evaluated first against all ``generated`` and ``instantiated`` resources. If a match meets the threshold, ``action="link_existing"`` is planned. The incoming resource is saved as ``origin='imported'``, linked to the target via ``prov:wasDerivedFrom``, and any alternate spellings are preserved on the target as ``wording_variant`` entries in ``extended_attributes``.
   * **Tier 2 (Unharmonized Imported Candidates)**: Evaluated only if Tier 1 yields no match. When two ``imported`` resources match across surveys, ``action="generate_harmonized"`` is planned. Both source records remain intact as ``origin='imported'``, and a brand-new ``origin='generated'`` resource is minted, linking both sources via ``prov:wasDerivedFrom``.

4. **Referential Deletion Protection**:
   Resources referenced by other entities (foreign keys, junction tables, groups, or semantic relationships) cannot be deleted. Batch rollbacks (``undo_ingestion``) safely preserve generated resources if subsequent survey waves derive from them.

Reviewing Ingestion Plans
-------------------------

Before applying changes, generate an Ingestion Execution Plan YAML::

   fairwddi ingest plan survey_wave_2.xml --report-out wave2_plan.yaml

Example plan snippet:

.. code-block:: yaml

   plan_id: "plan-20261112-wave2"
   source_file: "survey_wave_2.xml"
   detected_format: "DDI-Lifecycle-3.3"
   summary:
     total_resources: 142
     actions:
       create: 18
       link: 122
       re_version: 2
       quarantine: 0
   proposals:
     - entity: "InstanceVariable"
       name: "AGE_R"
       action: "LINK"
       target_urn: "urn:ddi:fr.cdsp:RV_AGE:1.0"
       confidence: 1.0
     - entity: "QuestionItem"
       name: "Q_INCOME_2026"
       action: "CREATE"
       proposed_urn: "urn:ddi:fr.cdsp:QI_INCOME_2026:1.0"

Executing Batch Transactions
----------------------------

Apply the validated plan in a single atomic database transaction::

   fairwddi ingest execute wave2_plan.yaml

Every execution produces an immutable **IngestBatch receipt** storing:
* Batch ID and timestamp.
* Source file name and SHA-256 checksum.
* Operator identity and execution options.
* Full list of created, linked, and quarantined entity URNs.

Handling Quarantine Records
---------------------------

If metadata drift is detected, inspect the quarantine list::

   fairwddi ingest status <batch_id> --show-quarantine

Archivists can resolve quarantined items via the CLI:

.. code-block:: bash

   # Option A: Accept incoming changes as a new version
   fairwddi ingest resolve-quarantine <quarantine_id> --action re-version --new-version "1.1"

   # Option B: Reject incoming changes and retain existing database record
   fairwddi ingest resolve-quarantine <quarantine_id> --action reject

Rolling Back a Batch
--------------------

If an error is discovered post-ingestion, roll back the entire batch safely using its receipt ID::

   fairwddi ingest undo <batch_id> --confirm

The rollback process will:
1. Delete all newly created child records and their corresponding ``UrnRegistry`` entries.
2. Sever linkages established during the batch.
3. Record a rollback event in ``EventLog``.
