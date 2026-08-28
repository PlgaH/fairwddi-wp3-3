"""Django application configuration for fairwddi."""

from django.apps import AppConfig


class FairwDDIConfig(AppConfig):
    """Django AppConfig for the fairwddi DDI-Lifecycle package."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "fairwddi"
    verbose_name = "FAIRwDDI Lifecycle Question Bank"
