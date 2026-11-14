Content Fingerprinting & Deduplication
========================================

FAIRwDDI implements **cryptographic content fingerprinting** to ensure metadata integrity, detect silent metadata drift between survey waves, and prevent duplicate entity creation.

The Multi-Algorithm Approach
----------------------------

Rather than relying on a single hash algorithm, FAIRwDDI stores multi-algorithm fingerprints in the ``hashes`` JSONB column of every versionable entity:

.. code-block:: json

   {
     "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
     "blake3": "af1349b9f5f9a1a6a0404dea36dcc9499bcb25c9adc112b7cc9a93cae41f3262"
   }

* **SHA-256**: Industry-standard cryptographic hash ensuring universal archive compatibility and verifiability.
* **BLAKE3**: Highly optimized, SIMD-parallelized cryptographic hash providing 5x to 10x throughput for large XML batch ingestions.

Canonical JSON Serialization
----------------------------

Hashing arbitrary Python dictionaries or XML snippets directly leads to false discrepancies caused by key order or formatting differences.

To guarantee deterministic fingerprints, FAIRwDDI converts every entity payload into **Canonical JSON**:
1. Dictionary keys are sorted recursively in alphabetical order.
2. Multilingual strings are normalized (Unicode NFKC, trimmed whitespace).
3. Null or default empty values are serialized uniformly.
4. Whitespace separators are strictly compact (``","`` and ``":"``).

.. code-block:: python

   import json
   import hashlib
   import blake3

   def compute_content_hashes(data: dict) -> dict[str, str]:
       # Canonical JSON serialization
       canonical_bytes = json.dumps(
           data,
           sort_keys=True,
           separators=(",", ":"),
           ensure_ascii=False
       ).encode("utf-8")

       sha256_hex = hashlib.sha256(canonical_bytes).hexdigest()
       blake3_hex = blake3.blake3(canonical_bytes).hexdigest()

       return {
           "sha256": sha256_hex,
           "blake3": blake3_hex,
       }

Simple vs Compound Hashing
--------------------------

1. Simple Hashing (Leaf Entities)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Applied to leaf resources containing only intrinsic attributes (e.g., ``QuestionItem``, ``Category``):
* Payload consists solely of the entity's normalized properties (e.g., ``question_text``, ``instruction_text``).

2. Compound Hashing (Aggregate Entities)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Applied to complex aggregate resources (e.g., ``CodeList``, ``RepresentedVariable``):
* Payload combines intrinsic properties **plus the sorted hashes of its member items**:

  * A ``CodeList``'s hash incorporates the ordered list of its ``CodeItem`` hashes.
  * If a single category label or code changes, the compound hash updates automatically.

Deterministic 16-Character URN Hashes
--------------------------------------

When ingesting legacy DDI files without persistent URNs, FAIRwDDI synthesizes deterministic URNs using the first 16 characters of the canonical SHA-256 hash::

   urn:ddi:fr.cdsp:QI_a8f9c2d1b7e403fa:1.0

This ensures that ingesting the exact same legacy question text across multiple runs always resolves to the exact same URN without generating random duplicates.

Detecting Metadata Drift
------------------------

During batch ingestion, if an incoming XML element carries an existing URN:

.. list-table::
   :widths: 30 30 40
   :header-rows: 1

   * - URN Match
     - Content Hash Match
     - System Action
   * - Matches existing
     - Matches existing
     - **Safe Reuse**: Link without database write.
   * - Matches existing
     - **Differs** from existing
     - **Metadata Drift**: Quarantine for archivist review.
   * - Does not match
     - Matches existing
     - **Alias Detected**: Register as ``URNAlias``.
   * - Does not match
     - Does not match
     - **New Resource**: Create canonical record.
