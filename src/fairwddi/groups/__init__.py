"""FAIRwDDI DDI Group Curation & Unified Resource Set Resolution (`fairwddi.groups`)."""

from __future__ import annotations

from fairwddi.groups.manager import (
    add_group_members,
    create_group,
    delete_group,
    get_group_details,
    list_groups,
    remove_group_members,
    rename_group,
    resolve_group,
)
from fairwddi.groups.resolver import (
    ResolvedResourceSet,
    ResourceSetSpec,
    parse_resource_set_spec,
    resolve_resource_set,
)

__all__ = [
    "resolve_group",
    "create_group",
    "list_groups",
    "get_group_details",
    "add_group_members",
    "remove_group_members",
    "rename_group",
    "delete_group",
    "ResourceSetSpec",
    "ResolvedResourceSet",
    "parse_resource_set_spec",
    "resolve_resource_set",
]
