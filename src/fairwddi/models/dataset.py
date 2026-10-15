"""Dataset Layer models for FAIRwDDI.

Includes StudyUnit (survey wave dataset), Datafile (data file entity relating
to StudyUnit), DatafileVariable (junction with column ordering),
InstanceVariableScheme, InstanceVariable (dataset column realization),
DatafileVariableFrequency (categorical count statistics),
DatafileVariableStatistic (descriptive statistics JSONB),
and StudyInstrument (study unit to instrument junction).
"""

from django.db import models

from fairwddi.models.base import DDIResource, DDIScheme
from fairwddi.models.representation import RepresentedVariable


class StudyUnit(DDIResource):
    """A specific survey wave or dataset (renamed from Survey)."""

    title = models.JSONField(
        default=list,
        blank=True,
        null=True,
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
        null=True,
        help_text="Multilingual study abstract/description as an array of objects.",
    )
    extended_attributes = models.JSONField(
        default=list,
        blank=True,
        null=True,
        help_text="Extended attributes stored as an array of objects.",
    )

    class Meta:
        db_table = "request_ddi_studyunit"
        verbose_name = "Study Unit"
        verbose_name_plural = "Study Units"

    def __str__(self) -> str:
        if isinstance(self.name, list) and self.name:
            return self.name[0].get("value", self.urn)
        if isinstance(self.title, list) and self.title:
            return self.title[0].get("value", self.urn)
        return self.urn


class Datafile(DDIResource):
    """A minimal Datafile entity relating InstanceVariables to a StudyUnit.

    A Datafile points to a StudyUnit and groups concrete dataset column
    InstanceVariables, replacing the legacy StudyVariable junction table.
    """

    study_unit = models.ForeignKey(
        StudyUnit,
        on_delete=models.CASCADE,
        related_name="datafiles",
        db_column="study_unit_urn",
        help_text="Study unit containing this datafile.",
    )
    description = models.JSONField(
        default=list,
        blank=True,
        null=True,
        help_text="Multilingual datafile description as an array of objects.",
    )
    extended_attributes = models.JSONField(
        default=list,
        blank=True,
        null=True,
        help_text="Extended attributes stored as an array of objects.",
    )

    class Meta:
        db_table = "request_ddi_datafile"
        verbose_name = "Datafile"
        verbose_name_plural = "Datafiles"

    @property
    def study(self) -> StudyUnit:
        """Alias returning parent StudyUnit."""
        return self.study_unit

    def __str__(self) -> str:
        if isinstance(self.name, list) and self.name:
            return self.name[0].get("value", self.urn)
        return self.urn


# Alias for canonical DDI PascalCase
DataFile = Datafile


class InstanceVariableScheme(DDIScheme):
    """Named collection of instance variables (DDI-L InstanceVariableScheme)."""

    class Meta:
        db_table = "request_ddi_instancevariablescheme"
        verbose_name = "Instance Variable Scheme"
        verbose_name_plural = "Instance Variable Schemes"


