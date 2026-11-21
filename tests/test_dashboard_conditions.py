"""The conditions on data of the dashboard: the PR Sync of a pull request, and skipped steps."""

import pytest

from pycal_dashboard.conditions.group.column import Column
from pycal_dashboard.conditions.state.scope import Scope
from pycal_dashboard.models import (
    Issue,
    PullRequestComment,
    PullRequestFilter,
    PullRequestStep,
    StepSkip,
)
from pycal_dashboard.services.column_results import ColumnResults

from .test_steps import filters, project  # noqa: F401 (fixtures)

pytestmark = pytest.mark.django_db


def pull(title):
    return Issue.objects.select_related("author", "repository").get(title=title)


def test_pr_sync_on(project):  # noqa: F811
    PullRequestComment.objects.create(project=project, issue=pull("Ready"), github_id=99, digest="")
    column = Column.decode("dashboard~applies~sync")
    scope = Scope.of(project)
    assert column.applies(pull("Ready"), scope) is True
    assert column.applies(pull("Conflict"), scope) is False
    assert column.applies(pull("Ready")) is None  # without the project: not known
    assert column.sentence == "it has the PR Sync on"
    assert column.inverted().sentence == "it does not have the PR Sync on"
    evidence = column.evidence(pull("Ready"), scope, project)
    assert evidence[0].url.endswith("/pull/1#issuecomment-99")
    other = column.evidence(pull("Conflict"), scope, project)
    assert other[0].url == "/projects/icalendar/message/"


def test_a_skipped_step(project, filters, bob):  # noqa: F811
    conflict, review = filters
    step = PullRequestStep.objects.create(project=project, filter=review, name="Review")
    column = Column.decode("dashboard~applies~skipped")
    assert column.applies(pull("Ready"), Scope.of(project)) is False
    StepSkip.objects.create(step=step, issue=pull("Ready"), user=bob, reason="Met")
    assert column.applies(pull("Ready"), Scope.of(project)) is True
    other = PullRequestStep.objects.create(project=project, filter=conflict, name="Conflicts")
    other.skip_authors = ["octocat"]  # the author of all pull requests of the fake
    other.save()
    assert column.applies(pull("Merged"), Scope.of(project)) is True
    evidence = column.evidence(pull("Ready"), Scope.of(project), project)
    assert evidence[0].url == f"/projects/icalendar/pull/{pull('Ready').number}/"
    assert "dashboard.pycal.org" in str(evidence[0].text)


def test_the_results_are_not_kept_in_the_cache(project, filters, bob):  # noqa: F811
    """A skip or a message changes them without an update from GitHub."""
    _conflict, review = filters
    step = PullRequestStep.objects.create(project=project, filter=review, name="Review")
    repositories = list(project.repositories.all())
    column = Column.decode("dashboard~applies~skipped")
    results = ColumnResults(repositories, project=project)
    assert results.of(column)[pull("Ready").pk] is False
    assert results.cached(column) is None
    StepSkip.objects.create(step=step, issue=pull("Ready"), user=bob, reason="Met")
    fresh = ColumnResults(repositories, project=project)  # the same version of the repositories
    assert fresh.version == results.version
    assert fresh.of(column)[pull("Ready").pk] is True
    assert fresh.matching([column]) == [pull("Ready").pk]


def test_the_table_filters_by_them(client, project, filters, bob):  # noqa: F811
    _conflict, review = filters
    step = PullRequestStep.objects.create(project=project, filter=review, name="Review")
    StepSkip.objects.create(step=step, issue=pull("Ready"), user=bob, reason="Met")
    page = client.get("/projects/icalendar/pull-requests/?col=dashboard~applies~skipped")
    text = page.content.decode()
    rows = [row for row in text.split("<tr")[1:] if "data-pull-request" in row]
    assert len(rows) == 1 and "Ready" in rows[0]
    menu = client.get("/projects/icalendar/pull-requests/").content.decode()
    assert 'value="dashboard"' in menu and "PR Sync on" in menu and "a skipped step" in menu


def test_a_filter_with_them_is_saved(project):  # noqa: F811
    saved = PullRequestFilter.objects.create(
        project=project, name="Synced", columns=["dashboard~applies~sync~skipped"]
    )
    column = Column.decode(saved.columns[0])
    assert column.choices == ("sync", "skipped")
    assert column.sentence == "it has the PR Sync on or a skipped step"
