"""The issues and pull requests of the repositories, their authors, and the version of the data."""

import importlib
from io import StringIO

import pytest
from django.apps import apps
from django.core.management import call_command

from pycal_dashboard.github.data_version import DATA_VERSION
from pycal_dashboard.models import GitHubUser, Issue, Repository, UpdateJob
from pycal_dashboard.services.identity import GitHubIdentity
from pycal_dashboard.services.project_editor import ProjectEditor
from pycal_dashboard.services.repository_update import PER_PAGE, RepositoryUpdate
from pycal_dashboard.services.update_queue import UpdateQueue
from tests.conftest import person

pytestmark = pytest.mark.django_db

ALICE = {"id": 11, "login": "alice", "avatar_url": "https://avatars.example/a", "type": "User"}


@pytest.fixture
def repository(github):
    github.add_repository("collective/icalendar")
    github.add_issue("collective/icalendar", "A bug", user=ALICE, body="It breaks.")
    github.add_issue("collective/icalendar", "Fix the bug", pull_request=True, user=ALICE)
    github.add_issue("collective/icalendar", "Old", state="closed")
    github.add_issue(
        "collective/icalendar", "Merged", pull_request=True, state="closed", merged=True
    )
    github.add_issue("collective/icalendar", "Refused", pull_request=True, state="closed")
    return Repository.objects.create(full_name="collective/icalendar")


def test_all_issues_and_pull_requests_are_kept(repository):
    assert RepositoryUpdate(repository).run()
    issues = {i.title: i for i in Issue.objects.all()}
    assert len(issues) == 5
    bug = issues["A bug"]
    assert (bug.number, bug.pull_request, bug.status, bug.description) == (
        1,
        False,
        "open",
        "It breaks.",
    )
    assert bug.author.login == "alice" and bug.author.avatar_url == "https://avatars.example/a"
    assert bug.created.isoformat() == "2026-10-01T09:00:00+00:00"
    assert bug.url == "https://github.com/collective/icalendar/issues/1"
    assert issues["Fix the bug"].url == "https://github.com/collective/icalendar/pull/2"
    assert [issues[t].status for t in ("Old", "Merged", "Refused")] == [
        "closed",
        "merged",
        "closed",
    ]
    assert issues["Merged"].merged and issues["Old"].closed
    assert GitHubUser.objects.count() == 2  # alice and octocat, once each
    assert set(repository.issues.values_list("author__login", flat=True)) == {"alice", "octocat"}
    repository.refresh_from_db()
    assert repository.data_version == DATA_VERSION
    assert (repository.open_issues, repository.open_pull_requests) == (1, 1)


def test_the_next_update_reads_only_what_changed(github, repository):
    RepositoryUpdate(repository).run()
    assert github.issue_requests[-1].get("since") is None
    github.add_issue("collective/icalendar", "New", updated="2026-11-05T10:00:00Z")
    repository.refresh_from_db()
    RepositoryUpdate(repository).run()
    assert github.issue_requests[-1]["since"].startswith("2026-11-01T10:00:00")
    assert Issue.objects.filter(title="New").exists() and Issue.objects.count() == 6


def test_a_complete_reading_removes_what_github_no_longer_has(github, repository):
    RepositoryUpdate(repository).run()
    github.repositories["collective/icalendar"]["issues"].pop(0)  # deleted or transferred
    repository.refresh_from_db()
    RepositoryUpdate(repository).run()
    assert Issue.objects.count() == 5  # only the changes were read
    Repository.objects.update(data_version=0)  # older data: read completely again
    repository.refresh_from_db()
    RepositoryUpdate(repository).run()
    assert not Issue.objects.filter(title="A bug").exists() and Issue.objects.count() == 4


def test_many_issues_are_read_page_by_page(github):
    github.add_repository("big/one", issues=PER_PAGE + 5)
    repository = Repository.objects.create(full_name="big/one")
    assert RepositoryUpdate(repository).run()
    assert Issue.objects.count() == PER_PAGE + 5
    assert [r["page"] for r in github.issue_requests] == ["1", "2"]


