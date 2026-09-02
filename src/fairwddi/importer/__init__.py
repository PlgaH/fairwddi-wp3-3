"""FAIRwDDI Metadata Importer package.

Provides high-performance streaming ingestion, format auto-detection,
YAML/JSON import profiles, and duplicate/drift resolution.
"""

from fairwddi.importer.detector import (
    MetadataFormatInfo,
    detect_metadata_format,
)
from fairwddi.importer.importer import (
    ProtectedImportError,
    compute_file_sha256,
    delete_staged_import,
    import_metadata_file,
)
from fairwddi.importer.logging import ImportSessionLogger
from fairwddi.importer.profiles import (
    ImportProfile,
    ImportStrategies,
    list_available_profiles,
    load_profile,
)
from fairwddi.importer.query import (
    get_import_statistics,
    get_import_statistics_as_json,
    get_import_statistics_as_markdown,
    list_staged_imports,
    query_staged_resources,
    render_statistics_json,
    render_statistics_markdown,
)
from fairwddi.importer.streaming import (
    RawResourceNode,
    stream_ddi_c_xml,
    stream_ddi_l_json,
    stream_ddi_l_xml,
    stream_resources,
)

__all__ = [
    "MetadataFormatInfo",
    "detect_metadata_format",
    "ImportProfile",
    "ImportStrategies",
    "load_profile",
    "list_available_profiles",
    "ImportSessionLogger",
    "RawResourceNode",
    "stream_resources",
    "stream_ddi_l_xml",
    "stream_ddi_l_json",
    "stream_ddi_c_xml",
    "import_metadata_file",
    "delete_staged_import",
    "ProtectedImportError",
    "compute_file_sha256",
    "get_import_statistics",
    "get_import_statistics_as_json",
    "get_import_statistics_as_markdown",
    "render_statistics_json",
    "render_statistics_markdown",
    "list_staged_imports",
    "query_staged_resources",
]