class InstanceVariable(DDIResource):
    """Physical realization of a variable in a specific dataset.

    Represents the bottom tier of the DDI variable cascade:
    ConceptualVariable -> RepresentedVariable -> InstanceVariable.
    Relates to StudyUnit via its containing Datafile and DatafileVariable junction.
    """

    scheme = models.ForeignKey(
        InstanceVariableScheme,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="instance_variables",
        db_column="scheme_urn",
        help_text="Parent InstanceVariableScheme defining this instance variable.",
    )
    datafiles = models.ManyToManyField(
        Datafile,
        through="DatafileVariable",
        related_name="instance_variables",
        blank=True,
        help_text="Datafiles containing this instance variable.",
    )
    represented_variable = models.ForeignKey(
        RepresentedVariable,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="instance_variables",
        db_column="represented_variable_urn",
    )
    label = models.JSONField(
        default=list,
        blank=True,
        null=True,
        help_text="Multilingual variable label as an array of objects.",
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
        db_table = "request_ddi_instancevariable"
        verbose_name = "Instance Variable"
        verbose_name_plural = "Instance Variables"

    @property
    def datafile(self) -> Datafile | None:
        """First containing Datafile if associated."""
        return self.datafiles.first()

    @datafile.setter
    def datafile(self, df: Datafile | None) -> None:
        """Associate primary Datafile via DatafileVariable junction."""
        if df is not None and self.pk:
            DatafileVariable.objects.get_or_create(datafile=df, instance_variable=self)


class DatafileVariable(models.Model):
    """Junction linking a Datafile to its InstanceVariable(s) with column ordering."""

    datafile = models.ForeignKey(
        Datafile,
        on_delete=models.CASCADE,
        related_name="datafile_variables",
        db_column="datafile_urn",
        help_text="Datafile containing this variable.",
    )
    instance_variable = models.ForeignKey(
        InstanceVariable,
        on_delete=models.CASCADE,
        related_name="datafile_variables",
        db_column="instance_variable_urn",
        help_text="Instance variable column in this datafile.",
    )
    order = models.IntegerField(
        default=0,
        help_text="Display order or column index of the variable within the datafile.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "request_ddi_datafilevariable"
        unique_together = ("datafile", "instance_variable")
        ordering = ["order", "id"]
        verbose_name = "Datafile Variable"
        verbose_name_plural = "Datafile Variables"

    def __str__(self) -> str:
        return f"{self.datafile_id} -> {self.instance_variable_id} [order={self.order}]"


class DatafileVariableFrequency(models.Model):
    """Stores categorical variable count statistics.

    Captures response frequencies per code value for an instance variable
    within a specific datafile, with optional weighting specifications.
    """

    datafile = models.ForeignKey(
        Datafile,
        on_delete=models.CASCADE,
        related_name="frequencies",
        db_column="datafile_urn",
        help_text="Datafile containing the variable and observations.",
    )
    instance_variable = models.ForeignKey(
        InstanceVariable,
        on_delete=models.CASCADE,
        related_name="frequencies",
        db_column="instance_variable_urn",
        help_text="Instance variable measured.",
    )
    code_value = models.CharField(
        max_length=128,
        help_text="Discrete code value as string (e.g. '1', '98', 'DK').",
    )
    frequency = models.FloatField(
        help_text="Count or frequency statistic of the code value.",
    )
    weight = models.CharField(
        max_length=256,
        null=True,
        blank=True,
        help_text="Optional weight variable name, URN, or weighting specification.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "request_ddi_datafilevariablefrequency"
        verbose_name = "Datafile Variable Frequency"
        verbose_name_plural = "Datafile Variable Frequencies"
        indexes = [
            models.Index(fields=["datafile", "instance_variable"]),
            models.Index(fields=["instance_variable", "code_value"]),
        ]

    def __str__(self) -> str:
        w_str = f" (weight={self.weight})" if self.weight else ""
        return (
            f"{self.datafile_id}:{self.instance_variable_id} "
            f"[{self.code_value}]: {self.frequency}{w_str}"
        )


# Aliases for backward compatibility
Frequency = DatafileVariableFrequency
VariableFrequency = DatafileVariableFrequency


class DatafileVariableStatistic(models.Model):
    """Stores descriptive statistics for a continuous or summary variable.

    Captures statistical summary metrics (e.g. mean, median, min, max, stddev, valid/missing cases)
    for an instance variable within a specific datafile, with optional weighting.
    The statistics JSONB field holds an object with statistics ID and value pairs.
    """

    datafile = models.ForeignKey(
        Datafile,
        on_delete=models.CASCADE,
        related_name="statistics",
        db_column="datafile_urn",
        help_text="Datafile containing the variable and observations.",
    )
    instance_variable = models.ForeignKey(
        InstanceVariable,
        on_delete=models.CASCADE,
        related_name="statistics",
        db_column="instance_variable_urn",
        help_text="Instance variable measured.",
    )
    statistics = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Descriptive statistics object mapping statistic ID/type to value "
            "(e.g. {'mean': 3.4, 'min': 1.0, 'max': 5.0, 'stddev': 1.1})."
        ),
    )
    weight = models.CharField(
        max_length=256,
        null=True,
        blank=True,
        help_text="Optional weight variable name, URN, or weighting specification.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "request_ddi_datafilevariablestatistic"
        verbose_name = "Datafile Variable Statistic"
        verbose_name_plural = "Datafile Variable Statistics"
        indexes = [
            models.Index(fields=["datafile", "instance_variable"]),
        ]

    def __str__(self) -> str:
        w_str = f" (weight={self.weight})" if self.weight else ""
        return (
            f"{self.datafile_id}:{self.instance_variable_id} "
            f"stats: {list(self.statistics.keys())}{w_str}"
        )


# Aliases for backward compatibility
VariableStatistic = DatafileVariableStatistic
DatafileStatistic = DatafileVariableStatistic


class StudyInstrument(models.Model):
    """Junction linking a StudyUnit to its Instrument(s) with path."""

    study_unit = models.ForeignKey(
        StudyUnit,
        on_delete=models.CASCADE,
        related_name="study_instruments",
        db_column="study_unit_urn",
        help_text="Study unit that used this instrument.",
    )
    instrument = models.ForeignKey(
        "fairwddi.Instrument",
        on_delete=models.CASCADE,
        related_name="study_associations",
        db_column="instrument_urn",
        help_text="Instrument used by the study unit.",
    )
    path = models.CharField(
        max_length=512,
        blank=True,
        default="",
        help_text="Referencing path from study unit to instrument.",
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order or sequence number of the instrument within the study unit.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "request_ddi_studyinstrument"
        unique_together = ("study_unit", "instrument")
        ordering = ["order", "id"]
        verbose_name = "Study Instrument"
        verbose_name_plural = "Study Instruments"

    def __str__(self) -> str:
        return f"{self.study_unit_id} -> {self.instrument_id}" + (
            f" ({self.path})" if self.path else ""
        )


# Alias
StudyUnitInstrument = StudyInstrument
