"""Representation Layer models for FAIRwDDI.

Includes QuestionScheme, QuestionItem, Category, CategoryScheme,
CodeList, Code, RepresentedVariable, and QuestionVariable.
"""

from __future__ import annotations

from typing import Any

from django.db import models

from fairwddi.models.base import DDIIdentifiable, DDIResource, DDIScheme
from fairwddi.models.concept import Concept, ConceptualVariable


class QuestionScheme(DDIScheme):
    """Named collection of reusable questions (maps to DDI-L QuestionScheme)."""

    class Meta:
        db_table = "request_ddi_questionscheme"
        verbose_name = "Question Scheme"
        verbose_name_plural = "Question Schemes"


class QuestionItem(DDIResource):
    """Standalone reusable question text."""

    scheme = models.ForeignKey(
        QuestionScheme,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="questions",
        db_column="scheme_urn",
        help_text="Parent QuestionScheme defining this question.",
    )
    code_list = models.ForeignKey(
        "fairwddi.CodeList",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="question_items",
        db_column="code_list_urn",
        help_text="Associated response CodeList (null for non-coded response domains).",
    )
    response_domain = models.JSONField(
        default=dict,
        blank=True,
        null=True,
        help_text=(
            "JSON object describing the response domain "
            "(e.g. {'type': 'code', 'code_list_urn': '...'}, {'type': 'numeric', ...})."
        ),
    )
    question_text = models.JSONField(
        default=list,
        blank=True,
        null=True,
        help_text="Multilingual literal question text: [{'lang': 'fr', 'value': '...'}].",
    )
    extended_attributes = models.JSONField(
        default=list,
        blank=True,
        null=True,
        help_text="Extended attributes stored as an array of objects.",
    )

    class Meta:
        db_table = "request_ddi_questionitem"
        verbose_name = "Question Item"
        verbose_name_plural = "Question Items"

    def save(self, *args, **kwargs) -> None:
        if self.code_list_id and not self.response_domain:
            self.response_domain = {"type": "code", "code_list_urn": self.code_list_id}
        elif (
            isinstance(self.response_domain, dict)
            and self.response_domain.get("type") == "code"
            and self.response_domain.get("code_list_urn")
            and not self.code_list_id
        ):
            self.code_list_id = self.response_domain["code_list_urn"]
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        if isinstance(self.name, list) and self.name:
            return self.name[0].get("value", self.urn)
        if isinstance(self.question_text, list) and self.question_text:
            return self.question_text[0].get("value", self.urn)
        return self.urn


class CategoryScheme(DDIScheme):
    """Named collection of reusable categories (maps to DDI-L CategoryScheme)."""

    class Meta:
        db_table = "request_ddi_categoryscheme"
        verbose_name = "Category Scheme"
        verbose_name_plural = "Category Schemes"


class Category(DDIResource):
    """Response category text label (decoupled from numerical code values)."""

    scheme = models.ForeignKey(
        CategoryScheme,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="categories",
        db_column="scheme_urn",
        help_text="Parent CategoryScheme defining this category.",
    )
    concept = models.ForeignKey(
        Concept,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="categories",
        db_column="concept_urn",
        help_text="Optional semantic concept anchor in a controlled vocabulary.",
    )
    label = models.JSONField(
        default=list,
        blank=True,
        null=True,
        help_text="Multilingual category label: [{'lang': 'fr', 'value': '...' }].",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        db_column="parent_urn",
        help_text="Parent category for hierarchical category schemes.",
    )
    order = models.PositiveIntegerField(
        default=0,
        null=True,
        blank=True,
        help_text="Display order within the category scheme.",
    )
    is_missing = models.BooleanField(
        default=False,
        null=True,
        blank=True,
        help_text="Indicates whether this category represents a missing or non-response value.",
    )
    extended_attributes = models.JSONField(
        default=list,
        blank=True,
        null=True,
        help_text="Extended attributes stored as an array of objects.",
    )

    class Meta:
        db_table = "request_ddi_category"
        ordering = ["order", "urn"]
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self) -> str:
        if isinstance(self.name, list) and self.name:
            return self.name[0].get("value", self.urn)
        if isinstance(self.label, list) and self.label:
            return self.label[0].get("value", self.urn)
        return self.urn


class CodeList(DDIResource):
    """Structural set of response codes linked to categories."""

    description = models.JSONField(
        default=list,
        blank=True,
        null=True,
        help_text="Multilingual description.",
    )
    scheme = models.ForeignKey(
        CategoryScheme,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="code_lists",
        db_column="scheme_urn",
        help_text="Optional link to parent CategoryScheme.",
    )
    extended_attributes = models.JSONField(
        default=list,
        blank=True,
        null=True,
        help_text="Extended attributes stored as an array of objects.",
    )

    class Meta:
        db_table = "request_ddi_codelist"
        verbose_name = "Code List"
        verbose_name_plural = "Code Lists"


