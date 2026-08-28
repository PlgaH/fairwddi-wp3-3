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
        help_text="Parent concept representing skos:broader hierarchical relationship.",
    )
    concept_type = models.CharField(
        max_length=64,
        default="concept",
        help_text="Concept classification type (e.g. 'domain', 'concept', 'thematic_group').",
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


class ConceptRelationship(models.Model):
    """Semantic mapping between concepts (SKOS / XKOS relationships)."""

    source_concept = models.ForeignKey(
        Concept,
        on_delete=models.CASCADE,
        related_name="outgoing_relationships",
    )
    target_concept = models.ForeignKey(
        Concept,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="incoming_relationships",
    )
    relationship_type = models.CharField(
        max_length=64,
        help_text="SKOS relation: broader, narrower, related, exactMatch, correspondsTo.",
    )
    target_uri = models.CharField(
        max_length=512,
        null=True,
        blank=True,
        help_text="External URI if target concept is outside the local database.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "request_ddi_concept_relationship"
        verbose_name = "Concept Relationship"
        verbose_name_plural = "Concept Relationships"

    def __str__(self) -> str:
        target = self.target_concept.pk if self.target_concept else self.target_uri
        return f"{self.source_concept_id} -[{self.relationship_type}]-> {target}"


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

    class Meta:
        db_table = "request_ddi_conceptualvariable"
        verbose_name = "Conceptual Variable"
        verbose_name_plural = "Conceptual Variables"

    def __str__(self) -> str:
        if isinstance(self.label, list) and self.label:
            return self.label[0].get("value", self.urn or str(self.pk))
        return self.urn or str(self.pk)
