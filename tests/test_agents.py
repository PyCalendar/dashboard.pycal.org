"""robots.txt and the guideline for agents (llms.txt): complete, and every JSON they show works."""

import pytest

from pycal_dashboard.json_api import JSON_API, PRIVATE, REPEATED
from pycal_dashboard.models import Repository
from pycal_dashboard.public_json import JSON_PAGES
from pycal_dashboard.services.project_editor import ProjectEditor
from pycal_dashboard.services.repository_update import RepositoryUpdate

pytestmark = pytest.mark.django_db


@pytest.fixture
def project(github, bob):
    github.add_repository("collective/icalendar", issues=1, pulls=1)
    repository = Repository.objects.create(full_name="collective/icalendar")
    project = ProjectEditor.create(bob, "iCalendar", slug="icalendar")
    project.repositories.add(repository)
    RepositoryUpdate(repository).run()
    return project


def project_pull_number(project) -> int:
    """The number of a pull request of the project, for the addresses of the guideline."""
    from pycal_dashboard.models import Issue

    return Issue.objects.get(repository__projects=project, pull_request=True).number


def test_every_page_with_json_is_in_the_guideline():
    assert {page["name"] for page in JSON_API} == JSON_PAGES


def test_the_guideline_shows_the_json_and_how_to_navigate(client, settings):
    settings.SITE_URL = "https://dashboard.example.org"
    answer = client.get("/llms.txt")
    assert answer["Content-Type"] == "text/markdown; charset=utf-8"
    text = answer.content.decode()
    assert text.startswith("# ")
    for page in JSON_API:
        assert f"[{page['json']}](https://dashboard.example.org{page['json']})" in text
        assert page["holds"] in text
    assert "start at https://dashboard.example.org/projects.json" in text
    assert "https://docs.example.org/reference/json.html" in text
    assert "&amp;" not in text and "&#" not in text  # text, not HTML


def test_every_json_of_the_guideline_answers(client, project):
    """Each address works, with the slug of a real project: the guideline is complete."""
    for page in JSON_API:
        address = page["json"].replace("<slug>", project.slug)
        address = address.replace("<number>", str(project_pull_number(project)))
        answer = client.get(address)
        assert answer.status_code == 200, address
        assert answer["Content-Type"] == "application/json", address
        assert answer["Access-Control-Allow-Origin"] == "*", address
    data = client.get("/projects.json").json()
    assert data["projects"][0]["slug"] == "icalendar"  # how to navigate: projects -> slug
    pulls = client.get("/projects/icalendar/pull-requests.json?per_page=25&page=1").json()
    assert (pulls["count"], pulls["page"], pulls["pages"]) == (1, 1, 1)


def test_the_start_page_points_to_the_json_and_the_guideline(client):
    data = client.get("/index.json").json()
    assert data["pages"]["projects"] == "/projects.json"
    assert data["agents"] == "/llms.txt"


def test_robots_may_read_the_public_pages(client, project, bob):
    answer = client.get("/robots.txt")
    assert answer["Content-Type"] == "text/plain; charset=utf-8"
    text = answer.content.decode()
    assert "User-agent: *" in text and "llms.txt" in text and text.rstrip().endswith("Allow: /")
    disallowed = [line.split(": ")[1] for line in text.splitlines() if line.startswith("Disallow")]
    assert disallowed == PRIVATE + REPEATED  # the private pages, then the repeated ones
    for page in JSON_API:  # the public pages and their JSON are allowed
        for address in (page["page"], page["json"]):
            path = address.replace("<slug>", "icalendar").split("?")[0]
            assert not any(path.startswith(private) for private in PRIVATE), path


@pytest.mark.parametrize("path", PRIVATE)
def test_the_disallowed_pages_are_not_public_pages(client, path):
    """The pages robots leave alone are those of people, setup and the admin: no public JSON."""
    assert not any(page["page"].startswith(path) for page in JSON_API)


def test_the_json_reference_documents_every_json():
    from pathlib import Path

    reference = (Path(__file__).parent.parent / "docs/reference/json.rst").read_text()
    for page in JSON_API:
        assert f"``{page['json'].split('?')[0]}``" in reference, page["json"]


def test_robots_leave_the_repeated_addresses_alone(client):
    """Every pull request with every step, column and badge would be read again and again."""
    import re

    text = client.get("/robots.txt").content.decode()
    for path in ("/*?step=", "/*?col=", "/*/badge.svg", "/*/badge.png", "/*?example="):
        assert f"Disallow: {path}\n" in text
    disallowed = [
        re.compile("^" + re.escape(line.split(": ", 1)[1]).replace(r"\*", ".*"))
        for line in text.splitlines()
        if line.startswith("Disallow: ")
    ]
    for page in JSON_API:  # the JSON that the guideline shows stays open
        address = page["json"].replace("<slug>", "icalendar").replace("<number>", "1")
        assert not any(rule.match(address) for rule in disallowed), address
