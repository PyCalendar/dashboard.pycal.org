"""The badge of a pull request: its step and tasks done, cached, always linked to its page."""

import pytest
from django.core.cache import cache

from pycal_dashboard.models import Issue, Repository
from pycal_dashboard.services import pull_request_badge
from pycal_dashboard.step_template import expand, values_of

from .test_pull_request_page import number_of, steps  # noqa: F401 (fixtures)
from .test_steps import filters, project  # noqa: F401 (fixtures)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def empty_cache():
    cache.clear()


def badge(client, title: str, kind: str = "svg", **headers: str):
    return client.get(f"/projects/icalendar/pull/{number_of(title)}/badge.{kind}", **headers)


def test_the_badge_shows_the_step_and_its_tasks(client, project, steps):  # noqa: F811
    answer = badge(client, "Ready")
    assert answer["Content-Type"] == "image/svg+xml"
    svg = answer.content.decode()
    assert "<title>Review: 0/1</title>" in svg and 'role="img"' in svg
    assert answer["Cache-Control"] == "public, max-age=300" and answer["ETag"]
    outside = badge(client, "Merged").content.decode()
    assert "<title>Steps: outside</title>" in outside


def test_without_steps(client, project):  # noqa: F811
    assert "<title>Steps: none</title>" in badge(client, "Ready").content.decode()


def test_the_png(client, project, steps):  # noqa: F811
    answer = badge(client, "Ready", "png")
    assert answer["Content-Type"] == "image/png" and answer.content[1:4] == b"PNG"


def test_the_badge_is_cached_until_something_changes(
    client,
    project,  # noqa: F811
    steps,  # noqa: F811
    monkeypatch,
):
    drawn = []
    texts = pull_request_badge.PullRequestBadge.texts
    monkeypatch.setattr(
        pull_request_badge.PullRequestBadge,
        "texts",
        lambda self: drawn.append(1) or texts(self),
    )
    first = badge(client, "Ready")
    second = badge(client, "Ready")
    assert first.content == second.content and len(drawn) == 1  # from the cache
    again = badge(client, "Ready", HTTP_IF_NONE_MATCH=first["ETag"])
    assert again.status_code == 304 and again.content == b""
    _first, review = steps
    review.name = "Waiting for a review"
    review.save()
    changed = badge(client, "Ready")
    assert "<title>Waiting for a review: 0/1</title>" in changed.content.decode()
    assert changed["ETag"] != first["ETag"] and len(drawn) == 2
    Repository.objects.update(updated="2026-11-20T10:00:00Z")  # an update of the repository
    badge(client, "Ready")
    assert len(drawn) == 3


def test_a_private_repository_has_no_public_badge(client, project, steps, bob):  # noqa: F811
    Repository.objects.update(private=True)
    assert badge(client, "Ready").status_code == 404
    client.force_login(bob)
    answer = badge(client, "Ready")
    assert answer.status_code == 200 and answer["Cache-Control"] == "private, max-age=300"


def test_a_number_of_two_repositories(client, github, project):  # noqa: F811
    from pycal_dashboard.services.repository_update import RepositoryUpdate

    github.add_repository("collective/other", installation=11)
    github.add_issue("collective/other", "Other", pull_request=True)
    other = Repository.objects.create(full_name="collective/other")
    project.repositories.add(other)
    assert RepositoryUpdate(other).run()
    answer = client.get("/projects/icalendar/pull/1/badge.svg")
    assert answer.status_code == 404 and "Which repository?" in answer.content.decode()
    answer = client.get("/projects/icalendar/pull/1/badge.svg?repository=collective/other")
    assert answer.status_code == 200


def test_the_variables_of_the_badge(project, settings):  # noqa: F811
    settings.SITE_URL = "https://dashboard.example.org"
    pull = Issue.objects.select_related("author", "repository").get(title="Ready")
    values = values_of(pull, project)
    page = "https://dashboard.example.org/projects/icalendar/pull/1/"
    query = "?repository=collective%2Ficalendar"  # always: the address stays the same
    assert values["pr_badge_url"] == page + "badge.svg" + query
    assert expand("{pr_badge}", values) == f"[![]({page}badge.svg{query})]({page}{query})"
    alt = values_of(pull, project, alt="Review 1/2")["pr_badge"]
    assert alt.startswith("[![Review 1/2](")  # read by screen readers
    assert expand("{pr_badge_url}", values) != values["pr_badge_url"]  # escaped as text


def test_the_table_and_the_page_show_the_badge_linked(client, project, steps):  # noqa: F811
    number = number_of("Ready")
    table = client.get("/projects/icalendar/pull-requests/").content.decode()
    linked = (
        f'<a href="/projects/icalendar/pull/{number}/" data-pull-badge>'
        f'<img src="/projects/icalendar/pull/{number}/badge.svg"'
    )
    assert linked in table and 'id="column-step" data-column="step" checked' in table
    page = client.get(f"/projects/icalendar/pull/{number}/").content.decode()
    assert "badge.png" not in page and "[![](" not in page  # no place to copy it


def test_a_step_description_shows_the_badge(client, project, steps, settings):  # noqa: F811
    import re

    settings.SITE_URL = "https://dashboard.example.org"
    _first, review = steps
    review.summary = "Where it is: {pr_badge}"
    review.save()
    number = number_of("Ready")
    page = client.get(f"/projects/icalendar/pull/{number}/").content.decode()
    shown = page.split("data-shown-step")[1]
    query = "?repository=collective%2Ficalendar"
    address = f"https://dashboard.example.org/projects/icalendar/pull/{number}/{query}"
    path = re.escape(f"/projects/icalendar/pull/{number}/badge.svg{query}")  # from this site
    assert re.search(rf'<a href="{re.escape(address)}"[^>]*><img src="{path}"', shown)
    # the alternative text is what the badge shows: the page is made again when it changes
    from pycal_dashboard.services.pull_request_badge import PullRequestBadge

    issue = Issue.objects.get(number=number)
    label, value, *_colors = PullRequestBadge(issue, project, [issue.repository]).texts()
    assert label == "Review" and f'alt="Review {value}"' in shown


def test_markdown_shows_images_of_this_site_only(settings):
    from pycal_dashboard.markdown_text import render

    settings.SITE_URL = "https://dashboard.example.org"
    html = render(
        "![a](https://dashboard.example.org/x/badge.svg) ![b](https://evil.example/t.png)"
        " ![c](/y/badge.png) ![d](//evil.example/z.png)"
    )
    assert '<img src="/x/badge.svg" alt="a">' in html and '<img src="/y/badge.png"' in html
    assert 'src="https://evil' not in html and 'src="//evil' not in html
    assert html.count("<img") == 2  # the others show their text, see test_markdown.py
    assert ">b</span>" in html and ">d</span>" in html


def test_the_color_of_the_step_is_behind_its_name(client, project, steps):  # noqa: F811
    _first, second = steps
    second.color = "#bbf7d0"
    second.save()
    badge = client.get(f"/projects/icalendar/pull/{number_of('Ready')}/badge.svg").content
    text = badge.decode()
    assert '<path fill="#bbf7d0" d="M0 0h' in text  # the left side: the name of the step
    assert 'fill="#111111"' in text  # dark text on the light color
    png = client.get(f"/projects/icalendar/pull/{number_of('Ready')}/badge.png").content
    assert png[1:4] == b"PNG"
    second.color = ""
    second.save()
    text = client.get(f"/projects/icalendar/pull/{number_of('Ready')}/badge.svg").content.decode()
    assert '<path fill="#555555" d="M0 0h' in text  # gray without a color