def test_an_error_keeps_the_older_version(github, repository, monkeypatch):
    def broken(self, item):
        raise ValueError("broken")

    monkeypatch.setattr(RepositoryUpdate, "keep", broken)
    assert not RepositoryUpdate(repository).run()
    repository.refresh_from_db()
    assert repository.data_version == 0 and repository.error_code


def test_the_github_user_is_linked_to_the_person_who_signs_in(repository, github):
    RepositoryUpdate(repository).run()
    alice = GitHubUser.objects.get(login="alice")
    assert alice.user is None and alice.url == "https://github.com/alice"
    user = person(11, "alice")
    GitHubIdentity.keep_profile(user)
    alice.refresh_from_db()
    assert alice.user == user and user.github_user == alice
    assert list(user.github_user.issues.values_list("title", flat=True)) == ["Fix the bug", "A bug"]


def test_a_github_user_recorded_later_finds_the_person(repository):
    user = person(11, "alice")  # signed in before
    RepositoryUpdate(repository).run()
    assert GitHubUser.objects.get(github_id=11).user == user


def test_a_renamed_account_keeps_its_issues(repository, github):
    RepositoryUpdate(repository).run()
    GitHubUser.record({**ALICE, "login": "alice-new"})
    assert GitHubUser.objects.filter(github_id=11).get().login == "alice-new"
    assert Issue.objects.filter(author__login="alice-new").count() == 2


def test_projects_with_older_data_are_updated_after_the_migration(github, repository, bob):
    project = ProjectEditor.create(bob, "iCalendar")
    project.repositories.add(repository)
    ProjectEditor.create(bob, "Empty")
    out = StringIO()
    call_command("prepare", stdout=out)
    assert "1 projects have older data of GitHub" in out.getvalue()
    job = UpdateJob.objects.get()
    assert (job.project, job.status) == (project, UpdateJob.QUEUED)
    out = StringIO()
    call_command("update_projects", stdout=out)
    assert "1 updates done" in out.getvalue()
    repository.refresh_from_db()
    assert repository.data_version == DATA_VERSION and Issue.objects.count() == 5
    assert UpdateQueue.outdated() == 0  # up to date: nothing more to do


def test_the_migration_records_the_people_who_signed_in(db):
    user = person(42, "carol")
    user.socialaccount_set.update(
        extra_data={"login": "carol", "avatar_url": "https://a.example/c"}
    )
    migration = importlib.import_module("pycal_dashboard.migrations.0010_issues_and_github_users")
    migration.record_github_users(apps, None)
    carol = GitHubUser.objects.get(github_id=42)
    assert (carol.login, carol.avatar_url, carol.user) == ("carol", "https://a.example/c", user)


# the tab Pull requests


@pytest.fixture
def project(bob, repository):
    project = ProjectEditor.create(bob, "iCalendar")
    project.repositories.add(repository)
    RepositoryUpdate(repository).run()
    return project


def test_the_pull_requests_of_a_project_are_public(client, project, github):
    github.add_repository("PyCalendar/plann")
    github.add_issue("PyCalendar/plann", "Plann change", pull_request=True)
    plann = Repository.objects.create(full_name="PyCalendar/plann")
    project.repositories.add(plann)
    RepositoryUpdate(plann).run()
    page = client.get(f"/projects/{project.slug}/pull-requests/").content.decode()
    assert "4 pull requests" in page  # of both repositories, together
    for title in ("Fix the bug", "Merged", "Refused", "Plann change"):
        assert title in page
    assert "A bug" not in page  # an issue
    assert 'data-github-user="alice"' in page
    assert 'src="https://avatars.example/a?s=40"' in page
    assert 'href="https://github.com/alice"' in page
    assert 'href="https://github.com/collective/icalendar/pull/2"' in page


