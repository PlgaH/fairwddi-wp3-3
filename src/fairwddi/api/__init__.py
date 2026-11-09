"""FAIRwDDI API and Interactive Visual Explorer Package."""

from __future__ import annotations

from fairwddi.api.router import api
from fairwddi.api.server import run_server

__all__ = ["api", "run_server"]
