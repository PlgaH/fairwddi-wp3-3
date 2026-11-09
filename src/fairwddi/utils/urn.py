"""Canonical DDI URN validation, slugification, and generic identifier generation."""

from __future__ import annotations

import os
import re
import unicodedata
import uuid

PREFIX_MAP: dict[str, str] = {
    "QuestionItem": "QI",
    "RepresentedVariable": "RV",
    "ConceptualVariable": "CV",
    "CodeList": "CL",
    "Category": "CAT",
    "Concept": "CON",
    "StudyUnit": "SU",
    "Instrument": "INS",
    "Group": "GRP",
    "VariableGroup": "VG",
    "ConceptScheme": "CS",
    "QuestionScheme": "QS",
    "CategoryScheme": "CATS",
    "CodeListScheme": "CLS",
    "RepresentedVariableScheme": "RVS",
    "ConceptualVariableScheme": "CVS",
    "VariableScheme": "VS",
    "InstanceVariableScheme": "IVS",
}


def slugify(value: str | None, max_len: int = 36) -> str:
    """Convert arbitrary text into a clean, lower-case, URL/URN-safe slug."""
    if not value or not isinstance(value, str):
        return "generic"

    text = unicodedata.normalize("NFKD", value)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    text = re.sub(r"[-\s]+", "-", text)
    slug = text.strip("-")
    if not slug:
        return "generic"
    return slug[:max_len].rstrip("-")


def validate_ddi_urn(urn: str) -> bool:
    """Strictly validate whether a string conforms to canonical DDI 3.3 / 4.0 URN syntax.

    Canonical format: urn:ddi:{agency}:{ID}:{version}
    e.g. urn:ddi:fr.cdsp:QI-trust-national-assembly-4f2a:1.0.0
    """
    if not urn or not isinstance(urn, str):
        return False

    if not urn.startswith("urn:ddi:"):
        return False

    parts = urn.split(":")
    # Canonical DDI 3.3 / 4.0 has 5 colon-separated segments:
    # ['urn', 'ddi', agency, identifier, version]
    if len(parts) != 5:
        return False

    agency = parts[2].strip()
    identifier = parts[3].strip()
    version = parts[4].strip()

    if not agency or not identifier or not version:
        return False

    # Agency should follow reverse-DNS or dot-separated alphanumeric
    if not re.match(r"^[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)*$", agency):
        return False

    # Identifier must be non-empty valid URI path segment
    if not re.match(r"^[a-zA-Z0-9_.\-]+$", identifier):
        return False

    # Version should be semantic or dot-separated numbers/characters
    if not re.match(r"^[a-zA-Z0-9_.\-]+$", version):
        return False

    return True


def generate_generic_urn(
    resource_type: str,
    name_or_text: str | None = None,
    agency: str | None = None,
    version: str = "1.0.0",
    token_len: int = 6,
) -> str:
    """Generate a canonical, survey-agnostic DDI URN for an elevated or generic resource.

    Args:
        resource_type: Name of the DDI model (e.g. 'QuestionItem', 'ConceptualVariable').
        name_or_text: Human label or wording used to derive a descriptive slug.
        agency: Maintenance agency (defaults to DDI_AGENCY env or 'fr.cdsp').
        version: Resource version (defaults to '1.0.0').
        token_len: Length of the random hex suffix to guarantee uniqueness.

    Returns:
        Canonical URN string, e.g. 'urn:ddi:fr.cdsp:QI-trust-in-parliament-a8b2c1:1.0.0'.
    """
    eff_agency = agency or os.getenv("DDI_AGENCY", "fr.cdsp")
    pfx = PREFIX_MAP.get(resource_type, resource_type[:3].upper())
    slug = slugify(name_or_text)
    rand_token = uuid.uuid4().hex[:token_len]
    object_id = f"{pfx}-{slug}-{rand_token}"
    return f"urn:ddi:{eff_agency}:{object_id}:{version}"

