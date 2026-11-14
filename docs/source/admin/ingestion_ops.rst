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
   │  Phase 1: Deterministic URN Matching                          │
   │  Phase 2: Multi-Algorithm Content Fingerprint Matching        │
   │  Phase 3: ICU Collation-Based Heuristic Match (Fallback)      │
   │  Phase 4: Action Determination:                               │
   │           - CREATE: Brand new entity                          │
   │           - LINK: Reusing existing representation             │
   │           - RE-VERSION: Semantic update under new version URN │
   │           - QUARANTINE: Identical URN, drifted content        │
   └───────────────────────────────┬───────────────────────────────┘
                                   │
                                   ▼
   ┌───────────────────────────────────────────────────────────────┐
   │ TRANSACTIONAL BATCH LOADER                                    │
   │  - Master UrnRegistry upsert                                  │
   │  - Child entity persistence                                   │
   │  - IngestBatch receipt & audit log generation                 │
   └───────────────────────────────────────────────────────────────┘

The 4-Phase Comparison Cascade
------------------------------

When an incoming XML entity is compared against the database:

1. **Phase 1 — Deterministic URN Match**:
   If an entity with the exact URN (e.g., ``urn:ddi:fr.cdsp:Q_AGE:1.0``) already exists:
   * If its content fingerprint matches the incoming payload, the entity is verified as **identical** and linked.
   * If its content fingerprint differs, a **metadata collision** is detected! Rather than silently overwriting, the entity is routed to **Quarantine** for archivist review.

2. **Phase 2 — Multi-Algorithm Fingerprint Match**:
   If the URN does not match, the pipeline checks whether an entity with an identical canonical content hash exists under another URN (e.g., when a survey generates random identifiers for a standard question):
   * If an identical hash is found, the incoming URN is recorded as an **alias** (``URNAlias``) pointing to the existing canonical entity, preventing duplicate records.

3. **Phase 3 — ICU Collation Heuristic Match**:
   For legacy DDI-Codebook files lacking persistent URNs, the engine applies normalized string comparisons using PostgreSQL's ICU collation (``und-x-icu``). Candidate matches exceeding the configured similarity threshold (e.g., 90%) are proposed for linking in the execution plan.

4. **Phase 4 — Execution Action Determination**:
   * **CREATE**: Persist as a new canonical entity in ``UrnRegistry`` and its respective table.
   * **LINK**: Connect the incoming ``InstanceVariable`` to an existing ``RepresentedVariable``.
   * **RE-VERSION**: Increment version number (e.g., ``1.0`` → ``2.0``) and record the historical link in ``URNAlias``.
   * **QUARANTINE**: Hold the record in isolation until an archivist inspects the discrepancy.

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
