The Import, Comparison & Harmonization Engines
===============================================

FAIRwDDI strictly isolates deterministic file loading from cross-survey harmonization:

1. **``fairwddi.importer``**: Format detection (``detector``), constant-memory streaming (``streaming``), profile QA & DDI-C upgrade (``preflight``), zero-write ``ImportPlan`` planning, and atomic core loading (``loader``) with zero harmonization dependencies.
2. **``fairwddi.groups``**: Context curation via ``Group`` (URN + unique ``slug``) and unified set resolution (``group:``, ``batch:``, ``study:``, ``bank:``, ``urn:``).
3. **``fairwddi.compare``**: Strictly read-only two-set comparison across syntactic, semantic, and conceptual layers with independent ``CodeListQualification`` analysis.
4. **``fairwddi.harmonize``**: Policy-driven ``HarmonizationPlan`` generation (supporting ``--approve-high`` and scale-divergence guardrails), atomic ``execute_harmonization``, and ``EventLog`` rollback.
