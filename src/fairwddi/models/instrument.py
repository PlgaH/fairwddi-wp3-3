"""Instrument Layer models for FAIRwDDI.

Includes Instrument and InstrumentQuestion.
"""

from django.db import models

from fairwddi.models.base import DDIIdentifiable
from fairwddi.models.representation import QuestionItem


class Instrument(DDIIdentifiable):
    """Data collection instrument / questionnaire in DDI-Lifecycle."""

    name = models.JSONField(
        default=list,
        blank=True,
        help_text="Multilingual instrument technical name: [{'lang': 'fr', 'value': '...'}].",
    )
    label = models.JSONField(
        default=list,
        blank=True,
        help_text="Multilingual human-readable title / label.",
    )
    description = models.JSONField(
        default=list,
        blank=True,
        help_text="Multilingual description / abstract.",
    )
    extended_attributes = models.JSONField(
        default=list,
        blank=True,
        help_text="Extended attributes stored as an array of objects.",
    )

    class Meta:
        db_table = "request_ddi_instrument"
        verbose_name = "Instrument"
        verbose_name_plural = "Instruments"

    def __str__(self) -> str:
        if isinstance(self.label, list) and self.label:
            return self.label[0].get("value", self.urn)
        if isinstance(self.name, list) and self.name:
            return self.name[0].get("value", self.urn)
        return self.urn


class InstrumentQuestion(models.Model):
    """Junction associating an Instrument to member QuestionItem entities with referencing path."""

    instrument = models.ForeignKey(
        Instrument,
        on_delete=models.CASCADE,
        related_name="question_associations",
        db_column="instrument_urn",
    )
    question_item = models.ForeignKey(
        QuestionItem,
        on_delete=models.CASCADE,
        related_name="instrument_associations",
        db_column="question_item_urn",
    )
    path = models.CharField(
        max_length=512,
        blank=True,
        default="",
        help_text="Referencing path from instrument to question (e.g. sequence/flow path).",
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order or question sequence number within the instrument.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "request_ddi_instrumentquestion"
        unique_together = ("instrument", "question_item", "path")
        ordering = ["order", "id"]
        verbose_name = "Instrument Question"
        verbose_name_plural = "Instrument Questions"

    def __str__(self) -> str:
        return f"{self.instrument_id} -> {self.question_item_id} ({self.path})"
