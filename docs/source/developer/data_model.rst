The 30-Model Database Architecture
===================================

The FAIRwDDI target database schema consists of **30 models** designed for PostgreSQL 17. The models are organized into 5 functional layers.

Abstract Base Classes
---------------------

1. DDIIdentifiable
~~~~~~~~~~~~~~~~~~

Every versionable entity in the system inherits from ``DDIIdentifiable``:

.. code-block:: python

   class DDIIdentifiable(models.Model):
       urn = models.CharField(max_length=512, primary_key=True)
       name = models.CharField(max_length=255)
       label = models.JSONField(default=dict, blank=True)
       description = models.JSONField(default=dict, blank=True)
       parent_urn = models.ForeignKey("UrnRegistry", null=True, blank=True, on_delete=models.SET_NULL)
       scheme_urn = models.CharField(max_length=512, null=True, blank=True)
       extended_attributes = models.JSONField(default=dict, blank=True)
       hashes = models.JSONField(default=dict, blank=True)  # {"sha256": "...", "blake3": "..."}

       class Meta:
           abstract = True

       def save(self, *args, **kwargs):
           # Automatically upserts into UrnRegistry before saving child record
           UrnRegistry.objects.update_or_create(
               urn=self.urn,
               defaults={"resource_type": self.__class__.__name__}
           )
           super().save(*args, **kwargs)

2. DDIScheme
~~~~~~~~~~~~

Containers of identifiable resources (schemes) inherit from ``DDIScheme``:

* Schemes do **NOT** carry content ``hashes`` because their content is dynamic and comprises member references.
* Leaf resources inside schemes do carry cryptographic multi-algorithm ``hashes``.

Layer & Model Breakdown
-----------------------

.. list-table::
   :widths: 20 30 50
   :header-rows: 1

   * - Layer
     - Model Names
     - Role & Scope
   * - **Concept Layer**
     - ``ConceptScheme``, ``Concept``, ``ConceptualVariable``
     - Controlled vocabularies, thesaurus concepts, and abstract measurement variables.
   * - **Representation Layer**
     - ``VariableScheme``, ``RepresentedVariable``, ``QuestionScheme``, ``QuestionItem``, ``InterviewerInstruction``, ``ControlConstruct``, ``Sequence``, ``CodeListScheme``, ``CodeList``, ``CodeItem``, ``CategoryScheme``, ``Category``, ``ValueDomain``
     - Question texts, instructions, logical flow, answer scales, and categorical labels.
   * - **Dataset Layer**
     - ``StudyUnit``, ``InstanceVariable``, ``DataFile``, ``DataFileVariable``
     - Survey waves, published dataset files, and physical column bindings.
   * - **Organization Layer**
     - ``VariableGroup``, ``Organization``, ``Individual``
     - Thematic clusters, funding agencies, research institutes, and principal investigators.
   * - **Infrastructure Layer**
     - ``UrnRegistry``, ``URNAlias``, ``SemanticRelationship``, ``IngestBatch``, ``IngestionPlan``, ``BatchLineage``, ``EventLog``
     - Referential master table, polymorphic aliases, semantic cross-links, and audit trails.

Polymorphic Cross-Resource Relations
------------------------------------

To allow flexible relationships between heterogeneous entities without cluttering specific tables, FAIRwDDI utilizes three polymorphic models anchored to ``UrnRegistry``:

1. **URNAlias**: Maps legacy, alternative, or external identifiers to a canonical URN::

      URNAlias(alias_urn="urn:cdsp:legacy:q10", canonical_urn="urn:ddi:fr.cdsp:QI_AGE:1.0")

2. **SemanticRelationship**: Generic RDF-style triples connecting any two resources::

      SemanticRelationship(
          subject_urn="urn:ddi:fr.cdsp:CV_AGE:1.0",
          predicate="skos:exactMatch",
          object_urn="https://vocabularies.cessda.eu/vocabulary/elsst/Age"
      )

3. **EventLog**: Immutable audit trail recording operations against any entity::

      EventLog(
          urn="urn:ddi:fr.cdsp:RV_POL:1.0",
          event_type="RE_VERSION",
          operator="archiviste_cdsp",
          details={"old_hash": "...", "new_hash": "..."}
      )
