"""The GitHub handles proposed while a person types, the same in every field (/complete/people/)."""

import pytest
from allauth.socialaccount.models import SocialToken

from pycal_dashboard.models import Issue, Repository
from pycal_dashboard.services.project_editor import ProjectEditor
from pycal_dashboard.services.repository_update import RepositoryUpdate

pytestmark = pytest.mark.django_db
COMPLETE = "/complete/people/"


def account(github_id: int, login: str) -> dict:
    return {"id": github_id, "login": login, "avatar_url": "", "type": "User"}


def logins(client, query: str) -> list[str]:
    return [person["login"] for person in client.get(f"{COMPLETE}?{query}").json()["people"]]


@pytest.fixture
def projects(github, bob):
    """A public project of a public repository, and a private one of a private repository."""
    github.add_repository("open/one", installation=11)
    github.add_repository(
        "bob/secret", private=True, installation=12, collaborators={"bob": "read"}
    )
    github.add_issue("open/one", "Public", pull_request=True, user=account(301, "pubauthor"))
    github.add_issue("bob/secret", "Hidden", pull_request=True, user=account(302, "pubsecret"))
    github.add_review("bob/secret", 1, account(303, "pubreviewer"))
    public = ProjectEditor.create(bob, "Open", slug="open")
    secret = ProjectEditor.create(bob, "Secret", slug="secret", public=False)
    for project, name, private in ((public, "open/one", False), (secret, "bob/secret", True)):
        repository = Repository.objects.create(full_name=name, private=private)
        project.repositories.add(repository)
        assert RepositoryUpdate(repository).run()
    return public, secret


def test_the_people_of_private_projects_only_for_their_people(client, projects, bob, alice):
    """The authors and reviewers of a private repository are proposed to its project only."""
    client.force_login(bob)  # of both projects
    assert logins(client, "q=pub") == ["pubauthor", "pubreviewer", "pubsecret"]
    client.force_login(alice)  # of none: the public project only; GitHub knows them all
    SocialToken.objects.filter(account__user=alice).delete()  # without GitHub, the site alone
    answer = client.get(f"{COMPLETE}?q=pub").json()
    assert [person["login"] for person in answer["people"]] == ["pubauthor"]
    assert answer["error"]  # the token is missing: GitHub could not be searched
    assert client.get(f"{COMPLETE}?project=secret&q=pub").status_code == 404


def test_the_authors_of_the_project_come_first(client, github, projects, bob):
    """In a project, the authors of its pull requests first, then the others, then GitHub."""
    client.force_login(bob)
    assert logins(client, "project=secret&q=pub") == ["pubsecret", "pubauthor", "pubreviewer"]
    assert logins(client, "project=open&q=pub") == ["pubauthor", "pubreviewer", "pubsecret"]


def test_all_of_github_while_fewer_are_known(client, github, projects, bob):
    """The accounts of GitHub follow those that the site knows, each once, at most 10."""
    github.add_account("pubfromgithub", 400)
    for number in range(12):
        github.add_account(f"zz{number:02d}", 500 + number)
    client.force_login(bob)
    assert logins(client, "q=pub") == ["pubauthor", "pubreviewer", "pubsecret", "pubfromgithub"]
    assert len(logins(client, "q=zz")) == 10
    assert logins(client, "q=p") == ["pubauthor", "pubreviewer", "pubsecret"]  # 1 character
    assert logins(client, "q=pub%20x") == []  # no GitHub handle: GitHub is not asked
    assert logins(client, "signed_in=1&q=pub") == []  # for a role: only who signed in
    assert not Issue.objects.filter(author__login="pubfromgithub").exists()  # nothing kept


def test_every_field_of_github_handles_completes_the_same(client, projects, bob):
    from pycal_dashboard.models import PullRequestFilter, PullRequestStep

    client.force_login(bob)
    public, _secret = projects
    saved = PullRequestFilter.objects.create(project=public, name="Open", columns=[])
    step = PullRequestStep.objects.create(project=public, filter=saved, name="Review")
    pages = {
        "steps": f"/projects/{public.slug}/steps/?step={step.pk}",
        "scope": f"/projects/{public.slug}/message/scope/",
        "collaborators": f"/projects/{public.slug}/settings/collaborators/",
    }
    expected = {
        "steps": f'data-complete-people="{COMPLETE}?project=open"',
        "scope": f'data-complete-people="{COMPLETE}?project=open"',
        "collaborators": f'data-complete-people="{COMPLETE}?signed_in=1"',
    }
    for name, page in pages.items():
        assert expected[name] in client.get(page).content.decode(), name
