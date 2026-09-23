# FAIRwDDi WP3-ST3 Phase I: Audit and DDI-L DB Model



## Summary

...

## Audit

The following findings about the current ReQuest database are based on a Postgres dump/copy we received in July, analysis of the application code, and conversations with the Sciences Po team.

### Database schema

- The current ReQuest database consists of 13 tables
- It partially mimics the variable cascade model but is primarily designed to support the ReQuest application
- Its content is based on a normalized subset of the metadata from DDI-Codebook documents sourced from Dataverse servers.
- Not all tables are populated.
- The ingestion process reads the DDI-C document, performs normalization and matching cleansing steps, and uses a subset of the information to ensure data quality and consistency in the database.

### Surveys, Collections and Distributors

- The `survey` table contains 271 records, including DOI links that connect to the survey home pages on the Sciences Po Dataverse server, highlighting the data's accessibility and relevance.
- The `external_reference` field holds a DOI that resolves to the survey home page on the Sciences Po Dataverse server.
- The table holds the study `name`, version date (`date_last_version`), `author`, and `start_date`
- Other fields, all holding the same value, are `language` (always `fr`),
- The `subcollection_id` points to one of the 14 entries in the `request_ddi_subcollection` table.
- All subcollections are associated with two collections in the `request_ddi_collection` table.
- All collections are associated with 'Science Po as the single record in the `request_ddi_distributor` table.

#### Variables & Questions

- The `representedvariable` table holds a _normalized_ version of a question and an optional associated category set.
  - It represents a question more than a variable. It does not hold data type or other variable attributes.
  - RepresentedVariable≡(Normalized Question Text)+(Exact Set of Categories)
  - Represented variables are associated with their categories (if applicable) through the `representedvariable_categories` table.
  - It is independent of the source variable name, type, label, and other attributes.
    - It holds an `internal_label` based on the first variable this question/value information appears in (this does not get updated).
- The `conceptualvariable` table acts as the umbrella that groups all structural variations of the same question text. 
  - The 'group' is referenced by the `conceptual_var_id` fields in the represented variable table
- A `is_unique` flag, used in both the represented and conceptual variable tables, indicates whether a variable is a *standard questionnaire item* or an *isolated / non-comparable variable*
  - `false`: The variable has actual verbatim question text. It is treated as semantically meaningful and eligible for longitudinal comparison across survey waves.
  - `true`: The variable has no question text. Because it lacks wording to guarantee semantic equivalence, it is flagged as is_unique=True.
  - Note that technically, the `is_unique` flag is redundant in the `representedvariable` table as the same information could be inferred by a null/empty `question_text`. It, however, facilitates querying and, importantly, its value can be manually toggled through the admin UI, even if it does have question text (e.g., a one-off experimental question that a curator wants to explicitly exclude from automated longitudinal comparison widgets).
- The ``
- Note that DDI-C interviewer instructions and pre/post question texts are currently not stored or taken into consideration

#### Codes Lists

- Harmonized codes and value labels are stored in the `category` table
  - Records in this table are deduplicated based on the code value and normalized category label
  - A `missing` flag is present and populated
- Entries are associated with represented variables through the `representedvariable_categories` table
- Entries are associated with variables through the `bindingvariablecategorystat` table
  - The `stats` column in that table contains the frequency for the associated variable

#### Concepts

- A `request_ddi_concept` table is present, but no concepts are populated
- The `request_ddi_conceptualvariable_concepts` is likewise empty



### Harmonization and deduplication pipeline

When imorting DDI-Codebook document, the system automatically deduplicates and harmonizes the resources for storage into the various tables.

#### Code Lists

- Looks up or creates a `category` record matching `code` and `category_label` using a custom case- and accent-insensitive database collation
- The `missing` flag is set when the code/label record is first created
  - :warning: The `missing` flag is never subsequently adjusted, even if the same code/category is ingested with a different value, which can techncially introduce semantic inconsistencies

#### Represented & Conceptual Variable Harmonization

To track questions over time and link recurring questions across different survey waves:

- Query by Question Text: Normalizes the question text and searches for existing `RepresentedVariable` entries with the same normalized text.
- Exact Match Check: Compares the set of category IDs of each match.
- If a `RepresentedVariable` with the _same question text_ and _identical set of categories_ exists, that existing variable is reused.
- Similar Variable (Same Concept): If the question text matches existing variables but the category set differs, a new `RepresentedVariable` is created and attached to the **existing** `ConceptualVariable`.
- If no matching question text exists, a new `ConceptualVariable` is created, and the new `RepresentedVariable` is linked to it.
- Variables with no categories
- Variables with no question text:
- Variable without a question and code list are ignored

The table below summarizes how the ingestion pipeline treats every permutation of presence or absence of question text and category sets:

