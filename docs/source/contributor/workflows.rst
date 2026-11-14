Development Workflows & Pull Requests
========================================

This section describes our Git branching strategy, pull request (PR) lifecycle, and documentation build procedures.

Git Branching Strategy
----------------------

* **Main Branch** (``main``): Always stable and deployable.
* **Feature Branches**: Branch from ``main`` using descriptive prefixes:
  * ``feat/<feature-name>``: New features or models
  * ``fix/<issue-name>``: Bug fixes or patch corrections
  * ``docs/<topic>``: Documentation additions or updates
  * ``refactor/<topic>``: Code cleanups without behavior changes

Commit Message Guidelines
-------------------------

We follow the `Conventional Commits <https://www.conventionalcommits.org/>`_ specification:

.. code-block:: text

   <type>(<scope>): <short description>

   [optional body]

   [optional footer]

Examples:
* ``feat(ingest): add streaming support for DDI-Lifecycle 3.3 sequence constructs``
* ``fix(urn): correct agency validation regex in parse_urn``
* ``docs(admin): add guide for PostgreSQL 17 ICU collation upgrades``

Pull Request Checklist
----------------------

Before opening or requesting review on a Pull Request, ensure:

1. **Tests Pass**: ``uv run pytest`` succeeds with zero failures.
2. **Linting & Formatting Clean**: ``uv run ruff check .`` and ``uv run ruff format --check .`` report no violations.
3. **Type Checking Succeeded**: ``uv run pyrefly check src tests`` returns zero errors.
4. **Documentation Built & Deployed**: Documentation builds cleanly without warnings (see below).
5. **Zero Data Loss**: Any migration changes do not drop columns or tables containing production metadata.

Building Documentation Locally
------------------------------

To build and preview the Sphinx documentation locally:

.. code-block:: bash

   # Option 1: Standard Sphinx build to docs/build/html
   uv run sphinx-build -b html docs/source docs/build/html

   # Option 2: Deploy Sphinx HTML directly under docs/ for the website
   uv run sphinx-build -d docs/build/doctrees -b html docs/source docs

   # Option 3: Using Hatch
   hatch run docs:build
   hatch run docs:deploy

   # Serve locally to inspect
   python -m http.server -d docs 8000
   # Open http://localhost:8000/docs/ in your browser
