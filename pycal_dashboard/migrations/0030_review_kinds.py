"""The reviews count of all kinds by default: a column saved with ~comments counts all of them."""

from django.db import migrations

LEGACY = "~comments"


def without_comments(value: str) -> str:
    """A column of reviews without the old choice comments, which all kinds are now.

    Parameters:
        value: The column, such as ``reviews~applies~at_least~2~comments``.

    Returns:
        Such as ``reviews~applies~at_least~2``; other columns as they are.
    """
    if value.startswith("reviews~") and value.endswith(LEGACY):
        return value[: -len(LEGACY)]
    return value


def migrate(apps, schema_editor):
    """The saved filters, and the notes of the tasks of steps, which are kept by the column.

    Parameters:
        apps: The models of the migration.
        schema_editor: Not used.
    """
    Filter = apps.get_model("pycal_dashboard", "PullRequestFilter")
    Step = apps.get_model("pycal_dashboard", "PullRequestStep")
    for saved in Filter.objects.all():
        columns = [without_comments(value) for value in saved.columns or []]
        if columns != saved.columns:
            saved.columns = columns
            saved.save(update_fields=["columns"])
    for step in Step.objects.all():
        notes = {without_comments(key): note for key, note in (step.conditions or {}).items()}
        if notes != step.conditions:
            step.conditions = notes
            step.save(update_fields=["conditions"])


class Migration(migrations.Migration):
    dependencies = [("pycal_dashboard", "0029_message_draft")]

    operations = [migrations.RunPython(migrate, migrations.RunPython.noop)]
