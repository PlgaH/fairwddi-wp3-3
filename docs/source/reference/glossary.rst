DDI Canonical Terminology Glossary
==================================

To maintain strict alignment with DDI 4.0, DDI-CDI, DDI-Lifecycle 3.3, and CESSDA European archive guidelines, FAIRwDDI adopts canonical DDI entity naming across the database schema, API, and documentation.

The table below maps legacy ReQuest model names to the canonical DDI names:

.. list-table::
   :widths: 25 25 15 35
   :header-rows: 1

   * - Current ReQuest Name
     - Target DDI Model Name
     - Layer
     - Description & Rationale
   * - ``ConceptualVariable``
     - **ConceptualVariable**
     - Concept
     - Abstract measurement concept (e.g., "Left-Right Political Placement"). Already aligned.
   * - ``RepresentedVariable``
     - **RepresentedVariable**
     - Representation
     - Question formulation + response code list. Decoupled from physical survey column bindings.
   * - *(embedded in RV)*
     - **QuestionItem**
     - Representation
     - Standalone, reusable question text with interviewer instructions. Extracted from ``RepresentedVariable.question_text``.
   * - ``Category``
     - **Category**
     - Representation
     - Human-readable response text label (e.g., "Strongly Agree"). Stores multilingual JSONB.
   * - *(embedded in Category)*
     - **CodeList** / **CodeItem**
     - Representation
     - Named sets of response codes; decouples numerical codes (e.g., ``1``, ``2``) from category labels.
   * - *(new)*
     - **VariableGroup**
     - Organization
     - Thematic grouping of variables within a study (e.g., "Demographics", "Political Attitudes").
   * - ``Survey``
     - **StudyUnit**
     - Dataset
     - A specific survey wave, study cycle, or dataset collection.
   * - ``BindingSurveyRepresentedVariable``
     - **InstanceVariable**
     - Dataset
     - Physical realization of a variable in a specific survey column or data file position.
   * - *(new)*
     - **DataFile** / **DataFileVariable**
     - Dataset
     - Technical file manifestation (CSV, Parquet, SPSS, Stata) and physical column position.
   * - *(new)*
     - **Concept** / **ConceptScheme**
     - Concept
     - Vocabulary-agnostic controlled taxonomy concepts (e.g., CESSDA ELSST or DDI-CV terms).
   * - *(new)*
     - **UrnRegistry**
     - Infrastructure
     - Central supertype master table guaranteeing universal referential integrity across all 30 entities.
