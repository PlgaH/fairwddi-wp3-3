"""Grouping / Organization Layer models for FAIRwDDI.

Includes VariableGroup (thematic grouping in DDI-Lifecycle 3.3) and VariableGroupMembership.
"""

from django.db import models

from fairwddi.models.base import DDIIdentifiable
from fairwddi.models.concept import Concept
from fairwddi.models.dataset import InstanceVariable, StudyUnit
from fairwddi.models.organization import Collection


class VariableGroup(DDIIdentifiable):
    """Thematic or structural grouping of variables conforming to DDI-Lifecycle 3.3.

    Can be scoped to a single StudyUnit wave or across a series Collection.
    Supports recursive nesting (parent_group) and classification (type_of_group).
    """

    study_unit = models.ForeignKey(
        StudyUnit,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="variable_groups",
        help_text="Optional link scoping this group to a specific study wave.",
    )
    collection = models.ForeignKey(
        Collection,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="variable_groups",
        help_text="Optional link scoping this group across a series collection.",
    )
    parent_group = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subgroups",
        help_text="Optional parent group for hierarchical group schemes.",
    )
    label = models.JSONField(
        default=list,
        help_text="Multilingual group title/label stored as an array of objects.",
    )
    description = models.JSONField(
        default=list,
        blank=True,
        help_text="Multilingual group description as an array of objects.",
    )
    type_of_group = models.CharField(
        max_length=64,
        default="Thematic",
        help_text="DDI-L typeOfVariableGroup (e.g. 'Thematic', 'Section', 'Subject', 'Iteration').",
    )
    concept = models.ForeignKey(
        Concept,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="variable_groups",
        help_text="Optional link to controlled vocabulary concept.",
    )

    class Meta:
        db_table = "request_ddi_variablegroup"
        verbose_name = "Variable Group"
        verbose_name_plural = "Variable Groups"

    def __str__(self) -> str:
        if isinstance(self.label, list) and self.label:
            return self.label[0].get("value", self.urn or str(self.pk))
        return self.urn or str(self.pk)


class VariableGroupMembership(models.Model):
    """Junction connecting VariableGroup to member InstanceVariable entries with explicit order."""

    variable_group = models.ForeignKey(
        VariableGroup,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    instance_variable = models.ForeignKey(
        InstanceVariable,
        on_delete=models.CASCADE,
        related_name="group_memberships",
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order of the variable within the group.",
    )

    class Meta:
        db_table = "request_ddi_variablegroupmembership"
        unique_together = ("variable_group", "instance_variable")
        ordering = ["order", "id"]
        verbose_name = "Variable Group Membership"
        verbose_name_plural = "Variable Group Memberships"

    def __str__(self) -> str:
        return f"{self.variable_group_id} -> {self.instance_variable_id} (order={self.order})"
