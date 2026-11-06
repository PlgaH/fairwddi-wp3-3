"""HTML views for the FAIRwDDI web explorer."""

from __future__ import annotations

from typing import Any

from django.http import HttpResponse

from fairwddi.api.explorer_html import EXPLORER_HTML


def explorer_view(request: Any) -> HttpResponse:
    """Serve the interactive Question Bank & Harmonization Explorer single-page application."""
    return HttpResponse(EXPLORER_HTML, content_type="text/html; charset=utf-8")
