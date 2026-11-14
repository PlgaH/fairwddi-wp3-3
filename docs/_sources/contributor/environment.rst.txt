Development Environment Setup
==============================

FAIRwDDI uses modern Python packaging tooling centered on `uv <https://astral.sh/uv>`_ and `Hatch <https://hatch.pypa.io/>`_.

Prerequisites
-------------

* **Python 3.12+**
* **Git 2.40+**
* **uv**: Install via ``curl -LsSf https://astral.sh/uv/install.sh | sh``

Cloning and Virtual Environment
-------------------------------

.. code-block:: bash

   # 1. Clone repository
   git clone https://github.com/DataArtifex/fairwddi-lifecycle.git
   cd fairwddi-lifecycle

   # 2. Synchronize virtual environment with dev and docs dependencies
   uv sync --all-groups

   # 3. Verify Python version in active environment
   uv run python --version
   # Should report Python 3.12.x or higher

Pre-commit Hooks
----------------

We recommend installing pre-commit hooks to catch formatting and linting errors before pushing:

.. code-block:: bash

   uv run pre-commit install

Running Quick Sanity Checks
---------------------------

Ensure your environment is functioning properly by executing the test suite and linter:

.. code-block:: bash

   # Run test suite
   uv run pytest

   # Run Ruff formatting and linting
   uv run ruff check .
   uv run ruff format --check .

   # Run static type checker
   uv run pyrefly check src tests