| Scenario                                      | Question Text? | Categories? | Lookup / Matching Strategy                                   | Harmonization & Database Creation Behavior                   | `is_unique` Flag |    Stats Created?    |
| :-------------------------------------------- | :------------: | :---------: | :----------------------------------------------------------- | :----------------------------------------------------------- | :--------------: | :------------------: |
| **Standard Categorical Question**             |     ✅ Yes      |    ✅ Yes    | Matched strictly on normalized `question_text`.              | • **Exact category match**: Reuses existing `RepresentedVariable`. • **Category mismatch**: Creates new `RepresentedVariable`, links to **existing** `ConceptualVariable`. • **No question match**: Creates **new** `ConceptualVariable` & `RepresentedVariable`. |     `False`      | ✅ Yes (per category) |
| **Open-ended / Continuous Variable**          |     ✅ Yes      |    ❌ No     | Matched on normalized `question_text` where categories is empty (`set() == set()`). | • **Match found**: Reuses existing open-ended `RepresentedVariable`. • **Mismatch/New**: Creates new `RepresentedVariable` (and new/reused `ConceptualVariable`). |     `False`      | ❌ No (no categories) |
| **Derived / Calculated Categorical Variable** |      ❌ No      |    ✅ Yes    | Fallback matching on `variable_name` across prior `BindingSurveyRepresentedVariable` records. | • **Exact category match**: Reuses existing `RepresentedVariable`. • **Category mismatch**: Creates new `RepresentedVariable`, reuses concept of matching variable name. • **No variable name match**: Creates **new** `ConceptualVariable` & `RepresentedVariable`. |      `True`      | ✅ Yes (per category) |
| **Empty / Unspecified Variable**              |      ❌ No      |    ❌ No     | None (skipped before lookup).                                | • **Completely ignored** (`get_or_create_represented_variable` returns `None`). • No database rows or bindings created. |       N/A        |         ❌ No         |

#### Survey-Variable

