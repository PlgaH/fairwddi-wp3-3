# FAIRwDDI CLI User Guide

> **Command:** `fairwddi`  
> **Framework:** Typer & Rich  
> **Python Version:** ≥ 3.12 (managed via `uv`)

The `fairwddi` Command-Line Interface (CLI) provides administrative and operational commands to inspect the environment, manage database schemas, export PostgreSQL DDL, seed demonstration records, ingest controlled vocabularies, and stream/stage multi-standard metadata documents.

---

## 1. Installation & Execution

The CLI is registered as a console script entry point in [pyproject.toml](file:///Users/pascal/git-plgah/fairwddi-lifecycle/pyproject.toml).

### Running with `uv` (Recommended)

You can invoke the CLI directly without manual virtualenv activation:

```bash
# View main help and available command groups
uv run fairwddi --help
```

### Running in Activated Virtual Environment

If your virtual environment is active:

```bash
fairwddi --help
```

---

## 2. Global Commands & Diagnostics

### Version Information

Check the installed version of `fairwddi`:

```bash
# Via global flag (eager execution)
uv run fairwddi --version
# or short flag
uv run fairwddi -v

# Via subcommand
uv run fairwddi version
```

**Output:**
```
fairwddi version 0.1.0
```

### Environment & Package Info

Display technical architecture and resolved database configuration:

```bash
uv run fairwddi info
```

**Output:**
```
╭─────────────────────── Environment & Configuration Info ───────────────────────╮
│ FAIRwDDI Lifecycle                                                             │
│ Version: 0.1.0                                                                 │
│ Active DB Engine: sqlite3                                                      │
│ Active DB Target: /Users/pascal/git-plgah/fairwddi-lifecycle/fairwddi_dev.sqlite3│
│ Target Specification: PostgreSQL >= 17 (DDI 4 / DDI-CDI / DDI-L)               │
│ Multilingual Format: JSONB Array of Objects                                    │
╰────────────────────────────────────────────────────────────────────────────────╯
```

---

## 3. Database Management (`fairwddi db`)

All database schema operations, seeding, vocabulary ingestion, and DDL export are grouped under the `db` command namespace.

```bash
uv run fairwddi db --help
```

### 3.1 Initialize Database (`fairwddi db init`)

Applies all pending Django migrations to create the 28 core DDI tables, indexes, and constraints.

```bash
uv run fairwddi db init
```

**Example Output:**
```
Applying database migrations...
Operations to perform:
  Apply all migrations: auth, contenttypes, fairwddi
Running migrations:
  Applying contenttypes.0001_initial... OK
  Applying auth.0001_initial... OK
  Applying fairwddi.0001_initial... OK
Database initialized successfully.
```

---

### 3.2 Check Database Inventory (`fairwddi db status`)

Displays the current status of all 30 models/tables along with their active record counts.

```bash
uv run fairwddi db status
```

**Example Output:**
```
                             FAIRwDDI Model Inventory [postgresql: fairwddi]
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Model Name                ┃ Database Table                    ┃ Record Count ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ ConceptScheme             │ request_ddi_conceptscheme         │            0 │
│ Concept                   │ request_ddi_concept               │            0 │
│ ConceptualVariableScheme  │ request_ddi_conceptualvariablesc… │            0 │
│ ConceptualVariable        │ request_ddi_conceptualvariable    │            0 │
│ SemanticRelationship      │ request_ddi_semanticrelationship  │            0 │
│ QuestionScheme            │ request_ddi_questionscheme        │            0 │
│ QuestionItem              │ request_ddi_questionitem          │            0 │
```
│ CategoryScheme            │ request_ddi_categoryscheme        │            1 │
│ Category                  │ request_ddi_category              │            6 │
│ CodeList                  │ request_ddi_codelist              │            1 │
│ Code                      │ request_ddi_code                  │            6 │
│ RepresentedVariableScheme │ request_ddi_representedvariables… │            1 │
│ RepresentedVariable       │ request_ddi_representedvariable   │            1 │
│ QuestionVariable          │ request_ddi_questionvariable      │            1 │
│ StudyUnit                 │ request_ddi_studyunit             │            2 │
│ InstanceVariableScheme    │ request_ddi_instancevariablesche… │            1 │
│ InstanceVariable          │ request_ddi_instancevariable      │            2 │
│ StudyUnitVariable         │ request_ddi_studyunitvariable     │            2 │
│ EventLog                  │ request_ddi_eventlog              │            1 │
│ UrnRegistry               │ request_ddi_urnregistry           │            0 │
│ URNAlias                  │ request_ddi_urnalias              │            1 │
│ MetadataQuarantine        │ request_ddi_metadataquarantine    │            0 │
│ IngestBatch               │ request_ddi_ingestbatch           │            0 │
│ Instrument                │ request_ddi_instrument            │            1 │
│ InstrumentQuestion        │ request_ddi_instrumentquestion    │            1 │
│ Organization              │ request_ddi_organization          │            1 │
│ Group                     │ request_ddi_group                 │            1 │
└───────────────────────────┴───────────────────────────────────┴──────────────┘
```

---

### 3.4 Export PostgreSQL DDL (`fairwddi db export-ddl`)

Generates standalone, pure PostgreSQL ≥ 17 SQL DDL for database administrators, CI/CD pipelines, or deployment into production without running Django migrations directly.

#### Print DDL to Standard Output:
```bash
uv run fairwddi db export-ddl
```

#### Save DDL to a Target File:
```bash
uv run fairwddi db export-ddl --output schema.sql
# or short flag
uv run fairwddi db export-ddl -o schema.sql
```

**Example Output:**
```
Success: DDL written to schema.sql
```

---

### 3.5 Wipe Database (`fairwddi db wipe`)

Permanently deletes all records across all tables in safe reverse topological order (respecting foreign key relationships).

> [!WARNING]
> This command completely erases all data in the active database. To prevent accidental data loss, it requires a 4-digit verification code by default.

#### Interactive Confirmation (Default):
```bash
uv run fairwddi db wipe
```
**Interactive Prompt:**
```
⚠️  WARNING: You are about to permanently delete ALL records from sqlite3 database fairwddi_dev.sqlite3!
Type confirmation code '8472' to confirm complete database erasure: 8472
Wiping database records...
                 Wipe Summary [sqlite3: fairwddi_dev.sqlite3]
┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ Entity / Table         ┃ Deleted Count ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ Event Logs             │             1 │
│ Semantic Relationships │             3 │
│ Instrument Questions   │             1 │
│ Instruments            │             1 │
│ Study Unit Variables   │             2 │
│ Instance Variables     │             2 │
│ Study Units            │             2 │
│ Question Variables     │             1 │
│ Represented Variables  │             1 │
│ Codes                  │             6 │
│ Code Lists             │             1 │
│ Categories             │             6 │
│ Category Schemes       │             1 │
│ Question Items         │             1 │
│ Question Schemes       │             1 │
│ Conceptual Variables   │             1 │
│ Concepts               │             2 │
│ Groups                 │             1 │
│ Organizations          │             1 │
│ Urn Aliases            │             1 │
│ Staged Nodes           │             1 │
│ Staged Imports         │             1 │
└────────────────────────┴───────────────┘
Database wiped successfully (36 records removed).
```

#### Non-Interactive / Script Execution:

Pass confirmation string (`WIPE` or the generated code) directly:
```bash
uv run fairwddi db wipe --confirm WIPE
```

Or bypass confirmation entirely using the force flag:
```bash
uv run fairwddi db wipe --force
# or short flag
uv run fairwddi db wipe -f
```

---

### 3.6 Drop & Recreate Database (`fairwddi db recreate`)

Drops the entire schema (all tables, constraints, and sequences) and runs all migrations from scratch. Useful for local development resets and testing migrations against empty databases.

```bash
# Interactive schema drop and recreation
uv run fairwddi db recreate

# Force recreation, followed by top ELSST concept loading
uv run fairwddi db recreate --force --load-vocab
# or using short flags
uv run fairwddi db recreate -f -v
```

---

### 3.7 Load Controlled Vocabulary (`fairwddi db load-vocab`)

Generic SKOS / SKOS-XL / XKOS loader that ingests controlled vocabularies from RDF files directly into the `Concept` table.

#### Supported RDF Formats & Standards:
- **Formats:** Turtle (`.ttl`), RDF/XML (`.rdf`, `.xml`), JSON-LD (`.jsonld`, `.json`), N-Triples (`.nt`), Notation3 (`.n3`).
- **Vocabularies:** CESSDA ELSST, CESSDA Topics, DDI-CV, UNESCO Thesaurus, Eurostat RAMON, Agrovoc, STW, custom project taxonomies.
- **Predicates Ingested:** `skos:prefLabel`, `skos:altLabel`, `skos:definition`, `skos:scopeNote`, `skos:notation`, `skos:broader`, `skos:narrower`, `skos:related`, `skos:exactMatch`, `skos:closeMatch`, `xkos:correspondsTo`, `dct:identifier`.

#### Basic Usage:
```bash
# Ingest ELSST Release 6 Turtle file
uv run fairwddi db load-vocab vocab/ELSST_R6.ttl

# Ingest CESSDA Topics RDF/XML file
uv run fairwddi db load-vocab path/to/cessda_topics.rdf --vocabulary "CESSDA Topics"

# Ingest DDI Controlled Vocabulary in JSON-LD format
uv run fairwddi db load-vocab path/to/ddi_cv.jsonld --format json-ld
```

#### Hierarchy Level Control:
You can limit loading to top-level domains, intermediate themes, or load the full concept tree:

```bash
# Load Level 1 only (Top concepts / domains: 249 concepts for ELSST)
uv run fairwddi db load-vocab vocab/ELSST_R6.ttl --levels 1

# Load Levels 1 & 2 (Top concepts + direct children: 1,254 concepts for ELSST)
uv run fairwddi db load-vocab vocab/ELSST_R6.ttl --levels 2

# Load Levels 1 through 3 (2,402 concepts)
uv run fairwddi db load-vocab vocab/ELSST_R6.ttl --levels 3
```

#### Checking Loaded Status (`fairwddi db check-vocab`):
Check all loaded vocabularies or filter by a specific scheme without modifying data:

```bash
# List all loaded vocabularies
uv run fairwddi db check-vocab

# Check specific vocabulary
uv run fairwddi db check-vocab --vocabulary ELSST
```

#### Forcing Reload / Overwrite:
If the vocabulary is already loaded in the database, `load-vocab` safely detects this and halts. To reload or overwrite:

```bash
uv run fairwddi db load-vocab vocab/ELSST_R6.ttl --levels 2 --reload
# or short flag
uv run fairwddi db load-vocab vocab/ELSST_R6.ttl -l 2 -r
```

---

## 4. Metadata Import & Staging (`fairwddi import`)

The `import` command group provides multi-standard metadata file ingestion, high-performance streaming parsing, YAML/JSON profile management, staging inspection, and diagnostic audit logs.

```bash
uv run fairwddi import --help
```

### 4.1 Import Metadata File (`fairwddi import file`)

Streams and stages external metadata documents (`.ddi33.xml`, `.ddi40.json`, `.ddic.xml`, CSV, etc.) into `StagedImport` and `StagedResourceNode` records.

```bash
# Stage a DDI-Lifecycle 3.3 XML file using default profile
uv run fairwddi import file path/to/study.ddi33.xml

# Stage using a custom profile preset or YAML path
uv run fairwddi import file path/to/study.ddi33.xml --profile profiles/request_profile.yaml
# or short flag
uv run fairwddi import file path/to/study.ddi33.xml -p request

# Dry-run validation (parse and check without writing to database)
uv run fairwddi import file path/to/study.ddi33.xml --dry-run

# Force re-staging an already ingested file
uv run fairwddi import file path/to/study.ddi33.xml --force-reload
# or short flag
uv run fairwddi import file path/to/study.ddi33.xml -r

# Specify explicit format override and bulk batch size
uv run fairwddi import file path/to/data.xml --format "ddi-l:3.3:xml" --batch-size 2000
```

**Example Output:**
```
Processing metadata file study.ddi33.xml with profile request...
 Metadata Import Summary [study.ddi33.xml] 
┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Metric / Property      ┃ Value                       ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Staged Import ID       │ #1                          │
│ Detected Specification │ DDI-Lifecycle 3.3 (xml)     │
│ Producer Flavor        │ Colectica                   │
│ Active Profile         │ request                     │
│ Total Resources Staged │ 14,280                      │
│ Skipped Duplicates     │ 0                           │
│ Quarantined Drift Items│ 0                           │
│ Elapsed Time           │ 1.842s                      │
│ Throughput             │ 7,752.4 resources/sec       │
│ Session Audit Log      │ logs/import_1_20260925.log  │
└────────────────────────┴─────────────────────────────┘
 Staged Nodes by Resource Type 
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Resource Type       ┃ Count ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ InstanceVariable    │ 4,800 │
│ Code                │ 4,200 │
│ Category            │ 3,100 │
│ QuestionItem        │ 1,200 │
│ RepresentedVariable │   950 │
│ CodeList            │    25 │
│ StudyUnit           │     5 │
└─────────────────────┴───────┘
Stage 1 import completed successfully.
```

---

### 4.2 List Available Import Profiles (`fairwddi import list-profiles`)

Displays all YAML/JSON ingestion profiles located in `profiles/` with inclusion/exclusion filters and reference resolution rules.

```bash
uv run fairwddi import list-profiles
```

**Example Output:**
```
                              Available Import Profiles                              
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Profile Name ┃ Description                   ┃ Include Types ┃ Exclude Types ┃ Resolve Refs ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ request      │ ReQuest Question Bank Profile │             8 │          None │      ✓       │
│ all_ddi      │ Ingest all DDI-L resources    │           ALL │          None │      ✓       │
│ minimal      │ Core variables & questions    │             3 │          None │      ✗       │
└──────────────┴───────────────────────────────┴───────────────┴───────────────┴──────────────┘
```

---

### 4.3 List Staged Import Jobs (`fairwddi import list`)

Lists past import staging batches with their status, format, and staged resource counts.

```bash
# List recent staged imports
uv run fairwddi import list

# Filter by status and format with custom limit
uv run fairwddi import list --status staged --format xml --limit 10
# or using short flags
uv run fairwddi import list -s staged -n 10
```

---

### 4.4 Import Statistics & Reports (`fairwddi import stats`)

Renders comprehensive breakdown metrics, normalization progress, URN alias counts, and resource type cross-tabulations.

```bash
# Render interactive Rich table
uv run fairwddi import stats 1

# Export structured JSON statistics
uv run fairwddi import stats 1 --format json --output stats_1.json

# Render or save Markdown audit report
uv run fairwddi import stats 1 --format markdown --output report_1.md
```

---

### 4.5 Query Staged Resource Nodes (`fairwddi import query`)

Filter and inspect individual broken-down resource nodes within the staging tables without writing SQL.

```bash
# Query nodes by resource type and status
uv run fairwddi import query --type QuestionItem --status staged

# Search by URN substring and preview raw JSON payload
uv run fairwddi import query --search "fr.cdsp:Q01" --show-json --limit 5

# Filter by specific StagedImport batch ID
uv run fairwddi import query --import-id 1 --type CodeList
```

---

### 4.6 Inspect Job Status (`fairwddi import status`)

Provides detailed execution status, total processed resources, timestamps, and node status breakdowns for an import ID.

```bash
uv run fairwddi import status 1
```

---

### 4.7 View Session Audit Log (`fairwddi import log`)

Displays the verbatim disk audit log generated during the staging process.

```bash
uv run fairwddi import log 1
```

---

### 4.8 Delete Staged Import (`fairwddi import delete`)

Safely deletes a staged import job and all associated child `StagedResourceNode` records. Includes automatic protection checks if resources have already been normalized or referenced downstream.

```bash
# Interactive deletion prompt
uv run fairwddi import delete 1

# Skip confirmation and clean up disk audit log
uv run fairwddi import delete 1 --yes --delete-log
# or short flags
uv run fairwddi import delete 1 -y --delete-log

# Force delete (overriding normalization protection checks)
uv run fairwddi import delete 1 --yes --force
```

---

## 5. Phase 2 Direct Ingestion & Harmonization Pipeline

Phase 2 introduces a **direct file-to-core streaming pipeline** (`fairwddi preflight`, `ingest`, `compare`, `harmonize`) that eliminates intermediate database staging tables. Metadata documents stream directly from disk into ReQuest core tables, with review-gated dry-run YAML plans and single-row batch receipts (`IngestBatch`).

---

### 5.1 Preflight Stage (`fairwddi preflight`)

The `preflight` command group inspects incoming files, validates profile conformance, audits persistent URN references, and executes explicit DDI-C to DDI-L disk conversions.

```bash
uv run fairwddi preflight --help
```

#### Command Roles: `preflight profile` vs. `preflight check` vs. `import plan`

| Command | Core Question Answered | DB Access | Converts DDI-C? | Default Outputs (in `.` unless noted) | Executable by `import execute`? |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `fairwddi preflight profile` | *"What is inside this XML file, and what is its documentation quality?"* | **None** | No | `<stem>.profile.json`, `<stem>.profile.md` | No |
| `fairwddi preflight check` | *"Is this file clean, non-duplicate, and URN-ready for this ReQuest DB?"* | **Read-only** (`IngestBatch`, `UrnRegistry`) | No (flags recommendation only) | `<stem>.preflight.json`, `<stem>.preflight.report.md` | No (readiness report only) |
| `fairwddi preflight upgrade` | *"Convert DDI-C XML to DDI-L 4.0/3.3 files on disk."* | **None** | **Yes** (writes to disk) | `*.ddi40.json`, `*.stats.ddi40.json`, `*.upgrade.report.md` | No (produces input for `import plan` / `run`) |
| `fairwddi import plan` | *"Exactly which DB entities will be created, reused, or quarantined?"* | **Read-only** (`UrnRegistry`, `IngestBatch`) | **No** (streams raw DDI-C in-memory without `CodebookToLifecycleConverter`) | `<stem>.import.plan.yaml`, `<stem>.import.report.md` | **Yes** |
| `fairwddi import run` | *"Run preflight, optional DDI-C upgrade, plan, and atomic load end-to-end."* | **Read + Atomic Write** (or read-only with `--dry-run`) | **Yes** (writes `*.ddi40.json` when given DDI-C) | Writes DB rows + `IngestBatch` receipt | N/A (executes directly) |

> [!TIP]
> **Which input should you pass to `fairwddi import plan` for DDI-Codebook?**
> - **Step-by-step:** Run `fairwddi preflight upgrade study.ddic.xml` first, then pass the upgraded `study.ddic.ddi40.json` to `fairwddi import plan` (this preserves `CodebookToLifecycleConverter` deduplication, `--category-scheme-mode`, `--id-strategy`, and `VariableStatistics` splitting).
> - **All-in-one:** Pass `study.ddic.xml` directly to `fairwddi import run` (add `--dry-run` to stop after `upgrade` + `import plan` without writing to the DB).
> - `preflight profile` and `preflight check` remain optional read-only QA reports before planning.

#### Preflight Readiness Check (`fairwddi preflight check`)

Audits metadata structure and generates a JSON report (`.preflight.json`) and Markdown report (`.preflight.report.md`) in the output directory (default: `.`):

```bash
uv run fairwddi preflight check tests/fixtures/FSD3562_eng.ddic.xml \
  --profile request \
  --output-dir ./ingest_output
```

*Key Options:*
- `-o, --output-dir`: Destination directory for `.preflight.json` and `.preflight.report.md` (default: `.`).
- `--auto-approve`: Automatically mark review gates as approved.

*Interpreting Findings & Remediation:*

| Finding / Code | Meaning | What to Do |
| :--- | :--- | :--- |
| **`PRE-FMT-001`** *(error)* | Unrecognized format or XML namespace | Verify the file isn't truncated and check its root XML namespace (`ddi:codebook:2_5`, `ddi:instance:3_3`) or DDI 4.0 JSON structure. |
| **`PRE-DUP-001`** *(warning)* | Identical file SHA-256 already exists in `IngestBatch` | Inspect the existing batch with `fairwddi import status <batch_id>`. Skip re-importing, or pass `--force-reload` to `fairwddi import plan` / `run` if you intentionally want a new batch. |
| **`PRE-URN-002`** *(warning)* | Resources have synthesized/anonymous URNs (`:anonymous:` / `:unknown.agency:`) | For DDI-C, run `fairwddi preflight upgrade <file> --agency <agency> --identifier <id>` (or pass `--agency` to `import run`) to assign proper canonical URNs before loading; for DDI-L, fix missing agency/IDs in the source XML. |
| **`PRE-REF-002`** *(warning)* | External `urn:ddi:...` references are missing from the file and `UrnRegistry` | Import the referenced dependency file/scheme first (or load controlled vocabularies with `fairwddi db load-vocab`), or confirm dangling external refs are acceptable before planning. |
| **Profiler QA findings / `PRE-DDIC-001`** | Missing study/variable documentation (from `dartfx-ddi` `recommended` / `cdif` / `schema` checks) or 0 variables | Run `fairwddi preflight profile <file>` for full variable-level details, fix the source XML upstream, or switch `--profile` (e.g., to `schema` or a custom profile YAML) if those rules are stricter than needed. |

If blocking errors exist (`error_count > 0`), resolve them before planning; if only acceptable warnings remain, proceed to `fairwddi import plan <file>` (or `fairwddi import run <file>`).

#### Explicit DDI-C to DDI-L Upgrade on Disk (`fairwddi preflight upgrade`)

Upgrades DDI-Codebook (2.5/2.6) XML files into canonical DDI-Lifecycle 4.0 JSON/XML on disk. When empirical observation statistics are present, the upgrade automatically emits **two decoupled files**:
1. **Primary Question Bank & Study File (`*.ddi40.json`):** Reusable `StudyUnit`, `LogicalProduct`, schemes, `QuestionItem`, `Variable`, `CodeList`, `Category`, and `PhysicalInstance` layout.
2. **Dedicated Secondary Statistics File (`*.stats.ddi40.json`):** Strongly-typed `VariableStatistics` elements containing `TotalResponses`, `SummaryStatisticType`, and `UnfilteredCategoryStatisticsType`.

```bash
uv run fairwddi preflight upgrade survey.ddic.xml \
  --output ./ingest_output/survey.ddi40.json \
  --format ddi4-json \
  --agency fr.cdsp \
  --version 2.0.0 \
  --harmonize-codes \
  --harmonize-questions
```

*Rich Terminal Summary:*
```text
                         DDI-C to DDI-L Upgrade Summary                         
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Metric                    ┃ Value                                            ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Output DDI-L File         │ ./ingest_output/survey.ddi40.json                │
│ Statistics DDI-L File     │ ./ingest_output/survey.stats.ddi40.json          │
│ Upgrade Report            │ ./ingest_output/survey.ddi40.upgrade.report.md   │
│ Agency / Version          │ fr.cdsp / 2.0.0                                  │
│ Variables                 │ 300                                              │
│ CodeLists (Deduplicated)  │ 80 (197 duplicates removed, 71.1% reduction)     │
│ Categories (Deduplicated) │ 610 (1,108 duplicates removed, 64.5% reduction)  │
│ Questions (Deduplicated)  │ 180 (120 duplicates removed, 40.0% reduction)    │
│ Physical Instances        │ 1                                                │
│ Variable Statistics       │ 300 (1,718 frequencies, 1,587 summary stats)     │
└───────────────────────────┴──────────────────────────────────────────────────┘
```

*CLI Options for `preflight upgrade`:*
- `--harmonize-codes / --no-harmonize-codes`: Enable/disable semantic deduplication of identical code lists and response categories across variables (default: enabled).
- `--harmonize-questions / --no-harmonize-questions`: Enable/disable deduplication of identical question texts across variables during DDI-C upgrade (default: enabled).

*Standalone Conversion with `dartfx-ddi`:*
The converter is part of the `ddi-toolkit` library and can also be executed independently via the standalone CLI:
```bash
uv run --directory /path/to/ddi-toolkit dartfx-ddi ddic2l survey.ddic.xml \
  --output survey.ddi40.json \
  --agency fr.cdsp \
  --version 2.0.0 \
  --harmonize-codes
```

#### List Available Profiles (`fairwddi preflight profiles`)

Lists all installed declarative import and validation profiles:

```bash
uv run fairwddi preflight profiles
```

#### Profile DDI Metadata (`fairwddi preflight profile`)

Generates full DDI-Codebook or DDI-Lifecycle JSON (`.profile.json`) and Markdown (`.profile.md`) reports in the output directory (default: `.`):

```bash
uv run fairwddi preflight profile tests/fixtures/FSD3562_eng.ddic.xml --profile request
```

---

### 5.2 Pure Deterministic Import Stage (`fairwddi import`)

The `import` command group performs pure, deterministic file-to-core metadata loading with **zero cross-study harmonization**:

```bash
# Direct one-command import (preflight -> optional DDI-C upgrade -> plan -> execute)
uv run fairwddi import survey.ddic.xml \
  --profile request \
  --category-scheme-mode per_codelist \
  --output-dir ./import_output

# Dry-run planning only
uv run fairwddi import survey.ddic.xml --dry-run --output-dir ./import_output
```

#### Generate Dry-Run Import Plan (`fairwddi import plan`)

Streams the document in constant memory, checks URNs in `UrnRegistry`, detects metadata drift (`IMP-DRIFT-001`), and plans deterministic core allocations with **zero database writes**:

```bash
uv run fairwddi import plan ./import_output/survey.ddi40.json \
  --profile request \
  --output-dir ./import_output
```

Emits `./import_output/survey.ddi40.import.plan.yaml` and `.import.report.md`.

> [!NOTE]
> **Why use `import plan` and `deliverables/editors/import_plan_editor.html` when import does zero harmonization?**
> Even without cross-study harmonization, deterministic loading still encounters identity and integrity edge cases that should not silently mutate the database:
> - **Same-URN Content Drift (`IMP-DRIFT-001`):** Incoming entity matches an existing URN in `UrnRegistry` with a *different* SHA-256 `content_hash` (triage for `MetadataQuarantine` vs. skip).
> - **Same-URN Cross-File Reuse (`IMP-URN-REUSE-001`):** Incoming entity matches an existing URN with an *identical* `content_hash` (confirm intentional reuse rather than accidental ID collision).
> - **Duplicate File (`PRE-DUP-001`) & Zero-Write Audit:** Preview exact `create` / `reuse` / `quarantine` counts and sign the `ReviewGate` before committing. For clean first-time imports, `fairwddi import run` can bypass manual plan editing.

#### Execute Import Plan (`fairwddi import execute`)

Executes insertion into PostgreSQL within an atomic transaction. Writes an `IngestBatch` receipt and bulk-loads frequency rows:

```bash
# Execute from an approved plan YAML
uv run fairwddi import execute ./import_output/survey.ddi40.import.plan.yaml

# Or execute directly from the metadata file
uv run fairwddi import execute ./import_output/survey.ddi40.json --auto-approve
```

#### Atomic Rollback & Batch Inspection (`fairwddi import undo` / `list` / `status`)

```bash
# List recent import batches
uv run fairwddi import list --limit 10

# Inspect batch receipt details
uv run fairwddi import status 42

# Atomically roll back batch #42
uv run fairwddi import undo 42
```

---

### 5.3 DDI Context Groups (`fairwddi group`)

Curate reusable DDI `Group` contexts (longitudinal series, thematic collections, question grids) identified by both canonical DDI URN and unique human-friendly `slug`:

```bash
uv run fairwddi group create "ESS France Series" --slug ess-fr --type longitudinal_series \
  --member urn:ddi:fr.cdsp:su_ess_w1:1.0.0 \
  --member urn:ddi:fr.cdsp:su_ess_w2:1.0.0

uv run fairwddi group list
uv run fairwddi group show ess-fr
uv run fairwddi group add ess-fr --member urn:ddi:fr.cdsp:su_ess_w3:1.0.0
```

---

### 5.4 Read-Only Two-Set, Three-Layer Comparison (`fairwddi compare`)

Compares any two resolved resource sets (`group:<slug|urn>`, `batch:<id>`, `study:<urn>`, `bank[:all|imported|harmonized]`, `urn:<u1,u2>`) across up to three layers (`syntactic`, `semantic`, `conceptual`) with independent CodeList qualification and zero database writes:

```bash
# List built-in presets (default, syntactic, semantic, multilingual)
uv run fairwddi compare configs

# Compare a newly imported batch against a curated series group
uv run fairwddi compare run \
  --source batch:42 \
  --target group:ess-fr \
  --level syntactic --level semantic \
  --type QuestionItem --type RepresentedVariable \
  --output-dir ./compare_output
```

---

### 5.5 Review-Gated Harmonization (`fairwddi harmonize`)

Consumes comparison outputs (`.comparison.yaml` / `.comparison.json`) under a declarative `HarmonizationPolicy` (defining explicit `auto_approve_high` criteria and CodeList divergence guardrails):

#### 1. Plan & Execute Harmonization

```bash
# Generate harmonization plan (all items pending manual review by default)
uv run fairwddi harmonize plan ./compare_output/compare-abc12345.comparison.yaml \
  --output-dir ./harm_output

# Or auto-approve qualifying high-confidence items directly during plan creation
uv run fairwddi harmonize plan ./compare_output/compare-abc12345.comparison.yaml \
  --approve-high \
  --output-dir ./harm_output

# Execute approved harmonization actions atomically
uv run fairwddi harmonize execute ./harm_output/harmonize-abc12345.harmonize.plan.yaml

# Roll back harmonization changes using EventLog snapshot
uv run fairwddi harmonize undo <job_id>
```

---

#### 2. Create Harmonized Resource (`fairwddi harmonize create`)

Creates a new `generated` (default) or `instantiated` harmonized resource uniting one or more `imported` source resources. Fuses multilingual labels and question texts, preserves all source records intact as `origin='imported'`, records W3C `prov:wasDerivedFrom` lineage edges, and records alternate spellings in `extended_attributes` (`wording_variant`):

```bash
# Create a generated harmonized QuestionItem with auto-generated generic URN
uv run fairwddi harmonize create \
  --source urn:ddi:fr.cdsp:elipss.2015.q01:1.0.0 \
  --source urn:ddi:fr.cdsp:elipss.2016.q01:1.0.0 \
  --name "Trust in National Assembly (Harmonized)"

# Create an administrator-instantiated resource with an explicit canonical target DDI URN
uv run fairwddi harmonize create \
  -s urn:ddi:fr.cdsp:elipss.2015.q01:1.0.0 \
  -s urn:ddi:fr.cdsp:elipss.2016.q01:1.0.0 \
  -t urn:ddi:fr.cdsp:QI-trust-national-assembly:1.0.0 \
  --origin instantiated
```

**Key Options:**
- `--source / -s`: Source `imported` URN(s) to harmonize (can specify multiple times).
- `--target-urn / -t`: Explicit canonical generic DDI URN (auto-generated if omitted).
- `--type / -T`: Optional resource type (e.g., `QuestionItem`, `RepresentedVariable`, `Category`). Auto-inferred if omitted.
- `--name / -n`: Human-readable label/name for the harmonized generic resource.
- `--origin`: Resource origin classification: `generated` (default) or `instantiated`.
- `--canonical-text`: Preferred text or translation dictionary for primary display.
- `--note`: Provenance note stored in `SemanticRelationship` and `EventLog`.

---

#### 3. Link to Existing Harmonized Resource (`fairwddi harmonize link`)

Links newly imported survey resources to an *already existing* harmonized target (`origin='generated'` or `'instantiated'`). Preserves source records intact, enriches the target with newly provided translations or alternate spellings (`wording_variant`), and records `prov:wasDerivedFrom` lineage:

```bash
# Link a wave 3 question to the existing harmonized QuestionItem
uv run fairwddi harmonize link \
  --source urn:ddi:fr.cdsp:elipss.2017.q01:1.0.0 \
  --target-urn urn:ddi:fr.cdsp:QI-trust-national-assembly:1.0.0 \
  --note "Wave 3 longitudinal linkage"
```

**Key Options:**
- `--source / -s`: Source `imported` URN(s) to link (can specify multiple times).
- `--target-urn / -t`: Target canonical harmonized URN (must already exist in `UrnRegistry`).
- `--type / -T`: Optional DDI resource type. Auto-inferred from target URN if omitted.
- `--canonical-text`: Preferred text to set on the target entity.
- `--note`: Audit note stored in `SemanticRelationship` and `EventLog`.

---

#### 4. Reverting Harmonization (`fairwddi harmonize undo`)

Reverts an applied harmonization or linkage job using its complete `EventLog` snapshot:

```bash
# Revert a creation job (removes generated entity and lineage links, provided no later batches depend on it)
uv run fairwddi harmonize undo harm-generated-questionitem-7f2a1b

# Revert a linkage job (restores target to pre-linkage state and removes prov:wasDerivedFrom link)
uv run fairwddi harmonize undo link-questionitem-9a0257
```

---

## 6. Database Connection Configuration & `.env` Files

The CLI automatically looks for and loads a `.env` file in the current working directory or any parent directory.

### Quick Setup with `.env`

Copy the provided template to create your local `.env`:

```bash
cp .env.example .env
```

---

### Supported Connection Options

The database resolver checks configurations in the following order of priority:

#### Option 1: `DATABASE_URL` (PostgreSQL or SQLite)

Recommended for 12-factor apps, Docker, and Kubernetes:

```env
# PostgreSQL
DATABASE_URL=postgresql://fairwddi_user:secret_password@localhost:5432/fairwddi_db

# SQLite
DATABASE_URL=sqlite:///./fairwddi_dev.sqlite3
```

#### Option 2: Discrete PostgreSQL Environment Variables

Directly configure individual PostgreSQL parameters:

```env
POSTGRES_DB=fairwddi_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

*(You can also use standard aliases like `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`.)*

#### Option 3: Standalone SQLite File Path (Default)

If no PostgreSQL variables are defined, the CLI automatically defaults to a persistent SQLite database for fast local development:

```env
FAIRWDDI_DB_PATH=./fairwddi_dev.sqlite3
```

#### Option 4: Existing Django Application (`DJANGO_SETTINGS_MODULE`)

When running within an existing Django deployment (such as the CDSP ReQuest platform), set `DJANGO_SETTINGS_MODULE` to use the host project's settings:

```env
DJANGO_SETTINGS_MODULE=request_service.settings
```

---

### Environment Variables Reference Table

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | _None_ | Complete connection string (e.g. `postgresql://user:pass@host:5432/db`). |
| `POSTGRES_DB` / `DB_NAME` | _None_ | PostgreSQL database name. |
| `POSTGRES_USER` / `DB_USER` | `postgres` | PostgreSQL username. |
| `POSTGRES_PASSWORD` / `DB_PASSWORD` | `""` | PostgreSQL password. |
| `POSTGRES_HOST` / `DB_HOST` | `localhost` | PostgreSQL server hostname or IP. |
| `POSTGRES_PORT` / `DB_PORT` | `5432` | PostgreSQL server port. |
| `FAIRWDDI_DB_PATH` | `./fairwddi_dev.sqlite3` | SQLite file path when running in standalone mode. |
| `DJANGO_SETTINGS_MODULE` | _None_ | Host Django settings module for integrated setups. |
| `DJANGO_SECRET_KEY` | `fairwddi-cli-default-secret-key` | Secret key used for cryptographic signing. |

---

## 7. Python Programmatic API Reference

All CLI commands and underlying data structures correspond directly to clean, reusable Python APIs in `fairwddi`:

### 6.1 Database Operations (`fairwddi.db`)

```python
from fairwddi.db import (
    export_postgres_ddl,
    seed_sample_data,
    wipe_database,
    load_skos_vocabulary,
    check_vocabulary_loaded,
)

# 1. Export PostgreSQL DDL SQL
sql = export_postgres_ddl("custom_schema.sql")

# 2. Programmatically seed demonstration data
seed_summary = seed_sample_data(reset=True)
print(f"Seeded {seed_summary['instance_variables']} instance variables.")

# 3. Ingest SKOS/XKOS controlled vocabulary
vocab_stats = load_skos_vocabulary("vocab/ELSST_R6.ttl", max_levels=2)
print(f"Loaded {vocab_stats['total_concepts']} concepts.")

# 4. Check loaded status
status = check_vocabulary_loaded(vocabulary="ELSST")
if status["loaded"]:
    print(f"ELSST is active with {status['total_concepts']} concepts.")

# 5. Programmatically wipe all tables
wipe_summary = wipe_database()
```

### 6.2 Metadata Ingestion & Staging API (`fairwddi.importer`)

```python
from pathlib import Path
from fairwddi.importer import (
    import_metadata_file,
    list_staged_imports,
    get_import_statistics,
    query_staged_resources,
    delete_staged_import,
    list_available_profiles,
    detect_metadata_format,
)

# 1. Detect file format
fmt = detect_metadata_format(Path("study.ddi33.xml"))
print(f"Format: {fmt.specification} {fmt.version} ({fmt.serialization})")

# 2. Stage metadata file
summary = import_metadata_file(
    file_path="study.ddi33.xml",
    profile="request",
    batch_size=1000,
    dry_run=False,
)
print(f"Staged {summary['total_staged']} resources (Import #{summary['staged_import_id']}).")

# 3. Query staged resource nodes
nodes = query_staged_resources(
    import_id=summary["staged_import_id"],
    resource_type="QuestionItem",
    limit=20,
)
for item in nodes["results"]:
    print(f"Question URN: {item['raw_urn']}")

# 4. Get detailed metrics and cross-tabulation
stats = get_import_statistics(summary["staged_import_id"])
print(f"Normalization progress: {stats['normalization_progress_pct']}%")

# 5. Delete staged batch
delete_result = delete_staged_import(summary["staged_import_id"], force=True)
```

### 6.3 Pydantic v2 Validation & Serialization (`fairwddi.schemas`)

```python
from fairwddi.schemas import (
    ConceptSchema,
    QuestionItemSchema,
    RepresentedVariableSchema,
    InstanceVariableSchema,
    MultilingualItem,
)

# Create a validated QuestionItem
question = QuestionItemSchema(
    urn="urn:ddi:fr.cdsp:QI_PolInterest:1.0.0",
    name=[MultilingualItem(lang="fr", value="QI_Interet_Politique")],
    question_text=[
        MultilingualItem(lang="fr", value="Dans quelle mesure vous intéressez-vous à la politique ?"),
        MultilingualItem(lang="en", value="How interested are you in politics?"),
    ],
    interviewer_instructions=[
        MultilingualItem(lang="fr", value="Ne pas lire les options 'Sans opinion'."),
    ],
)

# Serialize to JSON-LD / API response
json_payload = question.model_dump_json(indent=2)
```

### 6.4 Django ORM Models (`fairwddi.models`)

```python
from fairwddi.models import (
    Concept,
    ConceptualVariable,
    RepresentedVariable,
    InstanceVariable,
    QuestionItem,
    CodeList,
    StudyUnit,
)

# Query the variable cascade
for rv in RepresentedVariable.objects.select_related("conceptual_variable").all():
    print(f"RepresentedVariable: {rv.urn} -> Concept: {rv.conceptual_variable.urn}")
```

---

## 7. Interactive Visual Explorer & REST API (`fairwddi serve`)

For stakeholder demonstrations, cross-survey harmonization reviews, and visual question bank exploration, `fairwddi` provides a built-in interactive Single-Page Application (SPA) powered by `django-ninja`:

```bash
# Start server and auto-open the browser to the visual explorer
uv run fairwddi serve --open

# Or specify host and port
uv run fairwddi serve --host 127.0.0.1 --port 8000
```

### URLs Provided
- **Interactive Visual Explorer:** `http://127.0.0.1:8000/explorer`
- **Interactive Swagger / OpenAPI Docs:** `http://127.0.0.1:8000/api/docs`
- **REST API Base URL:** `http://127.0.0.1:8000/api`

### Core Explorer Capabilities
1. **DDI Variable Cascade Visualizer:** Click any canonical question to inspect its complete node-link lineage graph (`ConceptualVariable` $\rightarrow$ `RepresentedVariable` $\rightarrow$ `[InstanceVariables across waves]`), with inbound dashed arrows showing historical `URNAlias` provenance links.
2. **Cross-Wave Survey Harmonization Matrix:** Side-by-side comparison table (e.g. ELIPSS 2013 vs 2014) showing how repeated survey questions share identical canonical entities.
3. **URN Alias Crosswalk Directory:** Real-time lookup resolving historical wave URNs to canonical database master records.
4. **Entity Inspector:** Slide-out drawer with syntax-highlighted multilingual text, content hashes, and dataset column metadata.
