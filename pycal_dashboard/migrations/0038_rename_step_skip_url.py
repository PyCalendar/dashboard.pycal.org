"""The variables {step_check_skip_url} and {step_check_skip_url_author} are now
{step_skip_url} and {step_skip_url_author}: the saved texts are changed over."""

import re

from django.db import migrations

RENAMED = {
    "step_check_skip_url": "step_skip_url",
    "step_check_skip_url_author": "step_skip_url_author",
}
VARIABLE = re.compile(r"\{(step_check_skip_url(?:_author)?)\}")


def renamed(text):
    """The text with the new names; None stays None."""
    if not text:
        return text
    return VARIABLE.sub(lambda match: "{" + RENAMED[match[1]] + "}", text)


def change_over(apps, schema_editor):
    """The summaries and the texts of the quality checks of steps, and the messages."""
    for step in apps.get_model("pycal_dashboard", "PullRequestStep").objects.all():
        conditions = {
            value: {key: renamed(text) if isinstance(text, str) else text for key, text in notes.items()}
            if isinstance(notes, dict)
            else notes
            for value, notes in (step.conditions or {}).items()
        }
        summary = renamed(step.summary)
        if summary != step.summary or conditions != (step.conditions or {}):
            step.summary, step.conditions = summary, conditions
            step.save(update_fields=["summary", "conditions"])
    for message in apps.get_model("pycal_dashboard", "PullRequestMessage").objects.all():
        template, draft = renamed(message.template), renamed(message.draft)
        if (template, draft) != (message.template, message.draft):
            message.template, message.draft = template, draft
            message.save(update_fields=["template", "draft"])


class Migration(migrations.Migration):
    dependencies = [("pycal_dashboard", "0037_check_skip")]

    operations = [migrations.RunPython(change_over, migrations.RunPython.noop)]
