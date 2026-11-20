"""Time the pages with many pull requests: ``make benchmark``, not part of ``make test``.

It makes a project of 1500 pull requests with labels, states and reviews, and prints the time
and the queries of the table with each condition, the filters, the page of a pull request, its
badge and Check. The cache is not cleared between the addresses: the later ones may use what
the earlier ones kept, as on the site.
"""

import time

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

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
from pycal_dashboard.services.project_editor import ProjectEditor

pytestmark = pytest.mark.django_db
N = 1500
COLUMNS = [
    "labels~applies~present~needs review",
    "labels~applies~absent~needs review",
    "branch~applies~up_to_date",
    "branch~applies~outdated",
    "branch~applies~conflict",
    "ci~applies~passing",
    "ci~applies~failing",
    "ci~applies~unknown",
    "status~applies~open",
    "status~applies~merged",
    "status~applies~auto_merge",
    "reviews~applies~1",
    "author~applies~review_ratio~1",
    "author~applies~reviews_given~3",
]


@pytest.fixture
def big(bob):
    now = timezone.now()
    repository = Repository.objects.create(
        full_name="o/r", updated=now, issues_changed=now, reviews_changed=now, data_version=3
    )
    project = ProjectEditor.create(bob, "iCalendar", slug="icalendar")
    project.repositories.add(repository)
    people = [GitHubUser.objects.create(github_id=900000 + i, login=f"p{i}") for i in range(50)]
    labels = [
        Label.objects.create(repository=repository, github_id=i, name=f"l{i}") for i in range(20)
    ]
    labels.append(Label.objects.create(repository=repository, github_id=99, name="needs review"))
    issues = Issue.objects.bulk_create(
        Issue(
            repository=repository,
            number=i + 1,
            pull_request=True,
            title=f"PR {i}",
            author=people[i % 50],
            state="open" if i % 10 == 0 else "closed",
            created=now,
            merged=now if i % 3 else None,
            closed=None if i % 10 == 0 else now,
            changed=now,
        )
        for i in range(N)
    )
    through = Issue.labels.through
    through.objects.bulk_create(
        through(issue_id=issue.pk, label_id=labels[(issue.number * 7) % 21].pk) for issue in issues
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
        Review(github_id=i, issue=issues[i % N], author=people[(i * 3) % 50], state="APPROVED")
        for i in range(2000)
    )
    for i, column in enumerate(COLUMNS[:8]):
        saved = PullRequestFilter.objects.create(project=project, name=f"F{i}", columns=[column])
        if i < 4:
            PullRequestStep.objects.create(project=project, filter=saved, name=f"S{i}", position=i)
    return project


def measure(client, address):
    connection.queries_log.clear()
    with CaptureQueriesContext(connection) as queries:
        start = time.perf_counter()
        answer = client.get(address)
        seconds = time.perf_counter() - start
    assert answer.status_code == 200, address
    return seconds, len(queries)


def test_bench(client, big):
    table = "/projects/icalendar/pull-requests.json?per_page=100"
    rows = [("table", table)] + [(c, f"{table}&col={c}") for c in COLUMNS]
    rows.append(("all", table + "".join(f"&col={c}" for c in COLUMNS)))
    rows += [
        ("filters.json", "/projects/icalendar/filters.json"),
        ("filters page", "/projects/icalendar/filters/"),
        ("pull page", "/projects/icalendar/pull/1/"),
        ("badge", "/projects/icalendar/pull/1/badge.svg"),
        ("table page", "/projects/icalendar/pull-requests/"),
        ("check", "/projects/icalendar/steps/check/?all=1"),
    ]
    for name, address in rows:
        seconds, count = measure(client, address)
        print(f"{name:40} {seconds * 1000:8.0f} ms {count:6} queries")


def test_bench_after_an_update(big, caplog):
    """The receivers after an update of a repository: what the update thread does."""
    import logging

    from pycal_dashboard import receivers
    from pycal_dashboard.models import PullRequestMessage
    from pycal_dashboard.services.repository_update import RepositoryUpdate
    from pycal_dashboard.update_signals import repository_updated

    PullRequestMessage.objects.create(project=big, template="{tasks_all}", to_open=True)
    receivers.SLOW = 0.0  # every receiver says how long it took
    repository = big.repositories.get()
    with caplog.at_level(logging.INFO, logger="pycal_dashboard.receivers"):
        start = time.perf_counter()
        repository_updated.send(sender=RepositoryUpdate, repository=repository)
        total = time.perf_counter() - start
    for record in caplog.records:
        print(record.getMessage())
    print(f"all receivers: {total * 1000:.0f} ms")
