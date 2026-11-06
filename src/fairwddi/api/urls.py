"""URL routing configuration for FAIRwDDI API and web explorer."""

from __future__ import annotations

from django.urls import path

from fairwddi.api.router import api
from fairwddi.api.views import explorer_view

urlpatterns = [
    path("api/", api.urls),
    path("explorer/", explorer_view, name="explorer"),
    path("explorer", explorer_view, name="explorer_no_slash"),
    path("", explorer_view, name="root_explorer"),
]
