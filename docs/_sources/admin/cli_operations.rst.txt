CLI Operational Reference
=========================

The ``fairwddi`` command-line interface (built with `Typer <https://typer.tiangolo.com/>`_ and `Rich <https://rich.readthedocs.io/>`_) provides database administration, preflight inspection, pure deterministic import, context group curation, three-layer read-only comparison, policy-driven harmonization, and the ASGI REST API server.

Global Options
--------------

.. code-block:: bash

   fairwddi [OPTIONS] COMMAND [ARGS]...

   Options:
     --version, -v   Show package version and exit.
     --help          Show help message and exit.

   Commands:
     db              Database initialization, vocabulary loading, wipe, and DDL export.
     preflight       Preflight readiness checks, profile QA, and DDI-C -> DDI-L upgrades.
     import          Deterministic metadata import (``fairwddi import <file>`` + subcommands).
     group           Curate and inspect reusable DDI resource Groups (canonical URN + slug).
     compare         Read-only two-set, three-layer comparison (syntactic, semantic, conceptual).
     harmonize       Plan, approve, execute, and undo comparison-driven harmonization.
     serve / ui      Launch the ASGI REST API server and Question Bank Explorer.

Database Management (``fairwddi db``)
-------------------------------------

.. code-block:: bash

   fairwddi db status
   fairwddi db init
   fairwddi db export-ddl --output postgres_17_schema.sql
   fairwddi db load-vocab /path/to/elsst.ttl --vocabulary ELSST --levels 2
   fairwddi db check-vocab

Preflight Analysis (``fairwddi preflight``)
-------------------------------------------

.. code-block:: bash

   fairwddi preflight check survey_wave_1.xml --profile request
   fairwddi preflight upgrade legacy_codebook.xml --format ddi4-json --category-scheme-mode per_codelist
   fairwddi preflight profiles

Deterministic Import (``fairwddi import``)
------------------------------------------

Import DDI-Codebook or DDI-Lifecycle files into ReQuest core tables with **zero cross-study harmonization**:

.. code-block:: bash

   # Direct one-command import (DDI-C upgraded to DDI 4.0 automatically)
   fairwddi import survey_wave_1.xml --category-scheme-mode per_codelist

   # Plan-first dry-run workflow
   fairwddi import plan survey_ddi33.xml --output-dir ./import_out
   fairwddi import execute ./import_out/survey_ddi33.import.plan.yaml

   # Inspect and roll back batches
   fairwddi import list --limit 10
   fairwddi import status 42
   fairwddi import undo 42

Context Groups (``fairwddi group``)
-----------------------------------

.. code-block:: bash

   fairwddi group create "ESS France Series" --slug ess-fr --type longitudinal_series \
     --member urn:ddi:fr.cdsp:su_ess_w1:1.0.0 --member urn:ddi:fr.cdsp:su_ess_w2:1.0.0
   fairwddi group list
   fairwddi group show ess-fr
   fairwddi group add ess-fr --member urn:ddi:fr.cdsp:su_ess_w3:1.0.0

Three-Layer Comparison (``fairwddi compare``)
---------------------------------------------

.. code-block:: bash

   fairwddi compare configs
   fairwddi compare init-config my_compare.yaml --preset default

   fairwddi compare run \
     --source batch:42 \
     --target group:ess-fr \
     --level syntactic --level semantic \
     --type QuestionItem --type RepresentedVariable \
     --output-dir ./compare_out

Harmonization (``fairwddi harmonize``)
--------------------------------------

.. code-block:: bash

   # Plan harmonization (all items pending manual review by default)
   fairwddi harmonize plan ./compare_out/compare-abc12345.comparison.yaml --output-dir ./harm_out

   # Plan and auto-approve qualifying high-tier matches in one step
   fairwddi harmonize plan ./compare_out/compare-abc12345.comparison.yaml --approve-high --output-dir ./harm_out

   # Execute approved actions atomically
   fairwddi harmonize execute ./harm_out/harmonize-abc12345.harmonize.plan.yaml

   # Manual creation, linking, and EventLog rollback
   fairwddi harmonize create -s <src1_urn> -s <src2_urn> --name "Trust in Institutions"
   fairwddi harmonize link -s <wave3_urn> --into <harmonized_target_urn>
   fairwddi harmonize undo <job_id>

API Server (``fairwddi serve``)
-------------------------------

.. code-block:: bash

   fairwddi serve --host 127.0.0.1 --port 8000 --open
