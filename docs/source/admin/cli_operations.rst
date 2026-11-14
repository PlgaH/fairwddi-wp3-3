CLI Operational Reference
=========================

The ``fairwddi`` command-line interface (built with `Typer <https://typer.tiangolo.com/>`_ and `Rich <https://rich.readthedocs.io/>`_) is the primary management utility for database tasks, XML validation, ingestion planning, harmonizing variables, and serving the REST API.

Global Options
--------------

.. code-block:: bash

   fairwddi [OPTIONS] COMMAND [ARGS]...

   Options:
     --version       Show package version and exit.
     --help          Show help message and exit.

   Commands:
     info            Display runtime environment, database connection, and package details.
     db              Database initialization, status inspection, DDL export, and seeding.
     vocab           Controlled vocabulary and SKOS taxonomy administration.
     preflight       Static analysis and profile validation of incoming DDI XML files.
     compare         Batch comparison between XML files and database records.
     ingest          Execute, monitor, and rollback ingestion execution plans.
     harmonize       Interactive cross-survey variable clustering and harmonization.
     serve           Launch the ASGI REST API server with live Swagger documentation.

Database Management (``fairwddi db``)
-------------------------------------

Inspect, migrate, seed, and manage PostgreSQL schema state:

.. code-block:: bash

   # Check connection status, table counts, and pending migrations
   fairwddi db status

   # Apply all migrations and initialize the UrnRegistry
   fairwddi db init

   # Seed development / demonstration fixtures
   fairwddi db seed

   # Export raw PostgreSQL 17 DDL to a file
   fairwddi db export-ddl --output postgres_17_schema.sql

   # Wipe database (requires confirmation flag)
   fairwddi db wipe --confirm-irreversible-loss

   # Recreate database from scratch (wipe + init + seed)
   fairwddi db recreate --confirm-irreversible-loss

Vocabulary Administration (``fairwddi vocab``)
----------------------------------------------

Manage SKOS controlled vocabularies (e.g., CESSDA ELSST):

.. code-block:: bash

   # Check loaded vocabularies and concept counts
   fairwddi vocab check

   # Load SKOS RDF/XML file into the Concept and ConceptScheme tables
   fairwddi vocab load-skos /path/to/elsst_fr_en.rdf --vocabulary-name "ELSST" --agency "eu.cessda"

Preflight Analysis (``fairwddi preflight``)
-------------------------------------------

Validate DDI XML files before ingestion:

.. code-block:: bash

   # Inspect XML file encoding, namespaces, format version, and root elements
   fairwddi preflight check survey_wave_1.xml

   # Extract resource counts and profile characteristics
   fairwddi preflight profiles survey_wave_1.xml --output profile_report.json

   # Test upgrade crosswalks (e.g., DDI-Codebook 2.5 to 2.6 or DDI 3.3 to 4.0)
   fairwddi preflight upgrade legacy_codebook.xml --target-version 2.6

Ingestion Pipeline (``fairwddi ingest``)
----------------------------------------

Orchestrate safe, plan-based batch ingestion:

.. code-block:: bash

   # Step 1: Generate a non-destructive comparison plan against existing database
   fairwddi ingest plan survey_ddi33.xml --report-out survey_plan.yaml

   # Step 2: Review plan summary and proposed actions (Create, Link, Re-version, Quarantine)
   fairwddi ingest plan survey_ddi33.xml --dry-run

   # Step 3: Execute the plan transactionally
   fairwddi ingest execute survey_plan.yaml

   # List recent ingestion batches and receipts
   fairwddi ingest list --limit 10

   # Check detailed status of a specific batch receipt
   fairwddi ingest status <batch_id>

   # Rollback an ingestion batch cleanly
   fairwddi ingest undo <batch_id> --confirm

Harmonization (``fairwddi harmonize``)
--------------------------------------

Cluster, compare, and harmonize variables across studies:

.. code-block:: bash

   # Generate a harmonization plan proposing concept linkages
   fairwddi harmonize plan --threshold 0.85 --output harmonization_plan.yaml

   # Approve all high-confidence (>= 0.95) proposals automatically
   fairwddi harmonize approve-high harmonization_plan.yaml

   # Apply the approved harmonization linkages to the database
   fairwddi harmonize apply harmonization_plan.yaml

   # Elevate a RepresentedVariable to a new ConceptualVariable
   fairwddi harmonize elevate <rep_var_urn> --name "POL_ATTITUDE"

API Server (``fairwddi serve``)
-------------------------------

Start the ASGI web service running `django-ninja`::

   # Start server on default port (8000)
   fairwddi serve

   # Start with custom host, port, and auto-reload for development
   fairwddi serve --host 0.0.0.0 --port 8080 --reload
