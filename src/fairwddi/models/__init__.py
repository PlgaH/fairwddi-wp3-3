"""FAIRwDDI Django ORM models package."""

from fairwddi.models.base import DDIIdentifiable, DDIResource, DDIScheme
from fairwddi.models.concept import (
    Concept,
    ConceptScheme,
    ConceptualVariable,
    ConceptualVariableScheme,
    SemanticRelationship,
)
from fairwddi.models.dataset import (
    DataFile,
    Datafile,
    DatafileVariable,
    DatafileVariableFrequency,
    Frequency,
    InstanceVariable,
    InstanceVariableScheme,
    StudyInstrument,
    StudyUnit,
    StudyUnitInstrument,
    VariableFrequency,
)
from fairwddi.models.event import (
    EventLog,
)
from fairwddi.models.infrastructure import (
    IngestBatch,
    MetadataQuarantine,
    URNAlias,
    UrnRegistry,
)
from fairwddi.models.instrument import (
    Instrument,
    InstrumentQuestion,
)
from fairwddi.models.organization import (
    Group,
    Organization,
)
from fairwddi.models.representation import (
    Category,
    CategoryScheme,
    Code,
    CodeItem,
    CodeList,
    QuestionItem,
    QuestionScheme,
    QuestionVariable,
    RepresentedVariable,
    RepresentedVariableScheme,
)

VariableGroup = Group
VariableScheme = InstanceVariableScheme

__all__ = [
    "DDIIdentifiable",
    "DDIScheme",
    "DDIResource",
    "Organization",
    "Group",
    "VariableGroup",
    "ConceptScheme",
    "Concept",
    "ConceptualVariableScheme",
    "ConceptualVariable",
    "SemanticRelationship",
    "QuestionScheme",
    "QuestionItem",
    "QuestionVariable",
    "Instrument",
    "InstrumentQuestion",
    "CategoryScheme",
    "Category",
    "CodeList",
    "Code",
    "CodeItem",
    "RepresentedVariableScheme",
    "RepresentedVariable",
    "StudyUnit",
    "Datafile",
    "DataFile",
    "DatafileVariable",
    "InstanceVariableScheme",
    "VariableScheme",
    "InstanceVariable",
    "DatafileVariableFrequency",
    "Frequency",
    "VariableFrequency",
    "StudyInstrument",
    "StudyUnitInstrument",
    "EventLog",
    "UrnRegistry",
    "URNAlias",
    "MetadataQuarantine",
    "IngestBatch",
]
