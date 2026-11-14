Universal URN Master Registry (UrnRegistry)
=============================================

The central architectural innovation for referential integrity in FAIRwDDI is the **Supertype Master Registry** pattern implemented via the ``request_ddi_urnregistry`` table.

The Problem It Solves
---------------------

In monolithic DDI XML specifications, any resource can theoretically reference any other resource across schemes, modules, or files. In relational databases, this creates a major challenge:

* Relational databases cannot enforce a native foreign key constraint to "any table".
* Without central foreign key enforcement, cross-resource relations (aliases, parent-child links, semantic triples) frequently lead to dangling pointers and orphaned metadata.

The Supertype Master Pattern
----------------------------

FAIRwDDI solves this by designating ``UrnRegistry`` as the universal master parent of all DDI entities:

.. code-block:: sql

   CREATE TABLE request_ddi_urnregistry (
       urn VARCHAR(512) PRIMARY KEY,
       resource_type VARCHAR(64) NOT NULL,
       agency VARCHAR(128) NOT NULL,
       identifier VARCHAR(256) NOT NULL,
       version VARCHAR(64) NOT NULL,
       created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
       updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
   );

Every child table (e.g., ``request_ddi_questionitem``, ``request_ddi_representedvariable``) defines its primary key as:

.. code-block:: sql

   CREATE TABLE request_ddi_questionitem (
       urn VARCHAR(512) PRIMARY KEY REFERENCES request_ddi_urnregistry(urn) ON DELETE CASCADE,
       name VARCHAR(255) NOT NULL,
       question_text JSONB DEFAULT '{}'::jsonb,
       ...
   );

Lifecycle Guarantees
--------------------

1. Automatic Pre-Registration on Save
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Whenever ``model.save()`` is called on any instance inheriting from ``DDIIdentifiable``:

1. The entity's canonical URN is parsed into its component parts (``agency``, ``identifier``, ``version``).
2. The ``UrnRegistry`` row is created or updated in the current transaction.
3. The child table row is saved with guaranteed foreign key validity.

2. Guaranteed Cascading Deletions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When an entity is deleted from its specific table or from ``UrnRegistry``:
* PostgreSQL's ``ON DELETE CASCADE`` automatically purges all child records, aliases, semantic relationships, and references without manual cleanup scripts or dangling pointers.

3. O(1) Resource Type Resolution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Because ``UrnRegistry`` maintains the ``resource_type`` discriminator for every registered URN in the database, the system can resolve which table and model class any arbitrary URN belongs to in a single indexed query:

.. code-block:: python

   from fairwddi.models import UrnRegistry
   import fairwddi.models as models

   def resolve_entity(urn: str):
       reg = UrnRegistry.objects.get(urn=urn)
       model_class = getattr(models, reg.resource_type)
       return model_class.objects.get(urn=urn)

Canonical URN Syntax
--------------------

FAIRwDDI enforces RFC 3986-compliant DDI URNs::

   urn:ddi:<agency>:<identifier>:<version>

Examples:
* ``urn:ddi:fr.cdsp:QI_GENDER:1.0``
* ``urn:ddi:fr.cdsp:CL_EDUCATION_ISCED11:2.0``
* ``urn:ddi:fr.cdsp:RV_LEFT_RIGHT:1.0``

Utility Helpers:

.. code-block:: python

   from fairwddi.utils.urn import parse_urn, format_urn, is_valid_urn

   info = parse_urn("urn:ddi:fr.cdsp:QI_GENDER:1.0")
   # {"agency": "fr.cdsp", "id": "QI_GENDER", "version": "1.0"}
