"""Dataset Layer models for FAIRwDDI.

Includes StudyUnit (survey wave dataset), InstanceVariable (dataset column realization),
and StudyUnitVariable (study to variable mapping).
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
        db_column="subcollection_urn",
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
    extended_attributes = models.JSONField(
        default=list,
        blank=True,
        help_text="Extended attributes stored as an array of objects.",
    )

    class Meta:
        db_table = "request_ddi_studyunit"
        verbose_name = "Study Unit"
        verbose_name_plural = "Study Units"

    def __str__(self) -> str:
        if isinstance(self.title, list) and self.title:
            return self.title[0].get("value", self.urn)
        return self.urn


class InstanceVariable(DDIIdentifiable):
    """Physical realization of a variable in a specific dataset.

    Represents the bottom tier of the DDI variable cascade:
    ConceptualVariable -> RepresentedVariable -> InstanceVariable.
    Linked to StudyUnit datasets via StudyUnitVariable.
    """

    represented_variable = models.ForeignKey(
        RepresentedVariable,
        on_delete=models.CASCADE,
        related_name="instance_variables",
        db_column="represented_variable_urn",
    )
    name = models.CharField(
        max_length=255,
        help_text="Physical variable name in the dataset (e.g. 'q01a', 'age_r').",
    )
    label = models.JSONField(
        default=list,
        blank=True,
        help_text="Multilingual variable label as an array of objects.",
    )
    extended_attributes = models.JSONField(
        default=list,
        blank=True,
        help_text="Extended attributes stored as an array of objects.",
    )

    class Meta:
        db_table = "request_ddi_instancevariable"
        verbose_name = "Instance Variable"
        verbose_name_plural = "Instance Variables"

    def __str__(self) -> str:
        return self.name or self.urn


class StudyUnitVariable(models.Model):
    """Junction linking a StudyUnit to its InstanceVariables with path."""

    study_unit = models.ForeignKey(
        StudyUnit,
        on_delete=models.CASCADE,
        related_name="study_unit_variables",
        db_column="study_unit_urn",
    )
    instance_variable = models.ForeignKey(
        InstanceVariable,
        on_delete=models.CASCADE,
        related_name="study_unit_links",
        db_column="instance_variable_urn",
    )
    path = models.CharField(
        max_length=512,
        blank=True,
        default="",
        help_text="Referencing path from study unit to instance variable.",
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order of the variable within the study unit.",
    )

    class Meta:
        db_table = "request_ddi_studyunitvariable"
        unique_together = ("study_unit", "instance_variable")
        ordering = ["order", "id"]
        verbose_name = "Study Unit Variable"
        verbose_name_plural = "Study Unit Variables"

    def __str__(self) -> str:
        return f"{self.study_unit_id} -> {self.instance_variable_id} (order={self.order})"
