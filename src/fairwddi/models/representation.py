"""Representation Layer models for FAIRwDDI.

Includes QuestionItem, QuestionGroup, QuestionGroupItem, Category, CategoryScheme,
CategorySchemeItem, CodeList, Code, RepresentedVariable, and QuestionVariable.
"""

from django.db import models

from fairwddi.models.base import DDIIdentifiable
from fairwddi.models.concept import ConceptualVariable


class QuestionItem(DDIIdentifiable):
    """Standalone reusable question text."""

    question_text = models.JSONField(
        default=list,
        help_text="Multilingual literal question text: [{'lang': 'fr', 'value': '...'}].",
    )
    extended_attributes = models.JSONField(
        default=list,
        blank=True,
        help_text="Extended attributes stored as an array of objects.",
    )

    class Meta:
        db_table = "request_ddi_questionitem"
        verbose_name = "Question Item"
        verbose_name_plural = "Question Items"

    def __str__(self) -> str:
        if isinstance(self.question_text, list) and self.question_text:
            return self.question_text[0].get("value", self.urn)
        return self.urn


class QuestionGroup(DDIIdentifiable):
    """Grouping of related QuestionItem entities."""

    label = models.JSONField(
        default=list,
        help_text="Multilingual group title/label stored as an array of objects.",
    )
    description = models.JSONField(
        default=list,
        blank=True,
        help_text="Multilingual group description as an array of objects.",
    )
    parent_group = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subgroups",
        db_column="parent_group_urn",
        help_text="Optional parent group for hierarchical question groups.",
    )
    extended_attributes = models.JSONField(
        default=list,
        blank=True,
        help_text="Extended attributes stored as an array of objects.",
    )

    class Meta:
        db_table = "request_ddi_questiongroup"
        verbose_name = "Question Group"
        verbose_name_plural = "Question Groups"

    def __str__(self) -> str:
        if isinstance(self.label, list) and self.label:
            return self.label[0].get("value", self.urn)
        return self.urn


class QuestionGroupItem(models.Model):
    """Junction connecting QuestionGroup to member QuestionItem entities with explicit ordering."""

    question_group = models.ForeignKey(
        QuestionGroup,
        on_delete=models.CASCADE,
        related_name="items",
        db_column="question_group_urn",
    )
    question_item = models.ForeignKey(
        QuestionItem,
        on_delete=models.CASCADE,
        related_name="group_memberships",
        db_column="question_item_urn",
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order within the question group.",
    )

    class Meta:
        db_table = "request_ddi_questiongroupitem"
        unique_together = ("question_group", "question_item")
        ordering = ["order", "id"]
        verbose_name = "Question Group Item"
        verbose_name_plural = "Question Group Items"

    def __str__(self) -> str:
        return f"{self.question_group_id} -> {self.question_item_id} (order={self.order})"


class Category(DDIIdentifiable):
    """Response category text label (decoupled from numerical code values)."""

    label = models.JSONField(
        default=list,
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
    extended_attributes = models.JSONField(
        default=list,
        blank=True,
        help_text="Extended attributes stored as an array of objects.",
    )

    class Meta:
        db_table = "request_ddi_category"
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self) -> str:
        if isinstance(self.label, list) and self.label:
            return self.label[0].get("value", self.urn)
        return self.urn


class CategoryScheme(DDIIdentifiable):
    """Named collection of reusable categories (maps to DDI-L CategoryScheme)."""

    name = models.JSONField(
        default=list,
        help_text="Multilingual name for the category scheme.",
    )
    description = models.JSONField(
        default=list,
        blank=True,
        help_text="Multilingual description.",
    )
    extended_attributes = models.JSONField(
        default=list,
        blank=True,
        help_text="Extended attributes stored as an array of objects.",
    )

    class Meta:
        db_table = "request_ddi_categoryscheme"
        verbose_name = "Category Scheme"
        verbose_name_plural = "Category Schemes"

    def __str__(self) -> str:
        if isinstance(self.name, list) and self.name:
            return self.name[0].get("value", self.urn)
        return self.urn


class CategorySchemeItem(models.Model):
    """Junction connecting a CategoryScheme to member Category entities with explicit ordering."""

    category_scheme = models.ForeignKey(
        CategoryScheme,
        on_delete=models.CASCADE,
        related_name="items",
        db_column="category_scheme_urn",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="category_scheme_memberships",
        db_column="category_urn",
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order within the category scheme.",
    )

    class Meta:
        db_table = "request_ddi_categoryschemeitem"
        unique_together = ("category_scheme", "category")
        ordering = ["order", "id"]
        verbose_name = "Category Scheme Item"
        verbose_name_plural = "Category Scheme Items"

    def __str__(self) -> str:
        return f"{self.category_scheme_id} -> {self.category_id} (order={self.order})"


class CodeList(DDIIdentifiable):
    """Structural set of response codes linked to categories."""

    name = models.JSONField(
        default=list,
        blank=True,
        help_text="Multilingual human title for the code list.",
    )
    description = models.JSONField(
        default=list,
        blank=True,
        help_text="Multilingual description.",
    )
    category_scheme = models.ForeignKey(
        CategoryScheme,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="code_lists",
        db_column="category_scheme_urn",
        help_text="Optional link to parent CategoryScheme.",
    )
    extended_attributes = models.JSONField(
        default=list,
        blank=True,
        help_text="Extended attributes stored as an array of objects.",
    )

    class Meta:
        db_table = "request_ddi_codelist"
        verbose_name = "Code List"
        verbose_name_plural = "Code Lists"

    def __str__(self) -> str:
        if isinstance(self.name, list) and self.name:
            return self.name[0].get("value", self.urn)
        return self.urn


class Code(models.Model):
    """Junction connecting a CodeList to a Category with a code value (DDI Code)."""

    code_list = models.ForeignKey(
        CodeList,
        on_delete=models.CASCADE,
        related_name="codes",
        db_column="code_list_urn",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="code_memberships",
        db_column="category_urn",
    )
    code_value = models.CharField(
        max_length=64,
        help_text="The numerical or string code (e.g. '1', '98', 'Refused').",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        db_column="parent_id",
        help_text="Parent code for hierarchical code schemes.",
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order within the code list.",
    )
    extended_attributes = models.JSONField(
        default=list,
        blank=True,
        help_text="Extended attributes stored as an array of objects.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "request_ddi_code"
        unique_together = ("code_list", "code_value")
        ordering = ["order", "id"]
        verbose_name = "Code"
        verbose_name_plural = "Codes"

    def __str__(self) -> str:
        return f"{self.code_value}: {self.category_id}"


class RepresentedVariable(DDIIdentifiable):
    """Combination of conceptual variable and response code list representation.

    Represents the middle tier of the DDI variable cascade:
    ConceptualVariable -> RepresentedVariable -> InstanceVariable.
    Associated with QuestionItem entities via QuestionVariable.
    """

    conceptual_variable = models.ForeignKey(
        ConceptualVariable,
        on_delete=models.CASCADE,
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
    label = models.JSONField(
        default=list,
        blank=True,
        help_text="Multilingual short label as an array of objects.",
    )
    extended_attributes = models.JSONField(
        default=list,
        blank=True,
        help_text="Extended attributes stored as an array of objects.",
    )

    class Meta:
        db_table = "request_ddi_representedvariable"
        verbose_name = "Represented Variable"
        verbose_name_plural = "Represented Variables"

    def __str__(self) -> str:
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