- Creates or updates a `BindingSurveyRepresentedVariable` linking the specific `Survey` to the canonical RepresentedVariable`.
- Captures survey-specific properties: `variable_name` (e.g., `ea19_A1`), `universe`, and `notes`.

#### Category Statistics Binding

- Creates a `BindingVariableCategoryStat` record for each category, associating the frequency count (`stat`) with that specific `BindingSurveyRepresentedVariable`.

## Findings and Proposed Adjustments

- The table names can be misleading and are not always consistent with the DDI-C terminology

- The question is not treated as a reusable resource. 

- The question uniqueness is purely based on the literal question text and ignores other contextual elements (pre/post text, instructions)

- The variable data type and other attributes are being ignored

- Variables are directly associated with surveys, ignoring the dataset they belong to

### Suggested adjustments & questions

- Rename tables

- Add a table to hold question items
  - :question:Will the question item *uniqueness* continue to be solely based on the question text, or will other aspects such as instructions, pre/post texts, or even instrument characteristics be taken into account?
- Replace the  survey/representedvariable bindings with instance variables, physical instance, and studies
- :question:Are frequencies being used? Then why not other statistics?



## DDI-L + Multilingual Redesign

- Transitioning into a DDI-L and multilingual model strengthens capabilities but naturally increases complexity
- It requires a more sophisticated approach to metadata ingestion and management
- Which features of this enriched model to support or implement is up to the ReQuest team
  - This largely depends on the needs or requirements of the next version of the application itself, which is beyond the scope of this exercise
  - It can remain simple at first, mimicking the current implementation, and evolve later
  - We assume at this point that minimizing impact on the extisting application is a priority
- But in the new model, the simple relations between questions, variables, code/categories studies no longer hold true
  - The next iteration of the application will therefore need to take these aspects into account
- This, however, will depend on the content being ingested
  - If the imported DDI is simply based on DDI-C converted to DDI-L, little adjustment will be required
  - Once content is sourced from true DDI-L, the application will need to take into account the more versatile resource relationships
    - Questions may exist without associated variables (of any type), studies, or code lists

### Redesign principles

The new database has been designed on the following principles:

- Based on DDI-L but keep it simple. Only store what is needed by ReQuest. Avoid full DDI-L complexity/coverage.
- Align the table naming conventions on DDI-L terminology
- Strengthen the model (variable cascade and other DDI-L aspects)
- Support different import/export techniques or strategies
- Accommodate for current and future versions of DDI-L or similar specificaions (DDI-CDI)
- Backward compatibility with DDI-Codebook
- Use JSONB fields to store multilingual strings
- Rely on URNs as primay identifers

### Multilingual Fields

Besides the strengthening the alignment of the database model with DDI-L, support for multilinual is also a new features. 

At the database storage level, this is relatively easy to address by adopting a JSONB storage format for multilingual text values. Postgres provides several specialized querying mechanisms for this storage type.

We propose to simply store it as an array of objects with a language and value property:

```json
[
  {"lang": "en", "value": "How old are you?"},
  {"lang": "fr", "value": "Quel âge avez-vous?"}
]
```

For consistency, the entries must *always* be wrapped in an array, even if we only have a single entry.
and do not know the language.

```json
[{"lang": "en", "value": "How old are you?"}]
```

Another approach would be to adopt a flat lang/value format like:

```json
[{"en": "How old are you?"},  {"fr":"Quel âge avez-vous?"}]
```

However, we prefer the array-of-objects approach, as it lets us add other facets to the string. For example, we may want to store a 'normalized' version of a string used internally for comparison or hashing, or keep the 'raw' unsanitized version (which, for example, may contain typos or slight textual variations).

```
[
  {"lang": "en", "value": "how_old_are_you?", "type":"normalized"},
  {"lang": "fr", "value": "Quel âge avez-vous?"}
  {"lang": "fr", "value": "quel_age_avez-vous?", "type": "normalized"}
  {"lang": "fr", "value": "Quellle agge avez vous?   ", "type": "raw"}
]
```

Other useful facets can includes:

- "format": markdown, HTML
- "translated": to capture automatic or human translations

These additional properties must, of course, be formally defined, which we can do using a JSON schema and Python Pydantic classes.

Note that, technically, a string could be stored without a "lang" attribute.

```
[ {"value": "How old are you?"}]
```

### Database and resource identifiers

- The new model relies on URN as primary keys and resource identifiers
  - This implliesfor every resource to have a URN, but this is implied in DDI-L context
  - For resources that comes from non-DDI-L sources, such as DDI-C, this would need to be generated (which is a relatively easy)
- While auto-generated ids can still be generated in the database, these are not flexible and reliable. For example:
  - Reimporting the same metadata in different database (e.g. on different servers) would result into different identifiers
  - Maintaining multiple databases, which is common in a enterprise grade envrionment (e.g. staging and production), will translate into inconsistent identifiers, which can complicate scirpts or worflows
- In DDI-L
  - Different [identification](https://ddi-lifecycle-technical-guide.readthedocs.io/en/latest/General%20Structures/Identification.html) and referencing mechanisms are available:
    - Identification Sequence: composed of agency id, maintainable id, object id (), and version
    - URNs: a canonical repsentation of the identification sequence
  - A legacy deprecate URN format is also documented but should be avoided
  - All variations must be converted to the canonical URN format
- Using URNs as primary identifiers also caters for non-DDI resources (e.g controlled vocabularies)

### Extended Attributes

- Modeling all the attributes and characteristics of DDI-L resources in a database would be unrealistic.  SQL is not the right technology for this.
- The ReQuest application only uses a handful of them for comparison or information purposes
- Capturing a small subset of these elements can however be desirable for internal or future application needs. For example:
  - A question's intent, instructions, or instrument
  - A variable type, value domain
  - A category definition, inclusion/exclusion
- This can greatly vary depending on the metadata provider, the incoming DDI content, or the profile
- To support this,  we include an `extended_attributes` JSON field in applicable tables
- We recommend embedding a schema definition or URL in the stored JSON ( Self-Describing JSON Document) to identify its content
  - The JSON could be validated againt the schema (inside or outside the databse)
  - :question: an ``extended_attributes_schema` column coudl be use instead. Thoughts?
  - :question: if we know for sure that all extended attributes must follow the same schema, it can be defined at the table level using a `CHECK` constraint.

*Example: a question coming from DDI-L carrying few extra properties of interest (the question text is already in the table `question_text` field):*

```{json}
[
{
  "$schema": "https://request.sciencespo.fr/schemas/ddil-question-item.json",
  "urn": "urn:ddi:int.example:c7233173-2d8f-4a3f-918b-60ee08d61d5d:1",
  "Description": "This is a great question",
  "QuestionIntent": "Get a great answer"
  ]
}
]
```

*Example: a question coming from DDI-Codebook with surrouding elements (the question text is already in the table's'`question_text` field):*

```json}
[
{
  "$schema": "https://request.sciencespo.fr/schemas/ddic-qstn.json",
  "urn": "urn:some:var:ddiCodebookUrn",
  "preQTxt": "I will now ask you a great questions",
  "postQTxt": "Thank you for your great answer",
  "ivuInstr": "Be engaged and excited while asking this great question"
  ]
}
]
```



## Revised Database Model

### Model layers

- The proposed model is composed on 16 tables organized in 7 layers
- DDI-L table
- ReQuest support table
- Staging tavbles
- 1 layer is a helper to stage incoming metadata prior to ingestion (normalization, harmonization)

### DDI-L Tables



### ReQuest Tables





### Staging Tables

- We can technically directly inport DDI-L into the above
- To isolate the ReQuest database



### Summary of Changes





## Next Steps

- Export script
- Import scripts
- Model may continue to evolve and new tables may be introduces to support ingestion
- Test import with collected DDI-L files
- Test import using DDI-C upgraded to DDI-L once available (upgrade tool out of scope)
