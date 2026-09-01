# Generated for FAIRwDDI StagedImport refactoring

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("fairwddi", "0002_remove_conceptrelationship_source_concept_and_more"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="StagedImportPayload",
            new_name="StagedImport",
        ),
        migrations.AlterModelTable(
            name="stagedimport",
            table="request_ddi_stagedimport",
        ),
        migrations.AlterModelOptions(
            name="stagedimport",
            options={
                "verbose_name": "Staged Import",
                "verbose_name_plural": "Staged Imports",
            },
        ),
        migrations.RemoveField(
            model_name="stagedimport",
            name="raw_payload",
        ),
        migrations.RemoveField(
            model_name="stagedimport",
            name="original_urns",
        ),
        migrations.AddField(
            model_name="stagedimport",
            name="import_options",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Lightweight batch configuration and options passed with the upload.",
            ),
        ),
        migrations.AddField(
            model_name="stagedimport",
            name="total_resources",
            field=models.IntegerField(
                default=0,
                help_text="Total staged resource nodes extracted from the payload.",
            ),
        ),
        migrations.AddField(
            model_name="stagedimport",
            name="processed_resources",
            field=models.IntegerField(
                default=0,
                help_text="Count of successfully processed resource nodes.",
            ),
        ),
        migrations.RenameField(
            model_name="stagedresourcenode",
            old_name="import_payload",
            new_name="staged_import",
        ),
    ]
