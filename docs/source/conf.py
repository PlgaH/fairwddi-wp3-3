# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import builtins
import os
import sys
from collections.abc import Callable
from typing import Any, cast

# Add Any to builtins to fix Sphinx napoleon bug where Any is not defined
builtins.__dict__["Any"] = Any

# Patch Napoleon's _skip_member BEFORE Napoleon's setup() registers it.
try:
    import sphinx.ext.napoleon as _napoleon_ext

    _original_napoleon_skip = cast(
        Callable[[Any, str, str, Any, bool, Any], bool] | None,
        getattr(_napoleon_ext, "_skip_member", None),
    )

    def _safe_napoleon_skip(
        app: Any,
        what: str,
        name: str,
        obj: Any,
        skip: bool,
        options: Any,
    ) -> bool:
        """Safe wrapper around Napoleon's _skip_member that handles Pydantic internals."""
        if name.startswith("__pydantic_"):
            return True
        if _original_napoleon_skip is None:
            return skip
        try:
            return _original_napoleon_skip(app, what, name, obj, skip, options)
        except Exception:
            return True

    _napoleon_ext._skip_member = _safe_napoleon_skip
except Exception:
    pass

# Ensure fairwddi package source is discoverable
sys.path.insert(0, os.path.abspath("../../src"))

# Initialize lightweight in-memory Django configuration for Sphinx autodoc
try:
    import django
    from django.conf import settings

    if not settings.configured:
        settings.configure(
            SECRET_KEY="fairwddi-sphinx-docs-build-secret-key-only",
            INSTALLED_APPS=[
                "django.contrib.contenttypes",
                "django.contrib.auth",
                "fairwddi",
            ],
            DATABASES={
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": ":memory:",
                }
            },
            USE_TZ=True,
        )
        django.setup()
except Exception as e:
    print(f"Warning: Failed to initialize Django environment for Sphinx: {e}")

# -- Project information -----------------------------------------------------
project = "FAIRwDDI Lifecycle"
copyright = "2026, Centre des Données Socio-Politiques (CDSP), Sciences Po / CNRS"
author = "CDSP / Sciences Po & CNRS"
release = "0.1.0"
version = "0.1.0"

# -- General configuration ---------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.autosummary",
    "sphinx.ext.coverage",
    "myst_parser",
    "sphinx_copybutton",
]

# Autodoc configuration
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
    "special-members": "__init__",
}

autodoc_typehints = "description"
autodoc_typehints_description_target = "documented"

# Suppress warnings for missing or mocked modules
suppress_warnings = ["autodoc.import_error", "autodoc.mocked_object"]

# Napoleon configuration
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False

# MyST Parser configuration
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "fieldlist",
    "tasklist",
]

# Intersphinx mapping
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pydantic": ("https://docs.pydantic.dev/latest/", None),
    "django": ("https://docs.djangoproject.com/en/stable/", None),
    "rdflib": ("https://rdflib.readthedocs.io/en/stable/", None),
}

# Todo extension
todo_include_todos = True

templates_path = ["_templates"]
exclude_patterns: list[str] = ["_build", "build", "Thumbs.db", ".DS_Store"]

# -- Options for HTML output -------------------------------------------------
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_theme_options = {
    "navigation_depth": 4,
    "collapse_navigation": False,
    "sticky_navigation": True,
    "includehidden": True,
    "titles_only": False,
    "logo_only": False,
    "prev_next_buttons_location": "bottom",
    "style_external_links": True,
}

html_css_files = [
    "custom.css",
]

# -- Custom Setup -----------------------------------------------------------
def setup(app: Any) -> None:
    """Custom Sphinx setup to handle Pydantic and Django internal attributes."""

    def skip_internal_members(
        _app: Any,
        _what: str,
        name: str,
        _obj: Any,
        skip: bool,
        _options: Any,
    ) -> bool:
        if name.startswith("__pydantic_"):
            return True
        if name in ("DoesNotExist", "MultipleObjectsReturned"):
            return True
        return skip

    app.connect("autodoc-skip-member", skip_internal_members, priority=100)
