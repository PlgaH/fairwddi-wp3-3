Administrator Guide
===================

This guide covers operational instructions for deploying, configuring, maintaining, and monitoring the **FAIRwDDI Lifecycle** platform. It is intended for DevOps engineers, database administrators, and technical archivists.

Key Operational Responsibilities
--------------------------------

1. **System Provisioning**: Installing Python 3.12+ runtimes, provisioning PostgreSQL 17 clusters with ICU collations (``und-x-icu``), and configuring GIN/JSONB extensions.
2. **Environment Management**: Setting up and securing environment secrets (``.env``), database credentials, API access tokens, and logging configurations.
3. **Database Maintenance**: Running schema migrations, loading external SKOS taxonomies (CESSDA ELSST), vacuuming high-throughput GIN indexes, and orchestrating database backups.
4. **ETL Pipeline Operations**: Monitoring batch XML ingestions, reviewing automated quarantine records, validating execution plans, and inspecting audit receipts.
5. **API & Service Monitoring**: Deploying ASGI servers (Uvicorn / Gunicorn), monitoring response latency, and inspecting system event logs.

Guide Outline
-------------

.. toctree::
   :maxdepth: 2

   architecture
   installation
   cli_operations
   ingestion_ops
   deployment
