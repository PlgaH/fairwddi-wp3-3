REST API & Interactive Explorer (fairwddi.api)
==============================================

The ``fairwddi.api`` package provides a modern, asynchronous REST API built with `Django Ninja <https://django-ninja.rest-framework.com/>`_ and `Pydantic v2 <https://docs.pydantic.dev/>`_.

Key Advantages of Django Ninja
------------------------------

* **High Performance**: Built on ASGI and type-hinted Python functions for near-FastAPI speed.
* **Automatic OpenAPI 3.0**: Interactive Swagger and ReDoc documentation generated automatically from Python type hints.
* **Strict Validation**: Request and response payloads are validated using Pydantic v2 schemas.

API Architecture
----------------

.. code-block:: text

   fairwddi/api/
   ├── router.py         # Main NinjaAPI instance and route attachments
   ├── urls.py           # Django URL routing
   ├── views.py          # Endpoint route handlers
   ├── schemas.py        # Pydantic v2 API input/output models
   ├── server.py         # ASGI application entrypoint for Uvicorn
   └── explorer_html.py  # Standalone interactive SVG/Canvas database explorer

Endpoints Overview
------------------

.. list-table::
   :widths: 15 30 55
   :header-rows: 1

   * - HTTP Method
     - Endpoint
     - Description
   * - ``GET``
     - ``/api/v1/health``
     - System health check, PostgreSQL connectivity, and table counts.
   * - ``GET``
     - ``/api/v1/models``
     - Metadata schema definitions for all 30 DDI models.
   * - ``GET``
     - ``/api/v1/cascade``
     - Explore the 3-tier variable cascade for any concept or variable.
   * - ``GET``
     - ``/api/v1/questions``
     - Search and filter multilingual ``QuestionItem`` records.
   * - ``GET``
     - ``/api/v1/variables``
     - Search ``RepresentedVariable`` and ``InstanceVariable`` entities.
   * - ``POST``
     - ``/api/v1/ingest/preflight``
     - Upload and validate an XML file before starting ingestion.
   * - ``GET``
     - ``/explorer``
     - Full-screen interactive visual explorer of the 28 core database models.

Example Endpoint Implementation
-------------------------------

.. code-block:: python

   from ninja import NinjaAPI, Router
   from fairwddi.api.schemas import QuestionOut, HealthResponse
   from fairwddi.models import QuestionItem

   api = NinjaAPI(
       title="FAIRwDDI Lifecycle API",
       version="1.0.0",
       description="Standard-agnostic DDI API for the Sciences Po CDSP ReQuest Question Bank"
   )

   @api.get("/questions", response=list[QuestionOut])
   def list_questions(request, query: str = None, lang: str = "fr", limit: int = 50):
       qs = QuestionItem.objects.all()
       if query:
           qs = qs.filter(**{f"question_text__{lang}__icontains": query})
       return qs[:limit]

Interactive Database Explorer
-----------------------------

The API bundles a standalone, zero-dependency browser application in ``fairwddi.api.explorer_html``.

* Accessible at ``http://localhost:8000/explorer``
* Visualizes the complete 28-model architecture as an interactive node graph with pan, zoom, search, node inspection, and layer filtering.
* Renders using native SVG and Canvas without external heavy JavaScript framework dependencies.
