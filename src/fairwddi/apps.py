"""Django application configuration for fairwddi."""

from typing import Any

from django.apps import AppConfig


class FairwDDIConfig(AppConfig):
    """Django AppConfig for the fairwddi DDI-Lifecycle package."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "fairwddi"
    verbose_name = "FAIRwDDI Lifecycle Question Bank"

    def ready(self) -> None:
        """Register referential integrity pre_delete/post_delete guards for DDI models."""
        from django.db.models.signals import post_delete, pre_delete

        from fairwddi.models.base import DDIIdentifiable
        from fairwddi.utils.integrity import assert_can_delete, is_integrity_bypassed

        def _check_ddi_pre_delete(sender: type[Any], instance: Any, **kwargs: Any) -> None:
            if not issubclass(sender, DDIIdentifiable) or is_integrity_bypassed():
                return
            assert_can_delete(instance.urn)

        def _cleanup_ddi_post_delete(sender: type[Any], instance: Any, **kwargs: Any) -> None:
            if not issubclass(sender, DDIIdentifiable):
                return
            from fairwddi.models.concept import SemanticRelationship
            from fairwddi.models.infrastructure import UrnRegistry

            SemanticRelationship.objects.filter(subject_urn=instance.urn).delete()
            UrnRegistry.objects.filter(urn=instance.urn).delete()

        pre_delete.connect(
            _check_ddi_pre_delete,
            dispatch_uid="fairwddi_ddi_pre_delete_guard",
        )
        post_delete.connect(
            _cleanup_ddi_post_delete,
            dispatch_uid="fairwddi_ddi_post_delete_cleanup",
        )
