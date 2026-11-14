Production Deployment & Maintenance
===================================

This section outlines recommendations for deploying FAIRwDDI into production environments at CDSP or partner institutions, configuring web services, and performing routine database maintenance.

Service Architecture
--------------------

In production, FAIRwDDI is deployed as an ASGI web application behind a high-performance reverse proxy (e.g., Nginx, Caddy, or Kong):

.. code-block:: text

   [ Client Browser / Portal ]
                │
                ▼
      [ Nginx Reverse Proxy ]
         │ (SSL, Static Cache, Rate Limiting)
         ▼
     [ Gunicorn / Uvicorn Workers ]
         │ (Python 3.12+ ASGI Workers)
         ▼
     [ FAIRwDDI Application ]
         │ (psycopg v3 Connection Pool)
         ▼
     [ PostgreSQL 17 Cluster ]
       (ICU Collation, GIN Indexes, JSONB)

ASGI Application Server Setup
-----------------------------

We recommend running Uvicorn workers managed by Gunicorn for process supervision and graceful worker restarts.

Example Gunicorn Configuration (``gunicorn.conf.py``):

.. code-block:: python

   import multiprocessing

   bind = "127.0.0.1:8000"
   workers = multiprocessing.cpu_count() * 2 + 1
   worker_class = "uvicorn.workers.UvicornWorker"
   timeout = 120
   keepalive = 5
   accesslog = "/var/log/fairwddi/access.log"
   errorlog = "/var/log/fairwddi/error.log"
   loglevel = "info"

Systemd Service Unit (``/etc/systemd/system/fairwddi.service``):

.. code-block:: ini

   [Unit]
   Description=FAIRwDDI Lifecycle API Service
   After=network.target postgresql.service

   [Service]
   Type=notify
   User=fairwddi
   Group=fairwddi
   WorkingDirectory=/opt/fairwddi-lifecycle
   EnvironmentFile=/opt/fairwddi-lifecycle/.env
   ExecStart=/opt/fairwddi-lifecycle/.venv/bin/gunicorn -c gunicorn.conf.py fairwddi.api.server:app
   ExecReload=/bin/kill -s HUP $MAINPID
   KillMode=mixed
   TimeoutStopSec=30
   PrivateTmp=true
   Restart=always

   [Install]
   WantedBy=multi-user.target

Nginx Reverse Proxy Configuration
---------------------------------

Example Nginx virtual host snippet:

.. code-block:: nginx

   server {
       listen 443 ssl http2;
       server_name request-api.cdsp.sciencespo.fr;

       ssl_certificate /etc/letsencrypt/live/request-api.cdsp.sciencespo.fr/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/request-api.cdsp.sciencespo.fr/privkey.pem;

       client_max_body_size 50M;

       # Static website documentation & portal
       location /docs/ {
           alias /opt/fairwddi-lifecycle/docs/;
           try_files $uri $uri/ /docs/index.html;
           expires 7d;
           add_header Cache-Control "public, no-transform";
       }

       # REST API & Interactive Explorer
       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
           proxy_read_timeout 180s;
       }
   }

Database Maintenance & Index Optimization
-----------------------------------------

1. GIN Index Vacuuming
~~~~~~~~~~~~~~~~~~~~~~

High-volume insertions into tables with JSONB GIN indexes create pending list entries that require periodic vacuuming:

.. code-block:: sql

   -- Run weekly or after large batch ingestions
   VACUUM (ANALYZE, VERBOSE) request_ddi_representedvariable;
   VACUUM (ANALYZE, VERBOSE) request_ddi_questionitem;
   VACUUM (ANALYZE, VERBOSE) request_ddi_urnregistry;

2. ICU Collation Refresh
~~~~~~~~~~~~~~~~~~~~~~~~

When upgrading the host ICU library, run the following command to update collation versions without downtime:

.. code-block:: sql

   ALTER COLLATION "und-x-icu" REFRESH VERSION;

Backup and Disaster Recovery
----------------------------

1. Automated Daily Logical Dump
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run logical backups using ``pg_dump`` with directory format for parallel dumping:

.. code-block:: bash

   pg_dump -Fd -j 4 -h localhost -U fairwddi_user fairwddi_db -f /backups/fairwddi_$(date +%Y%m%d).dump

2. Point-in-Time Recovery (PITR)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For production deployments, enable continuous WAL archiving in ``postgresql.conf``:

.. code-block:: ini

   wal_level = replica
   archive_mode = on
   archive_command = 'test ! -f /mnt/wal_archive/%f && cp %p /mnt/wal_archive/%f'
