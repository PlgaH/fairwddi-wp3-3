Multilingual JSONB Architecture
=================================

European social science archives (such as CESSDA partners and Sciences Po CDSP) require native, robust support for multi-language surveys. Questions, instructions, and category labels frequently exist in multiple official languages (e.g., French and English).

JSONB Data Model
----------------

FAIRwDDI represents all descriptive textual fields (``label``, ``description``, ``definition``, ``question_text``, ``instruction_text``) as PostgreSQL ``JSONB`` objects keyed by ISO 639-1 two-letter language codes:

.. code-block:: json

   {
     "fr": "Quel est votre niveau d'études le plus élevé ?",
     "en": "What is the highest level of education you have completed?"
   }

Benefits over Traditional Approaches:
* **No Table Bloat**: Avoids creating separate translation tables with expensive joins.
* **Schema Flexibility**: Any language can be added dynamically without running DDL schema migrations.
* **Deterministic Serialization**: Keys are sorted canonically before computing cryptographic content hashes.

String Normalization Pipeline
-----------------------------

Before saving or hashing any string, text passes through ``fairwddi.utils.normalize_string.normalize_string``:

1. **Unicode NFKC Decomposition & Recomposition**: Resolves visual duplicates (such as full-width characters, ligature forms like ``œ`` vs ``oe``, and accented combinations).
2. **French Typographical Punctuation Rules**:
   * Replaces straight quotes (``"``, ``'``) with standardized characters.
   * Inserts non-breaking spaces before two-part punctuation marks (``:``, ``;``, ``?``, ``!``, ``»``) and after ``«``.
3. **Whitespace Collapsing**: Collapses multiple whitespace characters and trims leading/trailing spaces.

.. code-block:: python

   from fairwddi.utils.normalize_string import normalize_string

   raw = "Êtes-vous d'accord ?  "
   clean = normalize_string(raw, lang="fr")
   # Result: "Êtes-vous d'accord\xa0?"

Querying Multilingual Fields
----------------------------

1. Django ORM Key Transforms (KT)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Django provides direct access to JSONB keys via double-underscore syntax:

.. code-block:: python

   from fairwddi.models import QuestionItem

   # Filter by French question text
   questions = QuestionItem.objects.filter(
       question_text__fr__icontains="politique"
   )

   # Filter with fallback
   results = QuestionItem.objects.filter(
       models.Q(question_text__fr__isnull=False) | models.Q(question_text__en__isnull=False)
   )

2. PostgreSQL JSONPath Queries
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For complex multi-language filtering, native JSONPath operators leverage GIN indexes:

.. code-block:: sql

   -- Find questions where either French or English text contains 'income' or 'revenu'
   SELECT urn, name, question_text
   FROM request_ddi_questionitem
   WHERE question_text @? '$.* ? (@ like_regex "(?i)revenu|income")';

PostgreSQL 17 ICU Collations
----------------------------

Sorting multilingual text correctly requires Unicode-aware collation:

.. code-block:: sql

   -- Order by French label using ICU collation
   SELECT name, label->>'fr' AS fr_label
   FROM request_ddi_representedvariable
   ORDER BY (label->>'fr') COLLATE "und-x-icu";
