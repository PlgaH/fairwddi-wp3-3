"""Concept Layer models for FAIRwDDI supporting arbitrary controlled vocabularies.

Provides generic SKOS / XKOS hierarchical concept trees, multilingual definitions,
and concept-to-concept relationships for semantic harmonization across any vocabulary
(e.g., CESSDA ELSST, CESSDA Topics, DDI-CV, custom/local thesauri).
"""

from django.db import models

from fairwddi.models.base import DDIIdentifiable


class Concept(models.Model):
    """High-level thematic or domain concept from any controlled vocabulary or thesaurus.

    Supports hierarchical trees (skos:broader / skos:narrower) via parent relationship,
    notation codes, vocabulary identifiers, and multilingual definitions.
    """

    uri = models.CharField(
        max_length=512,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Authoritative concept URI in a controlled vocabulary or thesaurus.",
    )
    vocabulary = models.CharField(
        max_length=128,
        blank=True,
        default="",
        db_index=True,
        help_text="Controlled vocabulary name or scheme (e.g. 'ELSST', 'CESSDA Topics', 'DDI-CV').",
    )
    notation = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        db_index=True,
        help_text="Standard thesaurus notation / classification code.",
    )
    label = models.JSONField(
        default=list,
        help_text="Multilingual concept label stored as an array of objects.",
    )
    description = models.JSONField(
        default=list,
        blank=True,
        help_text="Multilingual concept description stored as an array of objects.",
    )
    definition = models.JSONField(
        default=list,
        blank=True,
        help_text="Multilingual skos:definition stored as an array of objects.",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="narrower_concepts",
        db_column="parent_urn",
        help_text="Parent concept representing skos:broader hierarchical relationship.",
    )
    concept_type = models.CharField(
        max_length=64,
        default="concept",
        help_text="Concept classification type (e.g. 'domain', 'concept', 'thematic_group').",
    )
    extended_attributes = models.JSONField(
        default=list,
        blank=True,
        help_text="Extended attributes stored as an array of objects.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "request_ddi_concept"
        verbose_name = "Concept"
        verbose_name_plural = "Concepts"

    def __str__(self) -> str:
        if isinstance(self.label, list) and self.label:
            return self.label[0].get("value", str(self.pk))
        return str(self.pk)


class ConceptualVariable(DDIIdentifiable):
    """Abstract measurement concept (e.g. 'Left-Right Political Placement').

    Represents the top tier of the DDI variable cascade:
    ConceptualVariable -> RepresentedVariable -> InstanceVariable.
    """

    concept = models.ForeignKey(
        Concept,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conceptual_variables",
        db_column="concept_urn",
        help_text="Optional parent concept anchor in a controlled vocabulary.",
    )
    label = models.JSONField(
        default=list,
        help_text="Multilingual conceptual variable label as an array of objects.",
    )
    description = models.JSONField(
        default=list,
        blank=True,
        help_text="Multilingual description as an array of objects.",
    )
    extended_attributes = models.JSONField(
        default=list,
        blank=True,
        help_text="Extended attributes stored as an array of objects.",
    )

    class Meta:
        db_table = "request_ddi_conceptualvariable"
        verbose_name = "Conceptual Variable"
        verbose_name_plural = "Conceptual Variables"

    def __str__(self) -> str:
        if isinstance(self.label, list) and self.label:
            return self.label[0].get("value", self.urn)
        return self.urn


class SemanticRelationship(models.Model):
    """RDF triple-like semantic relationship between resources.

    Captures SKOS mappings (skos:exactMatch, skos:broadMatch, skos:closeMatch,
    skos:relatedMatch), provenance/lineage relationships (prov:wasDerivedFrom),
    cross-vocabulary alignments, and domain-specific semantic graph links.
    """

    subject_type = models.CharField(
        max_length=128,
        help_text=(
            "Resource type of the subject (e.g. 'Concept', 'ConceptualVariable', 'QuestionItem')."
        ),
    )
    subject_urn = models.CharField(
        max_length=512,
        db_index=True,
        help_text="Canonical URN or URI of the subject resource.",
    )
    predicate = models.CharField(
        max_length=256,
        db_index=True,
        help_text=(
            "Relationship predicate (e.g. 'skos:exactMatch', 'skos:broadMatch', "
            "'skos:closeMatch', 'skos:relatedMatch')."
        ),
    )
    object_type = models.CharField(
        max_length=128,
        help_text=(
            "Resource type of the object (e.g. 'Concept', 'ConceptualVariable', "
            "'ExternalResource')."
        ),
    )
    object_urn = models.CharField(
        max_length=512,
        db_index=True,
        help_text="Canonical URN or URI of the object resource.",
    )
    extended_attributes = models.JSONField(
        default=list,
        blank=True,
        help_text="Extended attributes stored as an array of objects.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "request_ddi_semanticrelationship"
        verbose_name = "Semantic Relationship"
        verbose_name_plural = "Semantic Relationships"
        ordering = ["subject_urn", "predicate", "object_urn"]
        constraints = [
            models.UniqueConstraint(
                fields=["subject_urn", "predicate", "object_urn"],
                name="uq_semrel_triple",
            ),
        ]
        indexes = [
            models.Index(fields=["subject_urn", "predicate"], name="idx_semrel_sub_pred"),
            models.Index(fields=["object_urn", "predicate"], name="idx_semrel_obj_pred"),
            models.Index(fields=["predicate"], name="idx_semrel_predicate"),
            models.Index(fields=["subject_type"], name="idx_semrel_sub_type"),
            models.Index(fields=["object_type"], name="idx_semrel_obj_type"),
        ]

    def __str__(self) -> str:
        return f"{self.subject_urn} --[{self.predicate}]--> {self.object_urn}"
