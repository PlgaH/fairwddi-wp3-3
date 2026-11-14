Installation & Environment Setup
=================================

This section guides administrators through installing the FAIRwDDI package, configuring environment secrets, and provisioning the database.

Prerequisites
-------------

Ensure Python 3.12+ and `uv` are installed on your host system::

   curl -LsSf https://astral.sh/uv/install.sh | sh
   uv --version

Cloning and Virtual Environment
-------------------------------

Clone the repository and synchronize dependencies::

   git clone https://github.com/DataArtifex/fairwddi-lifecycle.git
   cd fairwddi-lifecycle

   # Synchronize virtual environment with frozen lockfile
   uv sync

Configuration (.env)
--------------------

FAIRwDDI uses `python-dotenv` to resolve settings from a local ``.env`` file. Copy the provided template::

   cp .env.example .env

Review and update the settings in ``.env``:

.. code-block:: ini

   # --------------------------------------------------------------------------
   # Core Application Settings
   # --------------------------------------------------------------------------
   DJANGO_SETTINGS_MODULE=fairwddi.db.config
   SECRET_KEY=replace-with-a-secure-random-secret-key-in-production
   DEBUG=False
   ALLOWED_HOSTS=localhost,127.0.0.1,api.cdsp.sciencespo.fr

   # --------------------------------------------------------------------------
   # Database Configuration (PostgreSQL 17)
   # --------------------------------------------------------------------------
   DATABASE_URL=postgresql://fairwddi_user:secure_password@localhost:5432/fairwddi_db

   # Alternatively, discrete variables:
   # DB_ENGINE=postgresql
   # DB_NAME=fairwddi_db
   # DB_USER=fairwddi_user
   # DB_PASSWORD=secure_password
   # DB_HOST=localhost
   # DB_PORT=5432

   # --------------------------------------------------------------------------
   # Ingestion & Normalization Settings
   # --------------------------------------------------------------------------
   FAIRWDDI_DEFAULT_AGENCY=fr.cdsp
   FAIRWDDI_CANONICAL_LANG=fr
   FAIRWDDI_QUARANTINE_ON_DRIFT=True
   FAIRWDDI_HASH_ALGORITHMS=sha256,blake3

   # --------------------------------------------------------------------------
   # Logging & Observability
   # --------------------------------------------------------------------------
   LOG_LEVEL=INFO
   LOG_FORMAT=json

Database Provisioning
---------------------

1. Create PostgreSQL User and Database
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run the following SQL commands on your PostgreSQL 17 cluster::

   CREATE USER fairwddi_user WITH PASSWORD 'secure_password';
   CREATE DATABASE fairwddi_db OWNER fairwddi_user ENCODING 'UTF8';
   GRANT ALL PRIVILEGES ON DATABASE fairwddi_db TO fairwddi_user;

2. Apply Database Migrations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Initialize the 30-model schema and the ``UrnRegistry`` supertype table using the CLI::

   uv run fairwddi db init

Alternatively, view or export the raw PostgreSQL DDL script for execution by an automated DBA pipeline::

   uv run fairwddi db export-ddl --output schema.sql

3. Load Controlled Vocabularies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Seed initial administrative taxonomies and load external CESSDA ELSST SKOS vocabularies::

   # Load basic seed data
   uv run fairwddi db seed

   # Load SKOS RDF/XML vocabulary (e.g., ELSST)
   uv run fairwddi vocab load-skos vocab/elsst_fr_en.rdf --vocabulary-name ELSST

Verifying Installation
----------------------

Verify that all tables, foreign keys, and registries are operational::

   uv run fairwddi db status

You should see output similar to::

   ┌────────────────────────────────────────────────────────┐
   │ FAIRwDDI Database Status Report                        │
   ├────────────────────────────────────────────────────────┤
   │ Engine:             PostgreSQL 17.2                    │
   │ Connection:         Active (fairwddi_db@localhost)     │
   │ UrnRegistry Count:  342 canonical URNs registered      │
   │ StudyUnit Count:    14 survey waves                    │
   │ Variables:          1,280 Represented / 4,110 Instance │
   │ Schema Status:      100% Aligned (0 pending)           │
   └────────────────────────────────────────────────────────┘
