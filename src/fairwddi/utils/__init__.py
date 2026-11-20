"""FAIRwDDI utility functions."""

from fairwddi.utils.integrity import (
    ResourceReferencedError,
    assert_can_delete,
    get_resource_references,
    integrity_deletion_context,
)
from fairwddi.utils.normalize_string import (
    normalize_string,
    normalize_string_for_comparison,
    normalize_string_for_database,
)
from fairwddi.utils.urn import (
    PREFIX_MAP,
    generate_generic_urn,
    slugify,
    validate_ddi_urn,
)

__all__ = [
    "ResourceReferencedError",
    "assert_can_delete",
    "get_resource_references",
    "integrity_deletion_context",
    "normalize_string",
    "normalize_string_for_comparison",
    "normalize_string_for_database",
    "validate_ddi_urn",
    "generate_generic_urn",
    "slugify",
    "PREFIX_MAP",
]