class Code(DDIIdentifiable):
    """Junction connecting a CodeList to a Category with a code value (DDI Code)."""

    code_list = models.ForeignKey(
        CodeList,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="codes",
        db_column="code_list_urn",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="code_memberships",
        db_column="category_urn",
    )
    code_value = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        default=None,
        help_text="The numerical or string code (e.g. '1', '98', 'Refused').",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        db_column="parent_urn",
        help_text="Parent code for hierarchical code schemes.",
    )
    order = models.PositiveIntegerField(
        default=0,
        null=True,
        blank=True,
        help_text="Display order within the code list.",
    )
    is_missing = models.BooleanField(
        default=False,
        null=True,
        blank=True,
        help_text="Indicates whether this code represents a missing or non-response value.",
    )
    hashes = models.JSONField(
        default=dict,
        blank=True,
        null=True,
        help_text="Unified key-value hash digests dictionary (e.g. {'sha256': '...'}).",
    )
    extended_attributes = models.JSONField(
        default=list,
        blank=True,
        null=True,
        help_text="Extended attributes stored as an array of objects.",
    )

    class Meta:
        db_table = "request_ddi_code"
        unique_together = ("code_list", "code_value")
        ordering = ["order", "urn"]
        verbose_name = "Code"
        verbose_name_plural = "Codes"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.urn and self.code_list_id and self.code_value:
            # Generate maintainable-scoped URN based on code_list and code_value
            parts = self.code_list_id.split(":")
            if len(parts) in (4, 5):
                agency = parts[2]
                cl_id = parts[3]
                ver = parts[4] if len(parts) == 5 else "1.0.0"
                self.urn = f"urn:ddi:{agency}:{cl_id}.{self.code_value}:{ver}"
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.code_value}: {self.category_id}"


class RepresentedVariableScheme(DDIScheme):
    """Named collection of represented variables (DDI-L RepresentedVariableScheme)."""

    class Meta:
        db_table = "request_ddi_representedvariablescheme"
        verbose_name = "Represented Variable Scheme"
        verbose_name_plural = "Represented Variable Schemes"


class RepresentedVariable(DDIResource):
    """Combination of conceptual variable and response code list representation.

    Represents the middle tier of the DDI variable cascade:
    ConceptualVariable -> RepresentedVariable -> InstanceVariable.
    Associated with QuestionItem entities via QuestionVariable.
    """

    scheme = models.ForeignKey(
        RepresentedVariableScheme,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="represented_variables",
        db_column="scheme_urn",
        help_text="Parent RepresentedVariableScheme defining this represented variable.",
    )
    conceptual_variable = models.ForeignKey(
        ConceptualVariable,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="represented_variables",
        db_column="conceptual_variable_urn",
        help_text="Parent conceptual variable.",
    )
    code_list = models.ForeignKey(
        CodeList,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="represented_variables",
        db_column="code_list_urn",
        help_text="Response code structure (null for open-ended questions).",
    )
    value_representation = models.JSONField(
        default=dict,
        blank=True,
        null=True,
        help_text=(
            "JSON object describing the value representation "
            "(e.g. {'type': 'code', 'code_list_urn': '...'}, {'type': 'numeric', ...})."
        ),
    )
    label = models.JSONField(
        default=list,
        blank=True,
        null=True,
        help_text="Multilingual short label as an array of objects.",
    )
    description = models.JSONField(
        default=list,
        blank=True,
        null=True,
        help_text="Multilingual description as an array of objects.",
    )
    extended_attributes = models.JSONField(
        default=list,
        blank=True,
        null=True,
        help_text="Extended attributes stored as an array of objects.",
    )

    class Meta:
        db_table = "request_ddi_representedvariable"
        verbose_name = "Represented Variable"
        verbose_name_plural = "Represented Variables"

    def save(self, *args, **kwargs) -> None:
        if self.code_list_id and not self.value_representation:
            self.value_representation = {"type": "code", "code_list_urn": self.code_list_id}
        elif (
            isinstance(self.value_representation, dict)
            and self.value_representation.get("type") == "code"
            and self.value_representation.get("code_list_urn")
            and not self.code_list_id
        ):
            self.code_list_id = self.value_representation["code_list_urn"]
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        if isinstance(self.name, list) and self.name:
            return self.name[0].get("value", self.urn)
        if isinstance(self.label, list) and self.label:
            return self.label[0].get("value", self.urn)
        return self.urn


class QuestionVariable(models.Model):
    """Junction associating QuestionItem with RepresentedVariable with referencing path."""

    question_item = models.ForeignKey(
        QuestionItem,
        on_delete=models.CASCADE,
        related_name="variable_associations",
        db_column="question_item_urn",
    )
    represented_variable = models.ForeignKey(
        RepresentedVariable,
        on_delete=models.CASCADE,
        related_name="question_associations",
        db_column="represented_variable_urn",
    )
    path = models.CharField(
        max_length=512,
        blank=True,
        default="",
        help_text="Referencing path from question to variable (e.g. XPath/DDI reference path).",
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order within the represented variable associations.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "request_ddi_questionvariable"
        unique_together = ("question_item", "represented_variable")
        ordering = ["order", "id"]
        verbose_name = "Question Variable"
        verbose_name_plural = "Question Variables"

    def __str__(self) -> str:
        return f"{self.question_item_id} -> {self.represented_variable_id} ({self.path})"
