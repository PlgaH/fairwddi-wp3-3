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

### 3.2 Seed Demonstration Data (`fairwddi db seed`)

Populates the database with realistic, multilingual DDI demonstration records (aligned with DDI 4 / DDI-CDI / DDI-L) across all architectural layers (Concepts, Representation, Datasets, Groups, and Staging).

```bash
# Seed records (idempotent get_or_create)
uv run fairwddi db seed
```

#### Resetting Data Before Seeding

To wipe existing records and re-seed clean demonstration data:

```bash
uv run fairwddi db seed --reset
# or short flag
uv run fairwddi db seed -r
```

**Example Output:**
```
Seeding DDI-Lifecycle demonstration data...
 Demonstration Data Seed Summary 
┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Entity / Layer         ┃ Count ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ Organizations          │     1 │
│ Groups                 │     1 │
│ Concepts               │     2 │
│ Conceptual Variables   │     1 │
│ Question Schemes       │     1 │
│ Question Items         │     1 │
│ Question Variables     │     1 │
│ Instruments            │     1 │
│ Instrument Questions   │     1 │
│ Categories             │     6 │
│ Category Schemes       │     1 │
│ Code Lists             │     1 │
│ Codes                  │     6 │
│ Represented Variables  │     1 │
│ Study Units            │     2 │
│ Instance Variables     │     2 │
│ Study Unit Variables   │     2 │
│ Urn Aliases            │     1 │
│ Staged Nodes           │     1 │
│ Event Logs             │     1 │
│ Semantic Relationships │     3 │
└────────────────────────┴───────┘
Database seeded successfully.
```

---

### 3.3 Check Database Inventory (`fairwddi db status`)

Displays the current status of all 28 models/tables along with their active record counts.

```bash
uv run fairwddi db status
```

**Example Output:**
```
                             FAIRwDDI Model Inventory [sqlite3: fairwddi_dev.sqlite3]
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Model Name                ┃ Database Table                    ┃ Record Count ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ ConceptScheme             │ request_ddi_conceptscheme         │            1 │
│ Concept                   │ request_ddi_concept               │            2 │
│ ConceptualVariableScheme  │ request_ddi_conceptualvariablesc… │            1 │
│ ConceptualVariable        │ request_ddi_conceptualvariable    │            1 │
│ SemanticRelationship      │ request_ddi_semanticrelationship  │            3 │
│ QuestionScheme            │ request_ddi_questionscheme        │            1 │
│ QuestionItem              │ request_ddi_questionitem          │            1 │
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
│ StagedImport              │ request_ddi_stagedimport          │            1 │
│ StagedResourceNode        │ request_ddi_stagedresourcenode    │            1 │
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

# Force recreation, followed by demonstration data seeding and top ELSST concept loading
uv run fairwddi db recreate --force --seed --load-vocab
# or using short flags
uv run fairwddi db recreate -f -s -v
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

## 5. Database Connection Configuration & `.env` Files

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

## 6. Python Programmatic API Reference

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
