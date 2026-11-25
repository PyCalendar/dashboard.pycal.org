"""The page of a person (/people/<handle>/), which every GitHub handle on the pages leads to."""

import pytest

from pycal_dashboard.models import Repository
from pycal_dashboard.services.project_editor import ProjectEditor
from pycal_dashboard.services.repository_update import RepositoryUpdate

pytestmark = pytest.mark.django_db


def account(github_id: int, login: str, name: str = "") -> dict:
    return {"id": github_id, "login": login, "avatar_url": "", "type": "User", "name": name}


@pytest.fixture
def projects(github, bob):
    """A public project of a public repository, and a private one of a private repository."""
    github.add_repository("open/one", installation=11)
    github.add_repository(
        "bob/secret", private=True, installation=12, collaborators={"bob": "read"}
    )
    carol = account(301, "carol", "Carol Hidden")
    github.add_issue("open/one", "Public", pull_request=True, user=account(302, "dave"))  # 1
    github.add_issue("open/one", "An issue", user=account(302, "dave"))  # 2
    github.add_review("open/one", 1, account(303, "erin"))
    github.add_issue("bob/secret", "Hidden", pull_request=True, user=carol)
    public = ProjectEditor.create(bob, "Open", slug="open")
    secret = ProjectEditor.create(bob, "Secret", slug="secret", public=False)
    for project, name, private in ((public, "open/one", False), (secret, "bob/secret", True)):
        repository = Repository.objects.create(full_name=name, private=private)
        project.repositories.add(repository)
        assert RepositoryUpdate(repository).run()
    return public, secret


def listed(page: str) -> dict[str, str]:
    """The projects of the page of a person, with their numbers."""
    rows = page.split("data-person-project=")[1:]
    return {row.split('"')[1]: row.split('class="muted">')[1].split("</span>")[0] for row in rows}


def test_the_projects_of_a_person(client, projects):
    page = client.get("/people/DAVE/").content.decode()
    assert listed(page) == {"open": "1 pull request · 1 issue · 0 reviews"}
    assert 'href="/projects/open/contributors/dave/"' in page
    assert 'href="https://github.com/dave"' in page  # the mark of GitHub
    erin = client.get("/people/erin/").content.decode()
    assert listed(erin) == {"open": "0 pull requests · 0 issues · 1 review"}


def test_private_projects_only_for_their_people(client, projects, bob):
    """Of private repositories, the page tells nothing to others: not even the GitHub name."""
    page = client.get("/people/carol/").content.decode()
    assert "data-person-none" in page and "Carol Hidden" not in page
    client.force_login(bob)
    page = client.get("/people/carol/").content.decode()
    assert listed(page) == {"secret": "1 pull request · 0 issues · 0 reviews"}
    assert "Carol Hidden" in page


def test_every_github_handle_has_a_page(client, db):
    page = client.get("/people/nobody-here/")
    assert page.status_code == 200 and "data-person-none" in page.content.decode()
    wrong = client.get("/people/no_handle/")
    assert wrong.status_code == 404 and "Not a GitHub handle" in wrong.content.decode()
    assert client.get(f"/people/{'a' * 40}/").status_code == 404  # longer than GitHub allows


def test_the_github_handles_lead_to_the_pages_of_people(client, projects, bob):
    """In a project to the page in the project, else to the page in all projects; the mark of
    GitHub after the handle leads to GitHub."""
    pulls = client.get("/projects/open/pull-requests/").content.decode()
    assert 'class="github-user" href="/projects/open/contributors/dave/"' in pulls
    assert 'aria-label="@dave on GitHub"' in pulls
    client.force_login(bob)
    members = client.get("/projects/open/settings/collaborators/").content.decode()
    assert 'href="/projects/open/contributors/bob/"' in members  # took no part: all projects
    assert client.get("/projects/open/contributors/bob/")["Location"] == "/people/bob/"
    account_page = client.get("/account/").content.decode()
    assert 'class="github-user" href="/people/bob/"' in account_page
