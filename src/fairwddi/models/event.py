"""Event Logging and Resource Lifecycle Audit Trail models for FAIRwDDI."""

from django.db import models


class EventLog(models.Model):
    """Resource-agnostic lifecycle mutation and event log for any DDI-L resource."""

    id = models.BigAutoField(primary_key=True)
    urn = models.CharField(
        max_length=512,
        db_index=True,
        help_text="Canonical or source URN of the affected DDI resource.",
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Timestamp when the event occurred.",
    )
    event_type = models.CharField(
        max_length=128,
        db_index=True,
        help_text="Classification type (e.g. 'created', 'updated', 'quarantined', 'normalized').",
    )
    event_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Arbitrary event payload and metadata as JSONB.",
    )

    class Meta:
        db_table = "request_ddi_eventlog"
        ordering = ["-timestamp", "-id"]
        indexes = [
            models.Index(fields=["urn", "timestamp"], name="req_ddi_event_urn_ts_idx"),
            models.Index(fields=["event_type"], name="req_ddi_event_type_idx"),
        ]
        verbose_name = "Event Log"
        verbose_name_plural = "Event Logs"

    def __str__(self) -> str:
        return f"[{self.timestamp}] {self.event_type} on {self.urn}"
