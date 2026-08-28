"""Institutional organization hierarchy models for FAIRwDDI."""

from django.db import models


class Distributor(models.Model):
    """Top-level organization distributing datasets (e.g. CDSP)."""

    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "request_ddi_distributor"
        verbose_name = "Distributor"
        verbose_name_plural = "Distributors"

    def __str__(self) -> str:
        return self.name


class Collection(models.Model):
    """Logical grouping of survey series (maps to DDI-L Group)."""

    distributor = models.ForeignKey(
        Distributor,
        on_delete=models.CASCADE,
        related_name="collections",
    )
    name = models.CharField(max_length=255)
    description = models.JSONField(
        default=list,
        blank=True,
        help_text="Multilingual collection description stored as an array of objects.",
    )
    urn = models.CharField(
        max_length=512,
        unique=True,
        null=True,
        blank=True,
        help_text="DDI-L Group URN.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "request_ddi_collection"
        verbose_name = "Collection"
        verbose_name_plural = "Collections"

    def __str__(self) -> str:
        return self.name


class Subcollection(models.Model):
    """Sub-series grouping (maps to DDI-L SubGroup)."""

    collection = models.ForeignKey(
        Collection,
        on_delete=models.CASCADE,
        related_name="subcollections",
    )
    name = models.CharField(max_length=255)
    urn = models.CharField(
        max_length=512,
        unique=True,
        null=True,
        blank=True,
        help_text="DDI-L SubGroup URN.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "request_ddi_subcollection"
        verbose_name = "Subcollection"
        verbose_name_plural = "Subcollections"

    def __str__(self) -> str:
        return f"{self.collection.name} - {self.name}"
