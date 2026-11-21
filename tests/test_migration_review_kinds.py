"""The migration of the columns of reviews saved with ~comments: all kinds count now."""

import importlib

import pytest

from pycal_dashboard.models import PullRequestFilter, PullRequestStep
from pycal_dashboard.services.project_editor import ProjectEditor

pytestmark = pytest.mark.django_db
MIGRATION = importlib.import_module("pycal_dashboard.migrations.0030_review_kinds")


def test_the_columns_and_the_notes_of_tasks_lose_comments(bob):
    from django.apps import apps

    project = ProjectEditor.create(bob, "iCalendar", slug="icalendar")
    saved = PullRequestFilter.objects.create(
        project=project,
        name="Review",
        columns=["reviews~applies~below~2~comments", "labels~applies~present~comments"],
    )
    step = PullRequestStep.objects.create(
        project=project,
        filter=saved,
        name="Review",
        conditions={"reviews~applies~below~2~comments": {"summary": "Review it"}},
    )
    MIGRATION.migrate(apps, None)
    saved.refresh_from_db()
    step.refresh_from_db()
    assert saved.columns == ["reviews~applies~below~2", "labels~applies~present~comments"]
    assert step.conditions == {"reviews~applies~below~2": {"summary": "Review it"}}
