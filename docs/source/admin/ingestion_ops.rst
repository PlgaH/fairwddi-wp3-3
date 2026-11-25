Import & Harmonization Operations
=================================

FAIRwDDI cleanly decouples **deterministic metadata import** (``fairwddi.importer``) from post-import **group curation** (``fairwddi.groups``), **read-only three-layer comparison** (``fairwddi.compare``), and **policy-driven harmonization** (``fairwddi.harmonize``).

Pure Import Lifecycle (``fairwddi import``)
-------------------------------------------

Incoming metadata files are always persisted faithfully with ``origin='imported'`` without synthesizing ``generated`` entities or cross-survey ``prov:wasDerivedFrom`` links:

1. **Preflight & Optional DDI-C Upgrade**: Validates profile compliance and converts DDI-Codebook 2.5/2.6 into DDI-Lifecycle 4.0 with intra-file deduplication and selectable ``--category-scheme-mode`` (``single`` vs. ``per_codelist``).
2. **Same-URN Collision Gate**:
   * Identical URN + identical hash triggers ``action="reuse"`` (``IMP-URN-REUSE-001``) flagged for review.
   * Identical URN + differing hash triggers ``action="quarantine"`` (``IMP-DRIFT-001``) and records payload in ``MetadataQuarantine``.
3. **Preserved Domain Attributes**: Preserves ``Category.is_missing``, ``CodeItem.is_missing``, ``Category.scheme``, and ``CodeList.scheme``.
4. **Atomic Rollback (``undo_import``)**: Verifies no external resources reference any URN in the batch before deleting in leaf-to-root order.

Post-Import Comparison & Harmonization
--------------------------------------

1. **Group Curation**: Use ``fairwddi group`` to organize longitudinal or thematic study collections by canonical URN and unique ``slug``.
2. **Read-Only Comparison**: ``fairwddi compare run --source ... --target ...`` evaluates syntactic, semantic, and conceptual correspondences alongside independent ``CodeListQualification`` diagnostics (isolating ``is_missing`` codes and flagging scale cardinality or dimension mismatches).
3. **Policy-Gated Harmonization**: ``fairwddi harmonize plan <comparison.yaml> [--approve-high]`` converts candidates into a review-gated ``HarmonizationPlan``, downgrades divergent response scales to ``link_semantic``, and executes approved operations atomically via ``fairwddi harmonize execute``.
