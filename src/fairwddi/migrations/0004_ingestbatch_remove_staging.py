# Generated for FAIRwDDI Phase 2 Ingestion: Replace staging tables with IngestBatch receipt

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("fairwddi", "0003_urnregistry_status"),
    ]

    operations = [
        migrations.CreateModel(
            name="IngestBatch",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "source_format",
                    models.CharField(
                        help_text=(
                            "Source format slug: 'ddi-l:4.0:json', 'ddi-l:4.0:jsonl', "
                            "'ddi-l:3.3:xml', 'ddi-c:2.5:xml'."
                        ),
                        max_length=64,
                    ),
                ),
                (
                    "file_name",
                    models.CharField(
                        help_text="Original or upgraded filename ingested.",
                        max_length=512,
                    ),
                ),
                (
                    "file_sha256",
                    models.CharField(
                        db_index=True,
                        help_text="SHA-256 digest of the ingested file for duplicate prevention.",
                        max_length=64,
                    ),
                ),
                (
                    "file_path",
                    models.CharField(
                        blank=True,
                        help_text="Resolved path to the ingested metadata file on disk.",
                        max_length=1024,
                        null=True,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        db_index=True,
                        default="completed",
                        help_text="Batch status: 'completed', 'quarantined', 'undone', 'failed'.",
                        max_length=32,
                    ),
                ),
                (
                    "options",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Batch configuration, job_id, profile, and options.",
                    ),
                ),
                (
                    "created_urns",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Ordered list of canonical URNs created exclusively by this batch.",
                    ),
                ),
                (
                    "reused_urns",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="List of pre-existing canonical URNs reused during this batch.",
                    ),
                ),
                (
                    "created_aliases",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="List of alias_urn values registered in URNAlias by this batch.",
                    ),
                ),
                (
                    "stats",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Summary counts of created entities, shortcuts, and frequencies.",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Ingest Batch",
                "verbose_name_plural": "Ingest Batches",
                "db_table": "request_ddi_ingestbatch",
            },
        ),
        migrations.DeleteModel(
            name="StagedResourceNode",
        ),
        migrations.DeleteModel(
            name="StagedImport",
        ),
    ]
