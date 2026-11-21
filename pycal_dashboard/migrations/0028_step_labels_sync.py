"""The step labels have two modes now: off, or with the PR Sync (sync)."""

from django.db import migrations


def to_sync(apps, schema_editor):
    """Automatic and manual are both the mode with the PR Sync now.

    Parameters:
        apps: The models of the migration.
        schema_editor: Not used.
    """
    Project = apps.get_model("pycal_dashboard", "Project")
    Project.objects.exclude(step_labels="off").update(step_labels="sync")


class Migration(migrations.Migration):
    dependencies = [("pycal_dashboard", "0027_status_labels")]

    operations = [migrations.RunPython(to_sync, migrations.RunPython.noop)]