def test_the_pull_requests_are_a_table_with_columns_to_choose(client, project):
    """No filters; a details of the columns to display, which CSS shows and hides."""
    page = client.get(f"/projects/{project.slug}/pull-requests/").content.decode()
    assert "?state=" not in page and "the newest first, as of the last update" not in page
    choice = page.split("data-columns>")[1].split("</details>")[0]
    assert "Display: <span data-columns-shown>Title, Step, Number, Creator</span>" in choice
    for column in ("title", "number", "creator"):  # shown first
        assert f'id="column-{column}" data-column="{column}" checked>' in choice
    for column in ("status", "organization", "repository", "created"):  # hidden first
        assert f'id="column-{column}" data-column="{column}">' in choice
    for column in ("status", "title", "organization", "repository", "number", "creator", "created"):
        assert f'<th class="col-{column}">' in page and f'<td class="col-{column}">' in page
    row = page.split('data-pull-request="collective/icalendar#2" data-status="open">')[1]
    row = row.split("</tr>")[0]
    assert (
        'class="col-link"' in row and 'href="https://github.com/collective/icalendar/pull/2"' in row
    )
    assert '<td class="col-organization">collective</td>' in row
    assert '<td class="col-repository">icalendar</td>' in row
    number = '<a href="https://github.com/collective/icalendar/pull/2">#2</a>'
    assert f'<td class="col-number">{number}</td>' in row
    assert 'data-status="merged"' in page and 'data-status="closed"' in page
    assert "pull-table.js" in page


def test_the_columns_are_hidden_by_css():
    """Each column has its rule; without Status, the first cell has the color of the status."""
    from pathlib import Path

    css = (Path(__file__).parent.parent / "static" / "style.css").read_text()
    for column in ("status", "title", "organization", "repository", "number", "creator", "created"):
        assert f".pull-table:has(#column-{column}:not(:checked)) .col-{column}" in css
    for status, color in (("open", "success"), ("merged", "merged"), ("closed", "danger")):
        assert (
            f'.pull-table:has(#column-status:not(:checked)) tr[data-status="{status}"] '
            f"{{ border-left-color: var(--{color}); }}"
        ) in css
    # the icon of GitHub only while neither the title nor the number links the pull request
    assert ".pull-table:has(#column-title:checked) .col-link" in css
    assert ".pull-table:has(#column-number:checked) .col-link" in css


@pytest.mark.parametrize(("asked", "size"), [("10", 10), ("100", 100), ("1000", 25), ("x", 25)])
def test_the_number_per_page(client, project, asked, size):
    page = client.get(f"/projects/{project.slug}/pull-requests/?per_page={asked}").content.decode()
    assert f'<option value="{size}" selected>' in page
    data = client.get(f"/projects/{project.slug}/pull-requests.json?per_page={asked}").json()
    assert data["per_page"] == size


def test_the_tile_of_open_pull_requests_leads_to_them(client, project):
    page = client.get(f"/projects/{project.slug}/").content.decode()
    tile = page.split("data-open-pull-requests>")[1].split("</li>")[0]
    assert f'href="/projects/{project.slug}/pull-requests/"' in tile


def test_the_tabs_are_in_order_overview_public_private(client, project, bob):
    client.force_login(bob)
    page = client.get(f"/projects/{project.slug}/pull-requests/").content.decode()
    tabs = page.split('<ul class="tabs">')[1].split("</ul>")[0]
    names = [part.split("<")[0] for part in tabs.split('">')[1:] if part.split("<")[0]]
    assert names == [
        "Overview",
        "Pull requests",
        "Filters",
        "Steps",
        "PR Message",
        "Repositories",
        "Collaborators",
        "Settings",
    ]
    client.logout()
    page = client.get(f"/projects/{project.slug}/pull-requests/").content.decode()
    assert "Repositories</a>" not in page.split('<ul class="tabs">')[1].split("</ul>")[0]


def test_many_pull_requests_have_pages(client, github, bob):
    github.add_repository("big/one", pulls=60)
    big = Repository.objects.create(full_name="big/one")
    project = ProjectEditor.create(bob, "Big")
    project.repositories.add(big)
    RepositoryUpdate(big).run()
    page = client.get(f"/projects/{project.slug}/pull-requests/").content.decode()
    assert "Page 1 of 3" in page and page.count("data-pull-request=") == 25
    assert 'href="?per_page=25&amp;page=2"' in page
    page = client.get(f"/projects/{project.slug}/pull-requests/?per_page=50&page=2")
    assert page.content.decode().count("data-pull-request=") == 10
    data = client.get(f"/projects/{project.slug}/pull-requests.json?per_page=100").json()
    assert (data["count"], data["pages"], len(data["pull_requests"])) == (60, 1, 60)


