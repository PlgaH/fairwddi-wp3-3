Testing Guide & Practices
==========================

FAIRwDDI enforces rigorous automated testing across models, schemas, ingestion pipelines, and REST API endpoints.

Testing Stack
-------------

* **Test Runner**: `pytest <https://docs.pytest.org/>`_ (version ≥ 8.0).
* **Django Integration**: `pytest-django <https://pytest-django.readthedocs.io/>`_.
* **Coverage**: `pytest-cov <https://pytest-cov.readthedocs.io/>`_.
* **Test Database**: In-memory SQLite for rapid unit testing; optional local PostgreSQL 17 for integration verification.

Running Tests
-------------

Execute the test suite via ``uv``::

   # Run all tests
   uv run pytest

   # Run with verbose output and stop on first failure
   uv run pytest -v -x

   # Run a specific test module or test function
   uv run pytest tests/test_ingest_pipeline.py
   uv run pytest tests/test_cascade.py -k "test_variable_cascade"

   # Run with coverage report
   uv run pytest --cov=fairwddi --cov-report=term-missing

Isolated SQLite Test Configuration
----------------------------------

Unit tests run against an in-memory SQLite database configured in ``tests/conftest.py``:

.. code-block:: python

   import django
   from django.conf import settings
   from django.core.management import call_command

   def pytest_configure() -> None:
       if not settings.configured:
           settings.configure(
               SECRET_KEY="fairwddi-test-secret-key",
               INSTALLED_APPS=[
                   "django.contrib.contenttypes",
                   "django.contrib.auth",
                   "fairwddi",
               ],
               DATABASES={
                   "default": {
                       "ENGINE": "django.db.backends.sqlite3",
                       "NAME": ":memory:",
                   }
               },
               USE_TZ=True,
           )
           django.setup()
           call_command("migrate", interactive=False, verbosity=0)

This allows developers and CI pipelines to run the full test suite in under 5 seconds without running a PostgreSQL service.

Testing Ingestion & Streaming
-----------------------------

When writing tests for XML parsing or format adapters:
* Place sample XML snippets or fixtures in ``tests/data/``.
* Use streaming parsers rather than loading large documents in memory.
* Validate that `UrnRegistry` entries are created and deleted with cascading precision.

Example Test Case:

.. code-block:: python

   import pytest
   from fairwddi.models import QuestionItem, UrnRegistry

   @pytest.mark.django_db
   def test_question_item_urn_registry_lifecycle():
       urn = "urn:ddi:fr.cdsp:QI_TEST:1.0"
       q = QuestionItem.objects.create(
           urn=urn,
           name="Q_TEST",
           question_text={"fr": "Test question en français", "en": "Test question in English"}
       )

       # Verify auto-registration in UrnRegistry
       reg = UrnRegistry.objects.get(urn=urn)
       assert reg.resource_type == "QuestionItem"
       assert reg.agency == "fr.cdsp"

       # Verify cascade deletion
       q.delete()
       assert not UrnRegistry.objects.filter(urn=urn).exists()
