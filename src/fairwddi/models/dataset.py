"""Dataset Layer models for FAIRwDDI.

Includes StudyUnit (survey wave dataset) and InstanceVariable (dataset column realization).
"""

from django.db import models

from fairwddi.models.base import DDIIdentifiable
from fairwddi.models.organization import Subcollection
from fairwddi.models.representation import RepresentedVariable


class StudyUnit(DDIIdentifiable):
    """A specific survey wave or dataset (renamed from Survey)."""

    subcollection = models.ForeignKey(
        Subcollection,
        on_delete=models.CASCADE,
        related_name="study_units",
    )
    title = models.JSONField(
        default=list,
        help_text="Multilingual study title as an array of objects.",
    )
    external_ref = models.CharField(
        max_length=512,
        unique=True,
        null=True,
        blank=True,
        help_text="External identifier or DOI.",
    )
    year = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Survey reference year.",
    )
    description = models.JSONField(
        default=list,
        blank=True,
        help_text="Multilingual study abstract/description as an array of objects.",
    )

    class Meta:
        db_table = "request_ddi_studyunit"
        verbose_name = "Study Unit"
        verbose_name_plural = "Study Units"

    def __str__(self) -> str:
        if isinstance(self.title, list) and self.title:
            return self.title[0].get("value", self.urn or str(self.pk))
        return self.urn or str(self.pk)


class InstanceVariable(DDIIdentifiable):
    """Physical realization of a variable in a specific study column.

    Represents the bottom tier of the DDI variable cascade:
    ConceptualVariable -> RepresentedVariable -> InstanceVariable.
    """

    study_unit = models.ForeignKey(
        StudyUnit,
        on_delete=models.CASCADE,
        related_name="instance_variables",
    )
    represented_variable = models.ForeignKey(
        RepresentedVariable,
        on_delete=models.CASCADE,
        related_name="instance_variables",
    )
    variable_name = models.CharField(
        max_length=255,
        help_text="Column name in the dataset (e.g. 'q01a', 'age_r').",
    )
    universe = models.JSONField(
        default=list,
        blank=True,
        help_text="Multilingual target population/universe description as an array of objects.",
    )
    notes = models.JSONField(
        default=list,
        blank=True,
        help_text="Multilingual variable notes as an array of objects.",
    )
    is_indexed = models.BooleanField(
        default=False,
        help_text="Whether this variable is synchronized in Elasticsearch.",
    )

    class Meta:
        db_table = "request_ddi_instancevariable"
        unique_together = ("study_unit", "variable_name")
        indexes = [
            models.Index(fields=["is_indexed"], name="req_ddi_iv_is_indexed_idx"),
        ]
        verbose_name = "Instance Variable"
        verbose_name_plural = "Instance Variables"

    def __str__(self) -> str:
        return f"{self.study_unit_id}:{self.variable_name}"
