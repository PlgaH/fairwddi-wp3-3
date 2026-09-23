"""Institutional organization hierarchy models for FAIRwDDI."""

from django.db import models

from fairwddi.models.base import DDIIdentifiable


class Distributor(models.Model):
    """Top-level organization distributing datasets (e.g. CDSP, CESSDA)."""

    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "request_ddi_distributor"
        verbose_name = "Distributor"
        verbose_name_plural = "Distributors"

    def __str__(self) -> str:
        return self.name


class Collection(DDIIdentifiable):
    """Logical grouping of survey series (maps to DDI-L Group)."""

    distributor = models.ForeignKey(
        Distributor,
        on_delete=models.CASCADE,
        related_name="collections",
        db_column="distributor_id",
    )
    name = models.CharField(max_length=255)
    description = models.JSONField(
        default=list,
        blank=True,
        help_text="Multilingual collection description stored as an array of objects.",
    )

    class Meta:
        db_table = "request_ddi_collection"
        verbose_name = "Collection"
        verbose_name_plural = "Collections"

    def __str__(self) -> str:
        return self.name


class Subcollection(DDIIdentifiable):
    """Sub-series grouping (maps to DDI-L SubGroup)."""

    collection = models.ForeignKey(
        Collection,
        on_delete=models.CASCADE,
        related_name="subcollections",
        db_column="collection_urn",
    )
    name = models.CharField(max_length=255)

    class Meta:
        db_table = "request_ddi_subcollection"
        verbose_name = "Subcollection"
        verbose_name_plural = "Subcollections"

    def __str__(self) -> str:
        return f"{self.collection.name} - {self.name}"
