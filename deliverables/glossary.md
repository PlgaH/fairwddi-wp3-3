# Glossary & Core Concepts — DDI-Lifecycle 3.3 Architecture

> **Project:** FAIRwDDI WP3 ST3 — Implementation of DDI-Lifecycle for ReQuest  
> **Status:** Reference Deliverable  
> **Target Audience:** Developers, Data Engineers, Archivists, AI Agents  

---

## 1. DDI-Lifecycle 3.3 Domain Model Concepts

| Concept / Entity | Layer | Definition | ReQuest Upgrade Context |
| :--- | :--- | :--- | :--- |
| **ConceptualVariable** | Concept | An abstract, survey-agnostic measurement concept (e.g., *"Left-Right Political Placement"* or *"Trust in Institutions"*). | Clusters multiple `RepresentedVariable` instances across survey waves and archives, regardless of minor wording or code changes. |
| **RepresentedVariable** | Representation | The combination of a specific question wording (`QuestionItem`) and a set of response choices (`CodeList`). | Decoupled from physical datasets; reusable across multiple survey waves that ask the exact same question with the same response options. |
| **QuestionItem** | Representation | The standalone, reusable text of a question, including interviewer instructions and pre/post text. | Extracted from `RepresentedVariable.question_text` into a dedicated table to allow question text reuse across variables. |
| **Category** | Representation | A single text label representing a response option (e.g., *"Strongly Agree"* or *"Tout à fait d'accord"*). | Decoupled from numerical code values. Supports multilingual text (`JSONB`). |
| **CategorySet** | Representation | A named collection of reusable `Category` URNs (maps to DDI-L `CategoryScheme`). | Reusable set of category labels independent of numerical code assignments. |
| **UnorderedCategorySet** | Representation | An order-independent set-theoretic resource representing a set of `Category` URNs sorted alphabetically (`ucs-fr-...`). | Allows the normalization cascade to detect whether two `CategorySet` instances contain 100% identical category labels regardless of item sequence order. |
| **CodeList** | Representation | A structural set of response codes (`CodeItem` entries) mapping code values to `Category` URNs. | Decouples numerical values (e.g., Code `1`) from category text labels. Its structural URN is computed purely from code-category mappings. |
| **UnorderedCodeList** | Representation | An order-independent set-theoretic resource representing code-category mappings sorted alphabetically (`ucl-fr-...`). | Detects whether two `CodeList` instances share identical code-category pairs regardless of display order, eliminating 70% of manual archivist QA false alarms. |
| **CodeItem** | Representation | A specific value mapping within a `CodeList` connecting a numerical/string code (e.g., `"1"`) to a `Category` label. | Subordinate junction row inside a `CodeList`. |
| **StudyUnit** | Dataset | A specific survey wave or dataset (e.g., *"Baromètre Politique Français 2007"*). | **Renamed from `Survey`**. Serves as the dataset container for survey variables. |
| **InstanceVariable** | Dataset | The physical realization of a variable in a specific survey dataset column (e.g., column `q01a` in survey wave 2007). | **Renamed from `BindingSurveyRepresentedVariable`**. Binds a `RepresentedVariable` to a `StudyUnit`. |
| **VariableGroup** | Organization | A thematic grouping of variables within a study (e.g., *"Demographics"* or *"Political Attitudes"*). | **New entity**. Allows researchers to browse variables organized into thematic sections within a study. |

---

## 2. Identification & URN Classifications

| URN Classification | Definition & Anatomy | Usage & Purpose in ReQuest |
| :--- | :--- | :--- |
| **Curated / Authoritative URN** | A persistent, governance-backed URN assigned by an established data archive (e.g., CDSP, CESSDA, UK Data Service).<br>`urn:ddi:fr.cdsp:QuestionItem:QI_LEFT_RIGHT:1.0.0` | Preserved as the **Canonical URN** during import because it carries institutional authority and version discipline. |
| **Random / Ephemeral URN** | A temporary or auto-generated URN created by third-party DDI authoring tools (e.g., Nesstar, Colectica, Dataverse exports) when exporting files without agency authority.<br>`urn:ddi:int.example:QuestionItem:550e8400-e29b-41d4-a716-446655440000:1` | Detected via UUID/timestamp patterns and routed to the **Heuristic Normalization Cascade**. Saved as an `alias_urn` in `URNAlias`. |
| **Canonical URN** | The single, authoritative database URN assigned to a unique entity row in PostgreSQL.<br>`urn:ddi:fr.cdsp:QuestionItem:qi-fr-e7f2b1c4a9d8e5b2:1.0.0` | Derived deterministically from a **Shortened Hash Digest** (16-char truncated hex / Git-style, or 10-char Base62 URL shortener format) of the entity's SHA-256 `content_hash`. |
| **Alias URN** | An external or random URN mapped to a Canonical URN inside the `URNAlias` table.<br>`alias_urn ➔ canonical_urn` | Maintains 100% data integrity for external references without creating duplicate entity rows in PostgreSQL. |

---

## 3. Normalization & Hashing Terminology

