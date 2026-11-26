"""Every link to GitHub has the mark of GitHub: people see when they leave dashboard.pycal.org."""

from html.parser import HTMLParser

import pytest

from pycal_dashboard.github_mark import leads_to_github
from pycal_dashboard.models import Issue, PullRequestMessage, PullRequestStep, Repository
from pycal_dashboard.services.repository_update import RepositoryUpdate

from .test_evidence import BEN
from .test_pull_request_page import steps  # noqa: F401 (fixture)
from .test_steps import filters, project  # noqa: F401 (fixtures)

pytestmark = pytest.mark.django_db


class Links(HTMLParser):
    """The links of a page, with their text and whether the mark of GitHub is in them."""

    def __init__(self):
        super().__init__()
        self.open: list[dict] = []
        self.found: list[dict] = []

    def handle_starttag(self, tag, attrs):
        found = dict(attrs)
        if tag == "a":
            self.open.append({"href": found.get("href") or "", "mark": False, "text": ""})
        elif tag == "svg" and "github-mark" in (found.get("class") or "") and self.open:
            self.open[-1]["mark"] = True

    def handle_endtag(self, tag):
        if tag == "a" and self.open:
            self.found.append(self.open.pop())

    def handle_data(self, data):
        if self.open:
            self.open[-1]["text"] += data


def github_links(html: str) -> list[dict]:
    """The links to GitHub of a page, each with ``href``, ``text`` and whether it has the mark."""
    links = Links()
    links.feed(html)
    return [link for link in links.found if leads_to_github(link["href"])]


def unmarked(html: str) -> list[str]:
    """The links to GitHub of a page without the mark of GitHub, with their text."""
    return [
        f"{link['href']} ({' '.join(link['text'].split())})"
        for link in github_links(html)
        if not link["mark"]
    ]


def test_the_detector():
    page = (
        '<a href="https://github.com/a">a</a> <a href="/b">b</a>'
        '<a href="https://github.com/c"><svg class="icon github-mark"></svg> c</a>'
    )
    assert unmarked(page) == ["https://github.com/a (a)"]


def test_every_link_to_github_has_the_mark(client, github, project, steps, bob):  # noqa: F811
    """The pages of a project with steps, a message and texts in Markdown that link GitHub."""
    github.add_review("collective/icalendar", 2, BEN)
    assert RepositoryUpdate(Repository.objects.get()).run()
    link = "See [the issue](https://github.com/collective/icalendar/issues/1)."
    project.description = link
    project.save()
    review = PullRequestStep.objects.get(name="Review")
    review.summary = link
    review.conditions = {
        "labels~applies~present~needs review": {"summary": "Review", "description": link}
    }
    review.save()
    PullRequestMessage.objects.create(project=project, template=link, to_open=True)
    review.filter.description = link
    review.filter.save()
    ready = Issue.objects.get(title="Ready")
    client.force_login(bob)
    found = {}
    seen: set[str] = set()
    for path in (
        "/",
        "/about/",
        "/about/github-app/",
        "/about/privacy/",
        "/projects/",
        project.path(),
        project.path("pull-requests/"),
        project.path("pull-requests/") + "?col=labels~applies~present~needs+review",
        project.path("contributors/octocat/"),
        project.path("contributors/ben/?tab=reviews"),
        project.path("steps/check/?all=1"),
        project.path(f"message/review/?pull={ready.number}"),
        project.path("filters/"),
        project.path("steps/"),
        project.path(f"steps/?step={review.pk}"),
        project.path("steps/check/"),
        project.path("message/"),
        project.path("message/edit/"),
        project.path("message/review/"),
        project.path("message/scope/"),
        project.path(f"pull/{ready.number}/"),
        project.path(f"pull/{ready.number}/?step={review.pk}"),
        project.path("settings/"),
        project.path("settings/repositories/"),
        project.path("settings/collaborators/"),
        project.path("settings/backup/"),
        project.path("settings/snapshots/"),
        project.path("settings/danger/"),
        "/people/niccokunzmann/",
        "/account/",
        "/account/notifications/",
        "/projects/nothing/",  # an error, with its link to report a bug
    ):
        answer = client.get(path)
        assert answer.status_code in (200, 404), path
        html = answer.content.decode()
        seen.update(link["href"] for link in github_links(html))
        missing = unmarked(html)
        if missing:
            found[path] = missing
    assert found == {}
    for kind in (  # the test sees the links of every kind
        "github.com/collective/icalendar/issues/1",  # in Markdown
        "github.com/collective/icalendar/pull/1",  # of the pull request
        "#pullrequestreview-",  # a review of a contributor
        "issues/new?template=feedback.yml",  # to report a bug, also on an error
        "docs.github.com/",  # the privacy statement of GitHub
    ):
        assert any(kind in href for href in seen), kind
    assert "https://github.com/collective/icalendar" in seen  # the repository
