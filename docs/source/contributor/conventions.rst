Coding Conventions & Standards
==============================

All contributions must adhere to the project's coding standards, type annotation rules, and architectural guidelines.

Python Stack & Tooling
----------------------

* **Language**: Python 3.12+ (strictly required).
* **Package Manager**: ``uv`` and ``hatch``.
* **Linter & Formatter**: ``ruff`` (configuration in ``pyproject.toml``).
* **Type Checker**: ``pyrefly`` (strict static typing).
* **Validation & Schemas**: ``pydantic`` v2.
* **CLI Framework**: ``typer`` + ``rich``.
* **API Layer**: ``django-ninja``.

Code Formatting & Linting (Ruff)
--------------------------------

* **Line Length**: 100 characters max.
* **Imports**: Grouped and sorted automatically by Ruff (isort rules).
* Run formatting before every commit:

.. code-block:: bash

   uv run ruff check --fix .
   uv run ruff format .

Type Annotations & Static Typing
--------------------------------

* Type hints are mandatory on all public functions, classes, and method signatures.
* Use standard modern Python syntax (PEP 585 / PEP 604):
  * Prefer ``list[str]`` over ``typing.List[str]``
  * Prefer ``dict[str, Any]`` over ``typing.Dict[str, Any]``
  * Prefer ``str | None`` over ``typing.Optional[str]``
* Verify types with Pyrefly:

.. code-block:: bash

   uv run pyrefly check src tests

Django Migrations & Zero-Data-Loss
----------------------------------

When modifying models:
1. **Zero Data Loss**: Renames of existing models or columns must use ``migrations.RenameModel`` and ``migrations.RenameField``, never a drop-and-recreate sequence.
2. **Deterministic Foreign Keys**: All child entity tables must reference ``request_ddi_urnregistry(urn) ON DELETE CASCADE``.
3. **Multilingual JSONB**: All human-facing text fields must use PostgreSQL ``JSONB`` storing ISO 639-1 language keys.
4. **Always Test Migrations**: Verify that migrations can apply cleanly on fresh SQLite and PostgreSQL environments:

.. code-block:: bash

   uv run fairwddi db init

DDI Naming Conventions
----------------------

Follow standard DDI terminology across all code and documentation:

.. list-table::
   :widths: 30 30 40
   :header-rows: 1

   * - Canonical Target DDI Name
     - Legacy ReQuest Name
     - Layer
   * - ``ConceptualVariable``
     - ``ConceptualVariable``
     - Concept Layer
   * - ``RepresentedVariable``
     - ``RepresentedVariable``
     - Representation Layer
   * - ``QuestionItem``
     - *(Embedded in RV)*
     - Representation Layer
   * - ``Category``
     - ``Category``
     - Representation Layer
   * - ``CodeList`` / ``CodeItem``
     - *(Embedded in Category)*
     - Representation Layer
   * - ``VariableGroup``
     - *(New entity)*
     - Organization Layer
   * - ``StudyUnit``
     - ``Survey``
     - Dataset Layer
   * - ``InstanceVariable``
     - ``BindingSurveyRepresentedVariable``
     - Dataset Layer