| Term | Definition | Context & Implementation |
| :--- | :--- | :--- |
| **Technical Metadata Normalization** | The automated data engineering pipeline that standardizes raw text (NFKC, typography), parses multi-standard schemas, computes SHA-256 digests, and generates canonical URNs. | Implemented in `request_ddi.normalization` ([`deliverables/normalization.md`](file:///Users/pascal/git-plgah/fairwddi-lifecycle/deliverables/normalization.md)). |
| **Semantic Metadata Harmonization** | The archivist domain workflow that links survey variables across waves via `ConceptualVariable` entities and CESSDA ELSST thesaurus URIs. | Governed by the Concept Layer to enable cross-survey scientific comparison over time. |
| **Simple Text Hashing** | SHA-256 hashing computed directly on a single normalized text string in a specific language `lang`. | Used for base atomic entities (`Category` label, `ConceptualVariable` label, `VariableGroup` label). |
| **Compound URN Hashing** | SHA-256 hashing computed on the **canonical URNs** of an entity's constituent child base components. | Used for structural entities (`QuestionItem`, `CodeList`, `RepresentedVariable`, `InstanceVariable`). Decouples text re-normalization from structure. |
| **Content Hash (`content_hash`)** | A 64-character SHA-256 hexadecimal digest computed from the canonicalized text or compound URN payload of an entity. | Used for deterministic deduplication. If two incoming elements have the same `content_hash`, they are 100% identical. |
| **Canonical Pre-Processing** | The cleaning pipeline applied to strings prior to hashing (Unicode NFKC, whitespace collapsing, typography standardization, sorted JSONB keys). | Ensures hashing is 100% deterministic regardless of minor formatting noise or JSON key ordering. |
| **Sanitized Ideal Text** | Clean, beautifully cased, human-friendly text (NFKC normalized, French typography standard). | Powers clean UI rendering and human-readable Curated URN slugs (e.g. `cat-fr-tout_a_fait_d_accord`). Distinct from lowercased/accent-stripped Canonical Hash Text. |
| **Metadata Drift** | An anomaly where an incoming file reuses an existing URN, but its underlying content (text or categories) has changed without a version increment. | Caught by comparing SHA-256 hashes. Triggers `MetadataQuarantine` to prevent silent database corruption. |
| **Metadata Quarantine** | A holding state (`MetadataQuarantine` table) where conflicting or ambiguous metadata imports await review by a CDSP archivist. | Archivists can one-click **Approve & Merge**, **Fork Version**, or **Reject** the incoming payload. |
| **Hash Strategy (`hash_strategy`)** | The specific algorithm version used to compute a hash or establish an alias (e.g., `v1_strict_sha256`). | Recorded in `URNAlias` to allow safe, audited algorithm migrations in the future. |

---

## 4. Semantic Thesaurus & Multilingual Concepts

| Concept | Definition | Purpose in ReQuest |
| :--- | :--- | :--- |
| **ELSST (European Language Social Science Thesaurus)** | A controlled, multilingual social science vocabulary maintained by CESSDA in 14+ European languages. | `Concept.elsst_uri` links `ConceptualVariable` entities to ELSST URIs, providing cross-language semantic harmonization. |
| **Variable Cascade** | The 3-tier entity hierarchy: `ConceptualVariable → RepresentedVariable → InstanceVariable`. | Enables cross-survey harmonization, longitudinal variable comparison across waves, and multi-study indexing. |
| **JSONB Multilingual Storage** | Storing localized text fields in PostgreSQL `JSONB` columns using ISO 639-1 language keys (`{"fr": "...", "en": "..."}`). | Eliminates single-language database constraints and supports explicit DDI `xml:lang` tags on every text element. |

---

## 5. Staging & Multi-Standard Ingestion Concepts

| Concept | Definition | Purpose in ReQuest Architecture |
| :--- | :--- | :--- |
| **StagedImportPayload** | A PostgreSQL table storing raw uploaded file bundles (`file_name`, `source_format`, `file_path`, `raw_payload`). | Decouples Stage 1 raw file upload from Stage 2 background normalization. Prevents HTTP 504 timeouts. |
| **StagedResourceNode** | A PostgreSQL table storing individual broken-down raw element nodes (`resource_type`, `raw_urn`, `raw_value` JSONB). | Enables granular resource-level normalization, native DDI-L 4 JSON ingestion, and selective re-normalization without re-parsing files. |
| **DDI-L 4 JSON (COGS Model)** | A structured JSON/JSON-LD serialization of DDI-Lifecycle 3.3 (Colectica COGS model). | Parsed directly into `StagedResourceNode` rows in milliseconds during Stage 1 staging. |
| **Standard-Agnostic Core** | The 15 core PostgreSQL tables (`QuestionItem`, `CodeList`, `Category`, `StudyUnit`, etc.) holding normalized domain concepts. | Independent of specific file formats; receives parsed entities from DDI 2.5, DDI 3.3, DDI-L 4 JSON, Croissant, and CSV adapters. |
| **MetadataAdapter** | An abstract Python contract implemented by format-specific parsers (`DDICodebookAdapter`, `DDILifecycleAdapter`, `CroissantAdapter`). | Translates raw XML/JSON tags into standard-agnostic Python dictionaries for Stage 2 normalization. |
