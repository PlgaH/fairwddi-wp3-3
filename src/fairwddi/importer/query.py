"""Query and statistics helpers for the FAIRwDDI Staging Layer.

Provides inspection, filtering, cross-tabulation, and progress metrics
for staged imports and individual resource nodes.
"""

from __future__ import annotations

from typing import Any


def get_import_statistics(import_id: int) -> dict[str, Any]:
    """Retrieve detailed statistics and status breakdowns for a specific staged import.

    Args:
        import_id: Primary key of the StagedImport.

    Returns:
        Structured statistics dictionary containing resource breakdowns,
        harmonization progress, and downstream links.

    Raises:
        ValueError: If StagedImport with the given ID does not exist.
    """
    from django.db.models import Count

    from fairwddi.models import MetadataQuarantine, StagedImport, StagedResourceNode, URNAlias

    staged_import = StagedImport.objects.filter(id=import_id).first()
    if not staged_import:
        raise ValueError(f"StagedImport #{import_id} does not exist.")

    nodes = StagedResourceNode.objects.filter(staged_import=staged_import)
    total_resources = nodes.count()

    # Breakdown by resource type
    by_type = dict(
        nodes.values("resource_type")
        .annotate(count=Count("id"))
        .order_by("-count")
        .values_list("resource_type", "count")
    )

    # Breakdown by status
    by_status = dict(
        nodes.values("status")
        .annotate(count=Count("id"))
        .order_by("-count")
        .values_list("status", "count")
    )

    # Detailed cross-tabulation (resource_type x status)
    cross_tab_raw = (
        nodes.values("resource_type", "status")
        .annotate(count=Count("id"))
        .order_by("resource_type", "status")
    )
    cross_tab: dict[str, dict[str, int]] = {}
    for row in cross_tab_raw:
        rt = row["resource_type"]
        st = row["status"]
        cross_tab.setdefault(rt, {})[st] = row["count"]

    # Normalization metrics
    normalized_count = by_status.get("normalized", 0)
    normalization_pct = (
        round((normalized_count / total_resources) * 100, 1) if total_resources > 0 else 0.0
    )

    # Downstream URNAlias metrics
    raw_urns = list(nodes.values_list("raw_urn", flat=True))
    alias_count = URNAlias.objects.filter(alias_urn__in=raw_urns).count() if raw_urns else 0

    # Quarantine metrics
    quarantine_count = (
        MetadataQuarantine.objects.filter(incoming_urn__in=raw_urns).count() if raw_urns else 0
    )

    return {
        "staged_import_id": staged_import.id,
        "file_name": staged_import.file_name,
        "source_format": staged_import.source_format,
        "status": staged_import.status,
        "total_resources": total_resources,
        "normalized_count": normalized_count,
        "normalization_progress_pct": normalization_pct,
        # Backwards-compatible aliases
        "harmonized_count": normalized_count,
        "harmonization_progress_pct": normalization_pct,
        "alias_count": alias_count,
        "quarantine_count": quarantine_count,
        "counts_by_type": by_type,
        "counts_by_status": by_status,
        "cross_tab": cross_tab,
        "created_at": staged_import.created_at.isoformat() if staged_import.created_at else None,
        "processed_at": (
            staged_import.processed_at.isoformat() if staged_import.processed_at else None
        ),
        "import_options": staged_import.import_options,
    }


MARKDOWN_STATS_TEMPLATE = """# Import #{{ staged_import_id }} Statistics Report

- **File Name:** `{{ file_name }}`
- **Specification:** {{ source_format }}
- **Status:** `{{ status }}`
- **Created At:** {{ created_at }}
{% if processed_at %}- **Processed At:** {{ processed_at }}
{% endif %}

---

## High-Level Summary

| Metric | Value |
| :--- | :--- |
| **Total Staged Resources** | {{ "{:,}".format(total_resources) }} |
| **Normalized Resources** | {{ "{:,}".format(normalized_count) }} |
| **Normalization Progress** | {{ normalization_progress_pct }}% |
| **Downstream URN Aliases** | {{ "{:,}".format(alias_count) }} |
| **Quarantined Collisions** | {{ "{:,}".format(quarantine_count) }} |

---

## Resource Types & Status Breakdown

| Resource Type | Total | Staged | Normalized | Quarantined |
| :--- | :---: | :---: | :---: | :---: |
{% for r_type, total in counts_by_type.items() -%}
{% set breakdown = cross_tab.get(r_type, {}) -%}
| **{{ r_type }}** | {{ "{:,}".format(total) }} \
| {{ "{:,}".format(breakdown.get('staged', 0)) }} \
| {{ "{:,}".format(breakdown.get('normalized', 0)) }} \
| {{ "{:,}".format(breakdown.get('quarantined', 0)) }} |
{% endfor %}"""


