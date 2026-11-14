The Ingestion Engine (fairwddi.ingest)
=======================================

The ``fairwddi.ingest`` package provides an extensible, streaming ETL pipeline designed to import heterogeneous social science survey files into the standard-agnostic database model.

Package Architecture
--------------------

The package is organized into modular components:

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Module
     - Primary Responsibility
   * - ``detector.py``
     - Inspects file headers to detect XML namespaces and DDI format/version.
   * - ``streaming.py``
     - Memory-efficient fragment streaming using ``lxml.etree.iterparse``.
   * - ``profiles.py``
     - Specification profiles and mapping rules tailored for ReQuest.
   * - ``preflight.py``
     - Static validation, namespace checks, and encoding verification.
   * - ``comparator.py``
     - Compares in-memory XML fragments against existing database records.
   * - ``plan.py``
     - Generates structured YAML/JSON Ingestion Execution Plans.
   * - ``loader.py``
     - Transactional batch persistence into PostgreSQL 17.
   * - ``pipeline.py``
     - End-to-end orchestrator binding all stages together.
   * - ``harmonizer.py``
     - Multilingual dictionary merging and cross-wave variable clustering.

Format Detection (detector.py)
------------------------------

Before parsing, ``fairwddi.ingest.detector`` inspects the root element and namespace declarations without reading the entire document into memory:

.. code-block:: python

   from fairwddi.ingest.detector import detect_ddi_format

   format_info = detect_ddi_format("survey.xml")
   print(format_info.format_name)    # e.g., "DDI-Lifecycle"
   print(format_info.version)        # e.g., "3.3"
   print(format_info.adapter_class)  # e.g., DDILifecycleAdapter

Supported Ingestion Formats:
* **DDI-Lifecycle 3.3 / 3.2**: Streaming fragment parsing into DDI 4.0 Pydantic models.
* **DDI-Codebook 2.6 / 2.5**: Classic survey documentation, variable lists, and codebooks.
* **DDI 4.0 RC1 (COGS)**: Modern model-based XML / JSON representations.

Streaming XML Iteration (streaming.py)
--------------------------------------

Traditional DOM-based XML parsers (e.g., BeautifulSoup or standard `ElementTree`) load the entire document into RAM. A 500 MB DDI-Lifecycle survey with thousands of variables can consume 4+ GB of RAM, causing out-of-memory crashes.

FAIRwDDI employs low-memory streaming with `lxml.etree.iterparse`:

.. code-block:: python

   from fairwddi.ingest.streaming import stream_ddi_fragments

   # Streams resources one by one; clears elements from memory immediately
   for fragment in stream_ddi_fragments("large_survey.xml", tag_filter=["QuestionItem", "Variable"]):
       process_fragment(fragment)
       fragment.element.clear()

Comparator and Execution Plan (comparator.py & plan.py)
-------------------------------------------------------

The comparator evaluates extracted entities against PostgreSQL using the 4-phase cascade:

.. code-block:: python

   from fairwddi.ingest.comparator import DatabaseComparator
   from fairwddi.ingest.plan import IngestionPlan

   comparator = DatabaseComparator()
   plan: IngestionPlan = comparator.compare_batch(extracted_fragments)

   print(f"Proposed Creates: {len(plan.creates)}")
   print(f"Proposed Links: {len(plan.links)}")
   print(f"Quarantined Items: {len(plan.quarantines)}")

Batch Transaction Loading (loader.py)
-------------------------------------

Execution plans are applied inside an atomic PostgreSQL transaction:

.. code-block:: python

   from django.db import transaction
   from fairwddi.ingest.loader import BatchLoader

   loader = BatchLoader()
   with transaction.atomic():
       receipt = loader.load_plan(plan)

   print(f"Batch successfully executed: {receipt.batch_id}")
