The DDI Variable Cascade
========================

The **Variable Cascade** is the foundational structural pattern of modern statistical and social science metadata standards (DDI 4.0, DDI-CDI, DDI-Lifecycle 3.3, and UNECE GSIM).

It solves the fundamental problem of survey data harmonization: **decoupling abstract analytical concepts from specific question wordings and from physical dataset column locations.**

The Three Tiers of the Cascade
------------------------------

.. code-block:: text

   ┌────────────────────────────────────────────────────────┐
   │ CONCEPT LAYER                                          │
   │  ConceptualVariable (e.g., "Left-Right Placement")     │
   │  - Anchored to Controlled Vocabularies (ELSST / DDI-CV)│
   └───────────────────────────┬────────────────────────────┘
                               │ 1:N
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │ REPRESENTATION LAYER                                   │
   │  RepresentedVariable (Question + Standardized Codes)   │
   │  ├── QuestionItem (Interviewer instructions + text)    │
   │  └── CodeList / CodeItem / Category (Scale 1 to 10)    │
   └───────────────────────────┬────────────────────────────┘
                               │ 1:N
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │ DATASET LAYER                                          │
   │  InstanceVariable (Physical realization in a column)   │
   │  ├── StudyUnit (Survey wave, e.g., ESS Round 10)       │
   │  └── DataFile / DataFileVariable (Column position)     │
   └────────────────────────────────────────────────────────┘

Tier Definitions
----------------

1. ConceptualVariable (Concept Layer)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Definition**: An abstract measurement intent independent of any question text or scale.
* **Examples**: "Left-Right Political Orientation", "Monthly Net Income", "Educational Attainment".
* **Attributes**: ``name``, ``label``, ``description``, ``concept_urn``.
* **Controlled Vocabulary Anchoring**: Connected to a ``Concept`` (e.g., CESSDA ELSST term ``political attitudes``).

2. RepresentedVariable (Representation Layer)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Definition**: A reusable measurement specification combining a specific question formulation (``QuestionItem``) with a reusable set of valid responses (``CodeList``).
* **Question Decoupling**: In legacy ReQuest, question text was embedded in the variable. In FAIRwDDI, questions are standalone first-class entities (``QuestionItem``) reusable across variables and surveys.
* **Attributes**: ``question_item_urn``, ``code_list_urn``, ``value_domain``, ``concept_var_urn``.

3. InstanceVariable (Dataset Layer)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Definition**: The concrete realization of a variable in a specific survey dataset or data file column.
* **Examples**: Column ``V104`` in survey wave ``FR_ELIPSS_2024``.
* **Attributes**: ``study_unit_urn``, ``represented_var_urn``, ``physical_datatype``, ``missing_values``.

Standards Crosswalk
-------------------

.. list-table::
   :widths: 25 25 25 25
   :header-rows: 1

   * - FAIRwDDI Model
     - GSIM
     - DDI-CDI 1.0
     - DDI-Lifecycle 3.3
   * - ``ConceptualVariable``
     - Conceptual Variable
     - ``ConceptualVariable``
     - ``ConceptualVariable``
   * - ``RepresentedVariable``
     - Represented Variable
     - ``RepresentedVariable``
     - ``RepresentedVariable``
   * - ``InstanceVariable``
     - Instance Variable
     - ``InstanceVariable``
     - ``Variable``
   * - ``QuestionItem``
     - Question
     - ``QuestionItem``
     - ``QuestionItem``
   * - ``CodeList``
     - Node Set / Code List
     - ``CodeList``
     - ``CodeList``

ORM Traversal Examples
----------------------

Traversing from Dataset Column up to Abstract Concept::

   from fairwddi.models import InstanceVariable

   # Fetch instance variable for a column in a specific wave
   inst_var = InstanceVariable.objects.select_related(
       "study_unit",
       "represented_variable__question_item",
       "represented_variable__conceptual_variable"
   ).get(study_unit__name="ELIPSS_2024", name="POL_ORIENT")

   print(f"Dataset Column: {inst_var.name} in {inst_var.study_unit.name}")
   rep_var = inst_var.represented_variable
   print(f"Question Text: {rep_var.question_item.question_text.get('fr')}")
   print(f"Concept: {rep_var.conceptual_variable.label.get('fr')}")

Finding All Survey Questions Measuring the Same Concept::

   from fairwddi.models import ConceptualVariable

   concept = ConceptualVariable.objects.get(name="POLITICAL_PLACEMENT")

   # Retrieve all distinct survey waves asking this conceptual variable
   surveys = set()
   for rep_var in concept.represented_variables.all():
       for inst_var in rep_var.instance_variables.all():
           surveys.add(inst_var.study_unit.name)

   print(f"Surveys measuring {concept.name}: {', '.join(surveys)}")
