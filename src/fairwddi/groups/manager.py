"""DDI Group & VariableGroup curation manager (`fairwddi.groups.manager`).

Provides CRUD and membership management for reusable context groups (longitudinal series,
thematic variable clusters, question grids, comparison scopes). Groups carry both a
canonical DDI URN and an optional unique human-friendly ``slug``, and keep their JSONB
``references`` list synchronized with ``dcterms:isPartOf`` ``SemanticRelationship`` triples.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from django.db import transaction

from fairwddi.utils.integrity import assert_can_delete, integrity_deletion_context
from fairwddi.utils.urn import generate_generic_urn, slugify, validate_ddi_urn


def _to_multilingual_dict(
    value: str | dict[str, str] | None, default_lang: str = "en"
) -> dict[str, str] | None:
    if value is None:
        return None
    if isinstance(value, dict):
        cleaned = {
            str(k).strip().lower(): str(v).strip() for k, v in value.items() if str(v).strip()
        }
        return cleaned or None
    text = str(value).strip()
    if not text:
        return None
    return {default_lang: text}


def _display_text(val: Any, fallback: str = "") -> str:
    if isinstance(val, dict) and val:
        for lang in ("fr", "en"):
            if lang in val and str(val[lang]).strip():
                return str(val[lang]).strip()
        return str(next(iter(val.values()))).strip()
    if isinstance(val, list) and val:
        first = val[0]
        if isinstance(first, dict) and first.get("value"):
            return str(first["value"]).strip()
    if isinstance(val, str) and val.strip():
        return val.strip()
    return fallback


def _normalize_slug(raw_slug: str) -> str:
    cleaned = re.sub(r"[^a-z0-9_-]+", "-", raw_slug.strip().lower()).strip("-")
    if not cleaned:
        raise ValueError(f"Slug '{raw_slug}' produces an empty slug after normalization.")
    if len(cleaned) > 128:
        cleaned = cleaned[:128].rstrip("-")
    return cleaned


def _derive_unique_slug(name_text: str, explicit_slug: str | None = None) -> str:
    from fairwddi.models import Group

    if explicit_slug is not None:
        candidate = _normalize_slug(explicit_slug)
        if Group.objects.filter(slug__iexact=candidate).exists():
            raise ValueError(f"A group with slug '{candidate}' already exists.")
        return candidate

    base = slugify(name_text, max_len=110)
    candidate = base
    counter = 2
    while Group.objects.filter(slug__iexact=candidate).exists():
        candidate = f"{base[:100]}-{counter}"
        counter += 1
    return candidate


def resolve_group(identifier: str) -> Any:
    """Resolve a ``Group`` by canonical DDI URN or case-insensitive ``slug``."""
    from fairwddi.models import Group

    token = (identifier or "").strip()
    if not token:
        raise ValueError("Group identifier cannot be empty.")

    group = None
    if token.startswith("urn:"):
        group = Group.objects.filter(urn=token).first()
    if group is None:
        group = Group.objects.filter(slug__iexact=token).first()
    if group is None and not token.startswith("urn:"):
        group = Group.objects.filter(urn=token).first()

    if group is None:
        raise ValueError(f"Group '{identifier}' not found (looked up by URN and slug).")
    return group


def _resolve_valid_members(
    member_urns: Sequence[str], *, exclude_group_urn: str | None = None
) -> list[dict[str, str]]:
    """Validate incoming member URNs against ``UrnRegistry`` and map to ref dicts."""
    from fairwddi.models import UrnRegistry

    ordered_urns: list[str] = []
    seen: set[str] = set()
    for raw in member_urns:
        u = str(raw).strip()
        if not u or u in seen:
            continue
        if exclude_group_urn and u == exclude_group_urn:
            raise ValueError(f"Group '{exclude_group_urn}' cannot reference itself.")
        seen.add(u)
        ordered_urns.append(u)

    if not ordered_urns:
        return []

    registry_map = {
        row["urn"]: row["resource_type"]
        for row in UrnRegistry.objects.filter(urn__in=ordered_urns).values("urn", "resource_type")
    }
    missing = [u for u in ordered_urns if u not in registry_map]
    if missing:
        raise ValueError(
            f"Member URN(s) not found in UrnRegistry: {', '.join(missing[:5])}"
            + (f" (+{len(missing) - 5} more)" if len(missing) > 5 else "")
        )

    return [{"resource_type": registry_map[u], "urn": u} for u in ordered_urns]


def _get_synced_member_refs(group: Any) -> list[dict[str, str]]:
    """Return deduplicated member list from JSONB references and ``dcterms:isPartOf`` links."""
    from fairwddi.models import SemanticRelationship, UrnRegistry

    by_urn: dict[str, dict[str, str]] = {}
    if isinstance(group.references, list):
        for ref in group.references:
            if isinstance(ref, dict) and ref.get("urn"):
                u = str(ref["urn"])
                by_urn[u] = {
                    "resource_type": str(ref.get("resource_type") or "Resource"),
                    "urn": u,
                }

    linked_urns = list(
        SemanticRelationship.objects.filter(
            predicate="dcterms:isPartOf",
            object_urn=group.urn,
        ).values_list("subject_urn", flat=True)
    )
    missing_from_refs = [u for u in linked_urns if u not in by_urn]
    if missing_from_refs:
        type_map = dict(
            UrnRegistry.objects.filter(urn__in=missing_from_refs).values_list(
                "urn", "resource_type"
            )
        )
        for u in missing_from_refs:
            by_urn[u] = {
                "resource_type": type_map.get(u, "Resource"),
                "urn": u,
            }

    return list(by_urn.values())


def create_group(
    name: str | dict[str, str],
    *,
    slug: str | None = None,
    group_type: str = "custom",
    description: str | dict[str, str] | None = None,
    urn: str | None = None,
    member_urns: Sequence[str] | None = None,
    agency: str | None = None,
    origin: str = "instantiated",
) -> dict[str, Any]:
    """Create a new DDI Group with canonical URN, unique short slug, and initial members."""
    from fairwddi.models import Group, SemanticRelationship, UrnRegistry

    name_ml = _to_multilingual_dict(name)
    if not name_ml:
        raise ValueError("Group name cannot be empty.")
    display_name = _display_text(name_ml, fallback="group")
    resolved_slug = _derive_unique_slug(display_name, explicit_slug=slug)
    desc_ml = _to_multilingual_dict(description)

    if urn is not None:
        if not validate_ddi_urn(urn):
            raise ValueError(f"Invalid canonical DDI URN: '{urn}'")
        if UrnRegistry.objects.filter(urn=urn).exists():
            raise ValueError(f"URN '{urn}' already exists in UrnRegistry.")
        group_urn = urn
    else:
        group_urn = generate_generic_urn("Group", resolved_slug or display_name, agency=agency)

    with transaction.atomic():
        member_refs = _resolve_valid_members(member_urns or [], exclude_group_urn=group_urn)
        group = Group.objects.create(
            urn=group_urn,
            slug=resolved_slug,
            name=name_ml,
            description=desc_ml,
            group_type=group_type,
            references=member_refs,
            origin=origin,
        )
        for ref in member_refs:
            SemanticRelationship.objects.get_or_create(
                subject_urn=ref["urn"],
                predicate="dcterms:isPartOf",
                object_urn=group.urn,
                defaults={
                    "subject_type": ref["resource_type"],
                    "object_type": "Group",
                    "extended_attributes": [
                        {"type": "group_type", "value": group_type},
                        {"type": "slug", "value": resolved_slug},
                    ],
                },
            )

    return get_group_details(group.urn)


def list_groups(group_type: str | None = None) -> list[dict[str, Any]]:
    """List all curated Groups, optionally filtered by ``group_type``."""
    from fairwddi.models import Group

    qs = Group.objects.all().order_by("slug", "urn")
    if group_type:
        qs = qs.filter(group_type=group_type)

    results: list[dict[str, Any]] = []
    for g in qs:
        refs = _get_synced_member_refs(g)
        results.append(
            {
                "urn": g.urn,
                "slug": g.slug,
                "name": _display_text(g.name, fallback=g.urn),
                "name_ml": g.name or {},
                "description": _display_text(g.description),
                "group_type": g.group_type,
                "origin": g.origin,
                "member_count": len(refs),
                "created_at": g.created_at.isoformat() if g.created_at else None,
            }
        )
    return results


def get_group_details(identifier: str) -> dict[str, Any]:
    """Return full details and member roster for a Group identified by URN or slug."""
    from fairwddi.models import UrnRegistry

    group = resolve_group(identifier)
    refs = _get_synced_member_refs(group)
    member_urns = [r["urn"] for r in refs]
    origin_map = dict(UrnRegistry.objects.filter(urn__in=member_urns).values_list("urn", "origin"))
    enriched_members = [
        {
            "urn": r["urn"],
            "resource_type": r["resource_type"],
            "origin": origin_map.get(r["urn"], "unknown"),
        }
        for r in refs
    ]
    return {
        "urn": group.urn,
        "slug": group.slug,
        "name": _display_text(group.name, fallback=group.urn),
        "name_ml": group.name or {},
        "description": _display_text(group.description),
        "description_ml": group.description or {},
        "group_type": group.group_type,
        "origin": group.origin,
        "member_count": len(enriched_members),
        "members": enriched_members,
        "created_at": group.created_at.isoformat() if group.created_at else None,
        "updated_at": group.updated_at.isoformat() if group.updated_at else None,
    }


def add_group_members(identifier: str, member_urns: Sequence[str]) -> dict[str, Any]:
    """Add one or more resources to a Group, syncing references and ``dcterms:isPartOf`` links."""
    from fairwddi.models import SemanticRelationship

    group = resolve_group(identifier)
    with transaction.atomic():
        new_refs = _resolve_valid_members(member_urns, exclude_group_urn=group.urn)
        existing_refs = _get_synced_member_refs(group)
        existing_urns = {r["urn"] for r in existing_refs}

        added = 0
        merged = list(existing_refs)
        for ref in new_refs:
            if ref["urn"] not in existing_urns:
                merged.append(ref)
                existing_urns.add(ref["urn"])
                added += 1
            SemanticRelationship.objects.get_or_create(
                subject_urn=ref["urn"],
                predicate="dcterms:isPartOf",
                object_urn=group.urn,
                defaults={
                    "subject_type": ref["resource_type"],
                    "object_type": "Group",
                    "extended_attributes": [
                        {"type": "group_type", "value": group.group_type},
                        {"type": "slug", "value": group.slug},
                    ],
                },
            )

        group.references = merged
        group.save(update_fields=["references", "updated_at"])

    return {
        "urn": group.urn,
        "slug": group.slug,
        "added_count": added,
        "member_count": len(merged),
    }


def remove_group_members(identifier: str, member_urns: Sequence[str]) -> dict[str, Any]:
    """Remove resources from a Group and prune their ``dcterms:isPartOf`` triples."""
    from fairwddi.models import SemanticRelationship

    group = resolve_group(identifier)
    to_remove = {str(u).strip() for u in member_urns if str(u).strip()}
    with transaction.atomic():
        existing_refs = _get_synced_member_refs(group)
        remaining = [r for r in existing_refs if r["urn"] not in to_remove]
        removed = len(existing_refs) - len(remaining)

        SemanticRelationship.objects.filter(
            subject_urn__in=to_remove,
            predicate="dcterms:isPartOf",
            object_urn=group.urn,
        ).delete()
        group.references = remaining
        group.save(update_fields=["references", "updated_at"])

    return {
        "urn": group.urn,
        "slug": group.slug,
        "removed_count": removed,
        "member_count": len(remaining),
    }


def rename_group(
    identifier: str,
    *,
    name: str | dict[str, str] | None = None,
    slug: str | None = None,
    description: str | dict[str, str] | None = None,
) -> dict[str, Any]:
    """Update a Group's display name, short slug, and/or description."""
    from fairwddi.models import Group

    group = resolve_group(identifier)
    updated_fields: list[str] = []

    if name is not None:
        name_ml = _to_multilingual_dict(name)
        if not name_ml:
            raise ValueError("Group name cannot be empty.")
        group.name = name_ml
        updated_fields.append("name")

    if slug is not None:
        norm_slug = _normalize_slug(slug)
        if Group.objects.filter(slug__iexact=norm_slug).exclude(urn=group.urn).exists():
            raise ValueError(f"A different group already uses slug '{norm_slug}'.")
        group.slug = norm_slug
        updated_fields.append("slug")

    if description is not None:
        group.description = _to_multilingual_dict(description)
        updated_fields.append("description")

    if updated_fields:
        updated_fields.append("updated_at")
        group.save(update_fields=updated_fields)

    return get_group_details(group.urn)


def delete_group(identifier: str) -> dict[str, Any]:
    """Delete a Group and its ``dcterms:isPartOf`` membership triples cleanly."""
    from fairwddi.models import SemanticRelationship

    group = resolve_group(identifier)
    group_urn = group.urn
    group_slug = group.slug

    with transaction.atomic():
        SemanticRelationship.objects.filter(
            object_urn=group_urn, predicate="dcterms:isPartOf"
        ).delete()
        SemanticRelationship.objects.filter(subject_urn=group_urn).delete()
        assert_can_delete(group_urn, ignore_urns={group_urn})
        with integrity_deletion_context(ignore_urns={group_urn}):
            group.delete()

    return {
        "urn": group_urn,
        "slug": group_slug,
        "deleted": True,
    }
