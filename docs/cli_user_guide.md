# FAIRwDDI CLI User Guide

> **Command:** `fairwddi`  
> **Framework:** Typer & Rich  
> **Python Version:** ≥ 3.12 (managed via `uv`)

The `fairwddi` Command-Line Interface (CLI) provides administrative and operational commands to inspect the environment, manage database schemas, export PostgreSQL DDL, seed demonstration records, and view database inventories.

---

## 1. Installation & Execution

The CLI is registered as a console script entry point in `pyproject.toml`.

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

Display technical architecture and profile information:

```bash
uv run fairwddi info
```

**Output:**
```
╭─────────────────────── Package Info ───────────────────────╮
│ FAIRwDDI Lifecycle                                         │
│ Version: 0.1.0                                             │
│ Target Database: PostgreSQL >= 17 (Clean Standard DDL)     │
│ DDI Specification: DDI Model (DDI 4 / DDI-CDI / DDI-L)     │
│ Multilingual Format: JSONB Array of Objects                │
╰────────────────────────────────────────────────────────────╯
```

---

## 3. Database Management (`fairwddi db`)

All database operations are grouped under the `db` command namespace.

```bash
uv run fairwddi db --help
```

### 3.1 Initialize Database (`fairwddi db init`)

Applies all pending Django migrations to create the 16 core DDI tables, indexes, and constraints.

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

Populates the database with realistic, multilingual DDI demonstration records (aligned with DDI 4 / DDI-CDI / DDI-L) across all 6 architectural layers (Concepts, Representation, Datasets, Groups, and Staging).

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
┏━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Entity / Layer        ┃ Count ┃
┡━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ Distributors          │     1 │
│ Collections           │     1 │
│ Subcollections        │     1 │
│ Concepts              │     2 │
│ Concept Relationships │     1 │
│ Conceptual Variables  │     2 │
│ Question Items        │     1 │
│ Categories            │     6 │
│ Category Sets         │     1 │
│ Code Lists            │     1 │
│ Code Items            │     6 │
│ Represented Variables │     1 │
│ Study Units           │     2 │
│ Instance Variables    │     2 │
│ Variable Groups       │     1 │
│ Urn Aliases           │     1 │
│ Staged Nodes          │     1 │
└───────────────────────┴───────┘
Database seeded successfully.
```

---

### 3.3 Check Database Inventory (`fairwddi db status`)

Displays the current status of all 21 models/tables along with their active record counts.

```bash
uv run fairwddi db status
```

**Example Output:**
```
                            FAIRwDDI Model Inventory                            
┏━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Model Name              ┃ Database Table                      ┃ Record Count ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ Concept                 │ request_ddi_concept                 │            2 │
│ ConceptualVariable      │ request_ddi_conceptualvariable      │            2 │
│ Distributor             │ request_ddi_distributor             │            1 │
│ Collection              │ request_ddi_collection              │            1 │
│ Subcollection           │ request_ddi_subcollection           │            1 │
│ QuestionItem            │ request_ddi_questionitem            │            1 │
│ Category                │ request_ddi_category                │            6 │
│ CategorySet             │ request_ddi_categoryset             │            1 │
│ CategorySetItem         │ request_ddi_categorysetitem         │            4 │
│ CodeList                │ request_ddi_codelist                │            1 │
│ CodeItem                │ request_ddi_codeitem                │            6 │
│ RepresentedVariable     │ request_ddi_representedvariable     │            1 │
│ StudyUnit               │ request_ddi_studyunit               │            2 │
│ InstanceVariable        │ request_ddi_instancevariable        │            2 │
│ VariableGroup           │ request_ddi_variablegroup           │            1 │
│ VariableGroupMembership │ request_ddi_variablegroupmembership │            1 │
│ URNAlias                │ request_ddi_urnalias                │            1 │
│ MetadataQuarantine      │ request_ddi_metadataquarantine      │            0 │
│ StagedImportPayload     │ request_ddi_stagedimportpayload     │            1 │
│ StagedResourceNode      │ request_ddi_stagedresourcenode      │            1 │
└─────────────────────────┴─────────────────────────────────────┴──────────────┘
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
> This command completely erases all data in the active database. To prevent accidental data loss, it requires explicit string confirmation by default.

#### Interactive Confirmation (Default):
```bash
uv run fairwddi db wipe
```
**Interactive Prompt:**
```
⚠️  WARNING: You are about to permanently delete ALL records from sqlite3 database /Users/pascal/git-plgah/fairwddi-lifecycle/fairwddi_dev.sqlite3!
Type 'WIPE' to confirm complete database erasure: WIPE
Wiping database records...
                 Wipe Summary                 
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ Entity / Table             ┃ Deleted Count ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ Variable Group Memberships │             1 │
│ Variable Groups            │             1 │
│ Instance Variables         │             2 │
│ Study Units                │             2 │
│ Represented Variables      │             1 │
│ Code Items                 │             6 │
│ Code Lists                 │             1 │
│ Category Set Items         │             4 │
│ Category Sets              │             1 │
│ Categories                 │             6 │
│ Question Items             │             1 │
│ Conceptual Variables       │             2 │
│ Concept Relationships      │             1 │
│ Concepts                   │             2 │
│ Subcollections             │             1 │
│ Collections                │             1 │
│ Distributors               │             1 │
│ Urn Aliases                │             1 │
│ Staged Nodes               │             1 │
│ Staged Payloads            │             1 │
└────────────────────────────┴───────────────┘
Database wiped successfully (37 records removed).
```

#### Non-Interactive / Script Execution:

Pass confirmation string directly:
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

### 3.6 Load Controlled Vocabulary (`fairwddi db load-vocab`)

Generic SKOS / SKOS-XL / XKOS loader that ingests any controlled vocabulary from RDF files into the `Concept` table.

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

#### Checking Loaded Status:
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

**Example Output:**
```
Loading vocabulary ELSST from vocab/ELSST_R6.ttl (Levels: 2)...
 Vocabulary Load Summary [ELSST]  
┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Metric                 ┃ Value ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ Total Concepts Loaded  │  1254 │
│ Top Concepts (Level 1) │   249 │
│ Levels Traversed       │     2 │
│ Relationships Created  │  1716 │
│ Elapsed Time           │ 3.38s │
└────────────────────────┴───────┘
Vocabulary 'ELSST' loaded successfully.
```

---

## 4. Database Connection Configuration & `.env` Files

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

> ℹ️ **PostgreSQL `JSONB` vs. SQLite `JSON` Note:**  
> For technical details on the underlying differences between SQLite JSON text storage and PostgreSQL binary `JSONB` (including GIN inverted indexing and query execution), see [Database Schema Specification §2.2.1](file:///Users/pascal/git-plgah/fairwddi-lifecycle/deliverables/database.md#221-in-depth-comparison-postgresql-jsonb-vs-sqlite-json).

---

## 5. Python API Quick Reference

All CLI commands correspond directly to reusable Python functions in `fairwddi`:

```python
# 1. Export PostgreSQL DDL
from fairwddi.db import export_postgres_ddl
sql = export_postgres_ddl("custom_schema.sql")

# 2. Seed Database Programmatically
from fairwddi.db import seed_sample_data
summary = seed_sample_data(reset=True)
print(f"Seeded {summary['instance_variables']} instance variables.")
```
