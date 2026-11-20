"""The pages stay fast with many pull requests: few queries, results kept in the cache."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from pycal_dashboard.conditions.group.column import Column
from pycal_dashboard.models import (
    GitHubUser,
    Issue,
    Label,
    PullRequestFilter,
    PullRequestState,
    PullRequestStep,
    Repository,
    Review,
)
from pycal_dashboard.services import column_results
from pycal_dashboard.services.column_results import ColumnResults
from pycal_dashboard.services.project_editor import ProjectEditor
from pycal_dashboard.services.step_assignment import StepAssignment

pytestmark = pytest.mark.django_db
COLUMNS = [
    "labels~applies~present~needs review",
    "labels~not~absent~needs review",
    "branch~applies~up_to_date",
    "branch~applies~outdated~conflict",
    "ci~applies~passing",
    "ci~applies~failing~unknown",
    "status~applies~open",
    "status~applies~merged~auto_merge",
    "reviews~applies~1",
    "author~applies~review_ratio~1",
    "author~applies~reviews_given~3",
]
TABLE = "/projects/icalendar/pull-requests.json?per_page=100"


@pytest.fixture
def project(bob):
    now = timezone.now()
    repository = Repository.objects.create(
        full_name="o/r", updated=now, issues_changed=now, reviews_changed=now, data_version=3
    )
    project = ProjectEditor.create(bob, "iCalendar", slug="icalendar")
    project.repositories.add(repository)
    return project


def add_pull_requests(project, count: int, start: int = 0):
    """Pull requests of all kinds, with labels, states and reviews."""
    repository = project.repositories.get()
    now = timezone.now()
    label, _ = Label.objects.get_or_create(repository=repository, github_id=1, name="needs review")
    people = [
        GitHubUser.objects.get_or_create(github_id=800000 + i, defaults={"login": f"p{i}"})[0]
        for i in range(5)
    ]
    issues = Issue.objects.bulk_create(
        Issue(
            repository=repository,
            number=start + i + 1,
            pull_request=True,
            title=f"PR {start + i}",
            author=people[i % 5],
            state="open" if i % 2 else "closed",
            merged=None if i % 2 else now,
            closed=None if i % 2 else now,
            created=now,
            changed=now,
        )
        for i in range(count)
    )
    Issue.labels.through.objects.bulk_create(
        Issue.labels.through(issue_id=issue.pk, label_id=label.pk) for issue in issues[::3]
    )
    PullRequestState.objects.bulk_create(
        PullRequestState(
            issue=issue,
            mergeable=True,
            mergeable_state="clean",
            updated=now,
            checks="success",
            checks_complete="success",
            checks_updated=now,
        )
        for issue in issues
        if issue.state == "open"
    )
    Review.objects.bulk_create(
        Review(github_id=10000 + start + i, issue=issue, author=people[i % 5], state="APPROVED")
        for i, issue in enumerate(issues[::2])
    )
    repository.updated = timezone.now()  # as an update does
    repository.save()


def queries(client, address: str) -> int:
    from django.core.cache import cache

    cache.clear()  # evaluated, not from the cache
    with CaptureQueriesContext(connection) as found:
        assert client.get(address).status_code == 200, address
    return len(found)


@pytest.mark.parametrize(
    "address",
    [
        TABLE,
        TABLE + "".join(f"&col={column}" for column in COLUMNS),
        "/projects/icalendar/filters.json",
        "/projects/icalendar/filters/1/?numbers=1",
        "/projects/icalendar/steps/check/?all=1",
    ],
)
def test_the_queries_do_not_grow_with_the_pull_requests(client, project, address):
    for index, column in enumerate(COLUMNS[:6]):
        saved = PullRequestFilter.objects.create(
            project=project, name=f"F{index}", columns=[column]
        )
        PullRequestStep.objects.create(project=project, filter=saved, name=f"S{index}")
    add_pull_requests(project, 20)
    few = queries(client, address)
    add_pull_requests(project, 60, start=20)
    assert queries(client, address) == few


def test_the_results_are_kept_until_an_update(project, monkeypatch):
    add_pull_requests(project, 10)
    repositories = list(project.repositories.all())
    column = Column.decode("labels~applies~present~needs review")
    evaluated = []
    applies = Column.applies
    monkeypatch.setattr(Column, "applies", lambda *a: evaluated.append(1) or applies(*a))
    first = ColumnResults(repositories).of(column)
    assert len(evaluated) == 10 and sum(first.values()) == 4
    assert ColumnResults(repositories).of(column) == first and len(evaluated) == 10  # cached
    project.repositories.update(updated=timezone.now())  # an update of the repository
    ColumnResults(list(project.repositories.all())).of(column)
    assert len(evaluated) == 20


def test_an_update_prepares_the_results_of_the_filters(project, monkeypatch):
    from pycal_dashboard.services.repository_update import RepositoryUpdate
    from pycal_dashboard.update_signals import repository_updated

    add_pull_requests(project, 6)
    PullRequestFilter.objects.create(project=project, name="Open", columns=["status~applies~open"])
    repository = project.repositories.get()
    repository_updated.send(sender=RepositoryUpdate, repository=repository)
    evaluated = []
    monkeypatch.setattr(Column, "applies", lambda *a: evaluated.append(1))
    results = ColumnResults([repository])
    assert results.count(Column.decode("status~applies~open")) == 3 and evaluated == []


def test_the_step_of_all_is_the_step_of_each(project):
    add_pull_requests(project, 30)
    for position, column in enumerate(["reviews~applies~1", "labels~applies~present~needs review"]):
        saved = PullRequestFilter.objects.create(project=project, name=column, columns=[column])
        PullRequestStep.objects.create(
            project=project, filter=saved, name=column, position=position
        )
    results = ColumnResults(list(project.repositories.all()))
    assignment = StepAssignment(project, results.scope)
    every = assignment.step_of_all(results)
    for pull in results.pulls():
        assert every[pull.pk] == assignment.step_of(pull), pull.title
    assert {step.name if step else None for step in every.values()} == {
        "reviews~applies~1",
        "labels~applies~present~needs review",
        None,
    }


def test_a_page_of_the_table_loads_only_its_pull_requests(client, project, monkeypatch):
    add_pull_requests(project, 40)
    loaded = []
    rows = column_results.ColumnResults.rows
    monkeypatch.setattr(
        column_results.ColumnResults,
        "rows",
        lambda self, ids, columns: loaded.append(len(ids)) or rows(self, ids, columns),
    )
    data = client.get(TABLE.replace("100", "10") + "&col=status~applies~open&page=2").json()
    assert (data["count"], data["page"], len(data["pull_requests"])) == (20, 2, 10)
    assert loaded == [10]