def render_statistics_json(stats: dict[str, Any], indent: int = 2) -> str:
    """Render a statistics dictionary as pretty-printed JSON.

    Args:
        stats: Statistics dictionary from get_import_statistics.
        indent: JSON indentation spaces.

    Returns:
        Formatted JSON string.
    """
    import json

    return json.dumps(stats, indent=indent)


def render_statistics_markdown(stats: dict[str, Any]) -> str:
    """Render a statistics dictionary as GitHub-Flavored Markdown via Jinja2.

    Args:
        stats: Statistics dictionary from get_import_statistics.

    Returns:
        Formatted Markdown report string.
    """
    from jinja2 import Template

    template = Template(MARKDOWN_STATS_TEMPLATE)
    return template.render(**stats)


def get_import_statistics_as_json(import_id: int, indent: int = 2) -> str:
    """Retrieve and serialize import statistics directly as JSON."""
    stats = get_import_statistics(import_id)
    return render_statistics_json(stats, indent=indent)


def get_import_statistics_as_markdown(import_id: int) -> str:
    """Retrieve and render import statistics directly as Markdown."""
    stats = get_import_statistics(import_id)
    return render_statistics_markdown(stats)


def list_staged_imports(
    status: str | None = None,
    source_format: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List staged imports with high-level summary counts.

    Args:
        status: Optional filter by status ('staged', 'harmonized', 'quarantined', 'failed').
        source_format: Optional substring filter by source format (e.g. 'ddi_l', 'ddi_c').
        limit: Max imports to return.
        offset: Pagination offset.

    Returns:
        List of import summary dictionaries.
    """
    from fairwddi.models import StagedImport

    qs = StagedImport.objects.all().order_by("-id")
    if status:
        qs = qs.filter(status__iexact=status)
    if source_format:
        qs = qs.filter(source_format__icontains=source_format)

    items = list(qs[offset : offset + limit])
    results = []
    for imp in items:
        results.append(
            {
                "id": imp.id,
                "file_name": imp.file_name,
                "source_format": imp.source_format,
                "status": imp.status,
                "total_resources": imp.total_resources,
                "processed_resources": imp.processed_resources,
                "created_at": imp.created_at.isoformat() if imp.created_at else None,
                "processed_at": (imp.processed_at.isoformat() if imp.processed_at else None),
                "log_file": imp.import_options.get("log_file"),
            }
        )
    return results


def query_staged_resources(
    import_id: int | None = None,
    resource_type: str | None = None,
    status: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Query and filter staged resource nodes with pagination.

    Args:
        import_id: Optional StagedImport PK to filter by.
        resource_type: Optional resource type (e.g. 'QuestionItem', 'Variable').
        status: Optional status ('staged', 'harmonized', 'quarantined', 'failed').
        search: Optional substring search against raw_urn or canonical_urn.
        limit: Max results to return.
        offset: Pagination offset.

    Returns:
        Dict containing total matching count, page items, and pagination metadata.
    """
    from django.db.models import Q

    from fairwddi.models import StagedResourceNode

    qs = StagedResourceNode.objects.all().order_by("id")

    if import_id is not None:
        qs = qs.filter(staged_import_id=import_id)
    if resource_type:
        qs = qs.filter(resource_type__iexact=resource_type)
    if status:
        qs = qs.filter(status__iexact=status)
    if search:
        qs = qs.filter(Q(raw_urn__icontains=search) | Q(canonical_urn__icontains=search))

    total_count = qs.count()
    items_page = list(qs[offset : offset + limit])

    results = []
    for node in items_page:
        results.append(
            {
                "id": node.id,
                "staged_import_id": node.staged_import_id,
                "resource_type": node.resource_type,
                "raw_urn": node.raw_urn,
                "canonical_urn": node.canonical_urn,
                "status": node.status,
                "raw_value": node.raw_value,
                "created_at": node.created_at.isoformat() if node.created_at else None,
            }
        )

    return {
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
        "results": results,
    }
