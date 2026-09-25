"""Institutional organization hierarchy models for FAIRwDDI."""

from __future__ import annotations

from django.db import models

from fairwddi.models.base import DDIResource


class Organization(DDIResource):
    """Institutional organization resource in DDI-Lifecycle (maps to DDI-L Organization).

    Represents data distributors, archives, research centers, universities, funding bodies,
    and publishers in the DDI organizational hierarchy.
    """

    organization_type = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        default=None,
        db_index=True,
        help_text="Organization classification type (e.g. 'archive', 'distributor', 'funder').",
    )
    extended_attributes = models.JSONField(
        default=list,
        blank=True,
        null=True,
        help_text="Extended attributes stored as an array of objects.",
    )

    class Meta:
        db_table = "request_ddi_organization"
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"


class Group(DDIResource):
    """Generic Group DDI resource (maps to DDI-L Group / SubGroup).

    Logical grouping of related resources (e.g. study series, panels,
    thematic collections, or longitudinal waves) referenced via polymorphic
    typed URN references.
    """

    description = models.JSONField(
        default=list,
        blank=True,
        null=True,
        help_text="Multilingual description for the group.",
    )
    group_type = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        default=None,
        db_index=True,
        help_text=(
            "Group classification type (e.g. 'study_series', 'panel', 'thematic', 'collection')."
        ),
    )
    references = models.JSONField(
        default=list,
        blank=True,
        null=True,
        help_text=(
            "List of referenced member resources: [{'resource_type': 'StudyUnit', 'urn': '...' }]."
        ),
    )
    extended_attributes = models.JSONField(
        default=list,
        blank=True,
        null=True,
        help_text="Extended attributes stored as an array of objects.",
    )

    class Meta:
        db_table = "request_ddi_group"
        verbose_name = "Group"
        verbose_name_plural = "Groups"
