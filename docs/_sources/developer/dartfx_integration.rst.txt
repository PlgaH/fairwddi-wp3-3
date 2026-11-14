Data Artifex DDI Toolkit Integration
======================================

FAIRwDDI builds directly upon the **Data Artifex DDI Toolkit** (``dartfx-ddi``) for standards parsing, model crosswalks, and XML stream transformations.

Overview of dartfx-ddi
----------------------

The Data Artifex DDI Toolkit is a specialized Python framework providing:
* **DDI-Codebook 2.6**: Pydantic models and parser for survey codebooks.
* **DDI-CDI 1.1**: Pydantic models generated from official UML specs with an Assistant Framework.
* **DDI-Lifecycle 3.3 to DDI 4.0 RC1**: Low-memory fragment streaming with automatic XML schema crosswalks.
* **Harmonizer**: Multi-attribute variable comparison, unit conversion, and candidate blocking.

DDI-Lifecycle Fragment Streaming
--------------------------------

In ``fairwddi.ingest``, DDI-Lifecycle 3.3 files are parsed via ``ddilifecycle.stream_ddil``:

.. code-block:: python

   from dartfx.ddi import ddilifecycle

   # Streams DDI 3.3 XML fragments, crosswalking them into DDI 4.0 RC1 Pydantic models
   for resource in ddilifecycle.stream_ddil("study_33.xml", resource_types=["QuestionItem", "Variable"]):
       print(f"Resource Type: {type(resource).__name__}")
       print(f"URN: {resource.urn}")
       print(f"Name: {resource.name}")

Under-the-Hood Normalization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``dartfx-ddi`` handles the following schema discrepancies transparently during streaming:
1. **Namespace Unification**: Maps differing DDI 3.2 and 3.3 namespace variants to a uniform internal representation.
2. **Substitution Group Mapping**: Resolves polymorphic XML substitution groups into concrete model classes.
3. **Instruction Wrapping**: Normalizes interviewer instructions into standardized ``InterviewerInstruction`` objects.
4. **URN Synthesis**: Synthesizes RFC 3986-compliant URNs when legacy fragments lack full identifiers.

Multilingual Codebook Merging
-----------------------------

When migrating legacy bilingual studies documented in separate DDI-Codebook files (e.g., French and English XMLs), FAIRwDDI leverages ``dartfx.ddi.ddicodebook.i18n``:

.. code-block:: python

   from dartfx.ddi.ddicodebook.i18n import assess_merge, execute_merge

   # 1. Assess translation discrepancies and generate a review plan
   plan = assess_merge("survey_fr.xml", "survey_en.xml", lang_canonical="fr", lang_translated="en")

   # 2. Execute merge to produce a unified bilingual DDI document
   merged_codebook = execute_merge("survey_fr.xml", "survey_en.xml", plan=plan, output_path="survey_bilingual.xml")

DDI-CDI Assistant Framework
---------------------------

For forward compatibility with DDI-CDI, FAIRwDDI integrates with ``dartfx.ddi.ddicdi.assistants.CdiClassAssistant``:

.. code-block:: python

   from dartfx.ddi.ddicdi import model_1_1_0 as cdi_model
   from dartfx.ddi.ddicdi.assistants import CdiClassAssistant

   # Create dataset and variables with automated DDI URI management
   dataset = CdiClassAssistant.create(cdi_model.DataSet, name="ELIPSS_Wave_1")
   var_age = CdiClassAssistant.create(cdi_model.InstanceVariable, name="AGE")
   dataset.add_variable(var_age)

   # Validate against DDI-CDI SHACL shapes
   from dartfx.ddi.ddicdi.utils import shacl_validate_ddi_cdi
   is_valid, report_text = shacl_validate_ddi_cdi(dataset)
