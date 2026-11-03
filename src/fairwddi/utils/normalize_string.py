"""String normalization utilities aligned with ReQuest (`request_ddi.utils.normalize_string`)."""

from __future__ import annotations

import re
import unicodedata


def normalize_string(value: str | None, *, french_punctuation: bool = False) -> str:
    """Normalize a metadata string (Unicode NFKC, quotes/dashes, whitespace collapsing)."""
    if not isinstance(value, str):
        return ""

    text = unicodedata.normalize("NFKC", value)
    text = re.sub(r"[\u00A0\u202F\u2007\u2060\u2027\u00B7]", " ", text)
    text = text.replace("«", '"').replace("»", '"')
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2019", "'").replace("\u2013", "-")

    if french_punctuation:
        text = re.sub(r"(?<!\s)([?;])", r" \1", text)
        text = re.sub(r'(?<!\s)(["])', r" \1", text)
        text = re.sub(r'(["])(?=\S)', r"\1 ", text)

    text = text.replace("\u2026", "...")
    text = re.sub(r"\.{3,}", "...", text)
    return " ".join(text.split())


def normalize_string_for_database(value: str | None) -> str | None:
    """Normalize a string using legacy ReQuest database punctuation rules."""
    if not isinstance(value, str):
        return value
    return normalize_string(value, french_punctuation=True)


def normalize_string_for_comparison(value: str | None) -> str:
    """Normalize a string for accent-insensitive, case-insensitive comparison."""
    if not isinstance(value, str):
        return ""
    cleaned = normalize_string(value, french_punctuation=False)
    decomposed = unicodedata.normalize("NFD", cleaned)
    stripped = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return stripped.lower()
