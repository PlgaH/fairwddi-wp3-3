"""Representation Layer models for FAIRwDDI.

Includes QuestionItem, Category, CategorySet, CategorySetItem, CodeList, CodeItem,
and RepresentedVariable.
"""

from django.db import models

from fairwddi.models.base import DDIIdentifiable
from fairwddi.models.concept import ConceptualVariable


class QuestionItem(DDIIdentifiable):
    """Standalone reusable question text with interviewer instructions."""

    question_text = models.JSONField(
        default=list,
        help_text="Multilingual literal question text: [{'lang': 'fr', 'value': '...'}].",
    )
    pre_question_text = models.JSONField(
        default=list,
        blank=True,
        help_text="Multilingual introductory text / routing preamble.",
    )
    post_question_text = models.JSONField(
        default=list,
        blank=True,
        help_text="Multilingual post-question transition text.",
    )
    interviewer_instructions = models.JSONField(
        default=list,
        blank=True,
        help_text="Multilingual interviewer guidance.",
    )

    class Meta:
        db_table = "request_ddi_questionitem"
        verbose_name = "Question Item"
        verbose_name_plural = "Question Items"

    def __str__(self) -> str:
        if isinstance(self.question_text, list) and self.question_text:
            return self.question_text[0].get("value", self.urn or str(self.pk))
        return self.urn or str(self.pk)


class Category(DDIIdentifiable):
    """Response category text label (decoupled from numerical code values)."""

    label = models.JSONField(
        default=list,
        help_text="Multilingual category label: [{'lang': 'fr', 'value': 'Tout à fait d'accord'}].",
    )

    class Meta:
        db_table = "request_ddi_category"
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self) -> str:
        if isinstance(self.label, list) and self.label:
            return self.label[0].get("value", self.urn or str(self.pk))
        return self.urn or str(self.pk)


class CategorySet(DDIIdentifiable):
    """Named collection of reusable categories (maps to DDI-L CategoryScheme)."""

    name = models.JSONField(
        default=list,
        help_text="Multilingual name for the category set.",
    )
    description = models.JSONField(
        default=list,
        blank=True,
        help_text="Multilingual description.",
    )

    class Meta:
        db_table = "request_ddi_categoryset"
        verbose_name = "Category Set"
        verbose_name_plural = "Category Sets"

    def __str__(self) -> str:
        if isinstance(self.name, list) and self.name:
            return self.name[0].get("value", self.urn or str(self.pk))
        return self.urn or str(self.pk)


class CategorySetItem(models.Model):
    """Junction connecting a CategorySet to member Category entities with explicit ordering."""

    category_set = models.ForeignKey(
        CategorySet,
        on_delete=models.CASCADE,
        related_name="items",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="category_set_memberships",
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order within the category set.",
    )

    class Meta:
        db_table = "request_ddi_categorysetitem"
        unique_together = ("category_set", "category")
        ordering = ["order", "id"]
        verbose_name = "Category Set Item"
        verbose_name_plural = "Category Set Items"

    def __str__(self) -> str:
        return f"{self.category_set_id} -> {self.category_id} (order={self.order})"


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
    category_set = models.ForeignKey(
        CategorySet,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="code_lists",
        help_text="Optional link to parent CategorySet scheme.",
    )

    class Meta:
        db_table = "request_ddi_codelist"
        verbose_name = "Code List"
        verbose_name_plural = "Code Lists"

    def __str__(self) -> str:
        if isinstance(self.name, list) and self.name:
            return self.name[0].get("value", self.urn or str(self.pk))
        return self.urn or str(self.pk)


class CodeItem(models.Model):
    """Junction connecting a CodeList to a Category with a specific numerical code value."""

    code_list = models.ForeignKey(
        CodeList,
        on_delete=models.CASCADE,
        related_name="items",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="code_memberships",
    )
    code_value = models.CharField(
        max_length=64,
        help_text="The numerical or string code (e.g. '1', '98', 'Refused').",
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order within the code list.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "request_ddi_codeitem"
        unique_together = ("code_list", "code_value")
        ordering = ["order", "id"]
        verbose_name = "Code Item"
        verbose_name_plural = "Code Items"

    def __str__(self) -> str:
        return f"{self.code_value}: {self.category_id}"


class RepresentedVariable(DDIIdentifiable):
    """Combination of question wording and response code list linked to a conceptual variable.

    Represents the middle tier of the DDI variable cascade:
    ConceptualVariable -> RepresentedVariable -> InstanceVariable.
    """

    conceptual_variable = models.ForeignKey(
        ConceptualVariable,
        on_delete=models.CASCADE,
        related_name="represented_variables",
        help_text="Parent conceptual variable.",
    )
    question_item = models.ForeignKey(
        QuestionItem,
        on_delete=models.CASCADE,
        related_name="represented_variables",
        help_text="Reusable question text component.",
    )
    code_list = models.ForeignKey(
        CodeList,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="represented_variables",
        help_text="Response code structure (null for open-ended questions).",
    )
    label = models.JSONField(
        default=list,
        blank=True,
        help_text="Multilingual short label as an array of objects.",
    )

    class Meta:
        db_table = "request_ddi_representedvariable"
        verbose_name = "Represented Variable"
        verbose_name_plural = "Represented Variables"

    def __str__(self) -> str:
        if isinstance(self.label, list) and self.label:
            return self.label[0].get("value", self.urn or str(self.pk))
        return self.urn or str(self.pk)