def test_private_repositories_hide_their_pull_requests(client, project, repository):
    Repository.objects.filter(pk=repository.pk).update(private=True)
    page = client.get(f"/projects/{project.slug}/pull-requests/").content.decode()
    assert "Fix the bug" not in page


def test_a_person_without_a_github_user_is_unknown():
    from pycal_dashboard.templatetags.github import github_user

    assert github_user(None)["login"] == ""
    assert github_user("octocat")["avatar"] == "https://avatars.githubusercontent.com/octocat?s=40"
    without_avatar = GitHubUser(login="bob", github_id=1)
    assert github_user(without_avatar)["avatar"] == "https://avatars.githubusercontent.com/bob?s=40"


# the people of GitHub with their avatar, and the completion when sharing


def test_the_collaborators_have_their_avatar(client, project, bob):
    client.force_login(bob)
    page = client.get(f"/projects/{project.slug}/collaborators/").content.decode()
    row = page.split('data-member="bob"')[1].split("</tr>")[0]
    assert 'data-github-user="bob"' in row and 'class="avatar"' in row
    assert 'href="https://github.com/bob"' in row
    assert "data-complete-people=" in page and "person-complete.js" in page


def test_complete_the_people_to_share_with(client, bob, alice):
    GitHubUser.objects.filter(login="alice").update(
        name="Alice Liddell", avatar_url="https://a.x/1"
    )
    GitHubUser.record({"id": 999, "login": "alicia"})  # never signed in: no role possible
    assert client.get("/people/complete/?q=al").status_code == 302  # sign in first
    client.force_login(bob)
    people = client.get("/people/complete/?q=@AL").json()["people"]
    assert people == [{"login": "alice", "name": "Alice Liddell", "avatar": "https://a.x/1?s=40"}]
    assert client.get("/people/complete/?q=liddell").json()["people"][0]["login"] == "alice"
    assert client.get("/people/complete/?q=").json()["people"] == []


def test_a_repository_without_issues_is_read_completely_once(github):
    github.add_repository("empty/one")
    repository = Repository.objects.create(full_name="empty/one")
    RepositoryUpdate(repository).run()
    repository.refresh_from_db()
    assert repository.issues_changed is not None
    RepositoryUpdate(repository).run()
    assert github.issue_requests[-1].get("since")


def test_the_update_is_at_the_bottom_of_the_overview(client, project, bob):
    """Up to date is the usual case: a line at the bottom, after the repositories."""
    from pycal_dashboard.services.update_queue import UpdateQueue

    UpdateQueue.add(project)
    UpdateQueue.work()
    client.force_login(bob)
    page = client.get(project.path()).content.decode()
    assert page.index("data-repositories") < page.index('data-status="current"')
    assert '<footer class="update-line muted" data-status="current">' in page
    assert "data-update" in page.split('data-status="current"')[1]


def test_the_roles_link_what_each_may_do(client, project, bob):
    client.force_login(bob)
    page = client.get(project.path("collaborators/")).content.decode()
    link = 'href="https://docs.example.org/tutorial/projects.html#project-roles"'
    table, share = page.split("data-share")
    assert link in table.split("<thead>")[1].split("</thead>")[0]  # next to Role
    assert link in share and 'title="Help: What each role may do' in share


def test_the_creator_is_shown_by_the_github_name_alone(client, project):
    GitHubUser.objects.filter(login="alice").update(name="Alice Liddell")
    page = client.get(f"/projects/{project.slug}/pull-requests/").content.decode()
    assert 'data-github-user="alice"' in page and "Alice Liddell" not in page


def test_people_who_signed_in_before_their_github_account_was_kept(client, bob):
    """A profile without a kept account of GitHub is proposed by its handle."""
    from django.contrib.auth import get_user_model

    from pycal_dashboard.models import Profile

    carol = get_user_model().objects.create_user("carol")
    Profile.objects.update_or_create(user=carol, defaults={"github_name": "carolyn"})
    assert not GitHubUser.objects.filter(login="carolyn").exists()
    client.force_login(bob)
    people = client.get("/people/complete/?q=car").json()["people"]
    assert people == [
        {
            "login": "carolyn",
            "name": "",
            "avatar": "https://avatars.githubusercontent.com/carolyn?s=40",
        }
    ]
