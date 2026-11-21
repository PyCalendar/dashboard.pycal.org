"""Projects: create, see, change, share; repositories public and private; updates."""

import re

import pytest
from django.core import mail
from django.utils import timezone

from pycal_dashboard.models import (
    Installation,
    Profile,
    Project,
    ProjectMember,
    Repository,
    UpdateJob,
)
from pycal_dashboard.services.identity import GitHubIdentity
from pycal_dashboard.services.permission_notice import PermissionNotice
from pycal_dashboard.services.project_access import ProjectAccess
from pycal_dashboard.services.project_editor import ProjectEditor
from pycal_dashboard.services.project_status import ProjectStatus
from pycal_dashboard.services.repository_update import RepositoryUpdate
from pycal_dashboard.services.update_queue import UpdateQueue
from tests.conftest import person

pytestmark = pytest.mark.django_db


@pytest.fixture
def project(bob):
    return ProjectEditor.create(bob, "iCalendar", "The calendars of Python")


@pytest.fixture
def private_project(bob):
    return ProjectEditor.create(bob, "Secret", public=False)


@pytest.fixture
def repositories(github):
    github.add_repository("collective/icalendar", issues=3, pulls=2, installation=11)
    github.add_repository("PyCalendar/plann", issues=1, pulls=0)
    github.add_repository(
        "bob/secret", private=True, installation=12, collaborators={"bob": "read"}
    )
    return github


def add(client, project, *names):
    return client.post(
        f"/projects/{project.slug}/repositories/", {"repository": list(names)}, follow=True
    )


# the GitHub handle


def test_the_github_name_is_kept_at_the_sign_in(client, db):
    user = person(60, "carol")
    Profile.objects.filter(user=user).delete()
    user.socialaccount_set.update(extra_data={"login": "Carol-Renamed"})
    client.force_login(user)
    profile = Profile.objects.get(user=user)
    assert (profile.github_name, profile.github_id, str(profile)) == (
        "Carol-Renamed",
        "60",
        "@Carol-Renamed",
    )
    assert Profile.with_github_name("@carol-renamed") == profile
    assert Profile.with_github_name(" ") is None


def test_the_profile_needs_github(db, django_user_model):
    assert GitHubIdentity.keep_profile(django_user_model.objects.create(username="local")) is None


# the list and the overview


def test_the_projects_page_is_in_the_menu(client, project):
    page = client.get("/").content.decode()
    assert 'href="/projects/"' in page
    page = client.get("/projects/").content.decode()
    assert "iCalendar" in page and "The calendars of Python" in page
    assert "Create a project" in page and "data-private-hint" in page


def test_private_projects_are_listed_only_for_their_collaborators(client, private_project, alice):
    assert "Secret" not in client.get("/projects/").content.decode()
    assert client.get(f"/projects/{private_project.slug}/").status_code == 404
    client.force_login(alice)
    assert "Secret" not in client.get("/projects/").content.decode()
    client.force_login(private_project.created_by)
    assert "Secret" in client.get("/projects/").content.decode()
    assert client.get(f"/projects/{private_project.slug}/").status_code == 200


def test_site_admins_see_every_project(client, private_project, admin):
    client.force_login(admin)
    assert "Secret" in client.get("/projects/").content.decode()
    assert ProjectAccess(private_project, admin).is_owner


def test_the_overview_of_a_project_not_updated_yet(client, project):
    page = client.get(f"/projects/{project.slug}/").content.decode()
    assert "Not updated yet" in page and "never" in page
    assert "data-update" not in page  # visitors do not update
    assert "The project has no repositories yet." in page


def test_a_missing_project(client, db):
    page = client.get("/projects/nothing/")
    assert page.status_code == 404 and "Project not found" in page.content.decode()


def test_the_json_of_the_projects(client, project, private_project, bob, repositories):
    client.force_login(bob)
    add(client, project, "collective/icalendar")
    data = client.get("/projects.json").json()
    assert [p["slug"] for p in data["projects"]] == [project.slug]  # also with the session
    assert data["projects"][0]["repositories"] == ["collective/icalendar"]
    UpdateQueue.add(project)
    UpdateQueue.work()
    data = client.get(f"/projects/{project.slug}.json").json()
    assert (data["open_issues"], data["open_pull_requests"]) == (3, 2)
    assert data["repositories"][0]["full_name"] == "collective/icalendar"
    assert client.get(f"/projects/{private_project.slug}.json").status_code == 404


# creating and changing


def test_creating_needs_a_sign_in(client, db):
    answer = client.get("/projects/new/")
    assert answer.status_code == 302 and "/accounts/login/" in answer["Location"]


def test_create_a_project(client, bob):
    client.force_login(bob)
    assert "Create the project" in client.get("/projects/new/").content.decode()
    answer = client.post(
        "/projects/new/",
        {"name": "  My   project ", "description": "Mine", "visibility": "private"},
    )
    project = Project.objects.get()
    assert (project.name, project.public) == ("My project", False)
    assert re.fullmatch("[0-9a-f]{6}", project.slug)  # random by default
    assert answer["Location"] == f"/projects/{project.slug}/repositories/"
    assert ProjectMember.objects.get(project=project).role == ProjectMember.OWNER


def test_a_project_needs_a_name(client, bob):
    client.force_login(bob)
    page = client.post("/projects/new/", {"name": "  "})
    assert page.status_code == 400 and "The project needs a name" in page.content.decode()


def test_change_and_delete_a_project(client, project, bob):
    client.force_login(bob)
    assert (
        "Delete the project" in client.get(f"/projects/{project.slug}/settings/").content.decode()
    )
    client.post(
        f"/projects/{project.slug}/settings/",
        {"name": "New", "description": "Other", "visibility": "private"},
    )
    project.refresh_from_db()
    assert (project.name, project.description, project.public) == ("New", "Other", False)
    page = client.post(f"/projects/{project.slug}/settings/", {"delete": "yes"}, follow=True)
    assert "Tick the box" in page.content.decode() and Project.objects.exists()
    client.post(f"/projects/{project.slug}/settings/", {"delete": "yes", "confirm": "yes"})
    assert not Project.objects.exists()


def test_readers_may_not_change_writers_may_not_share(client, project, alice):
    ProjectEditor(ProjectAccess(project, project.created_by)).share("alice", "read")
    client.force_login(alice)
    page = client.get(f"/projects/{project.slug}/settings/")
    assert page.status_code == 403 and "You may not change this project" in page.content.decode()
    assert client.post(f"/projects/{project.slug}/update/").status_code == 403
    assert client.get(f"/projects/{project.slug}/repositories/").status_code == 403
    ProjectEditor(ProjectAccess(project, project.created_by)).share("alice", "write")
    client.post(
        f"/projects/{project.slug}/settings/",
        {"name": "Changed", "description": "", "visibility": "private"},
    )
    project.refresh_from_db()
    assert project.name == "Changed" and project.public  # writers do not change who sees it
    answer = client.post(
        f"/projects/{project.slug}/collaborators/", {"github_name": "x", "role": "read"}
    )
    assert answer.status_code == 403 and "Only the owners" in answer.content.decode()
    answer = client.post(f"/projects/{project.slug}/settings/", {"delete": "yes"})
    assert answer.status_code == 403 and Project.objects.exists()
    page = client.get(f"/projects/{project.slug}/settings/").content.decode()
    assert "Delete the project" not in page and "Only the owners change it." in page


# sharing


def test_share_the_project(client, project, bob, alice):
    client.force_login(bob)
    page = client.post(
        f"/projects/{project.slug}/collaborators/",
        {"github_name": "@Alice", "role": "write"},
        follow=True,
    ).content.decode()
    assert "@alice may change the project." in page
    assert ProjectMember.objects.get(user=alice).role == "write"
    member = ProjectMember.objects.get(user=alice)
    client.post(f"/projects/{project.slug}/collaborators/", {"remove": member.pk})
    assert not ProjectMember.objects.filter(user=alice).exists()


@pytest.mark.parametrize("role", ["read", "write"])
def test_only_owners_change_roles_and_add_collaborators(client, project, bob, alice, role):
    """Readers and writers add nobody, change no role and remove nobody, not even themselves."""
    carol = person(3, "carol")
    owner = ProjectEditor(ProjectAccess(project, bob))
    owner.share("alice", role)
    owner.share("carol", "read")
    client.force_login(alice)
    address = f"/projects/{project.slug}/collaborators/"
    page = client.get(address).content.decode()
    assert "data-share" not in page and 'name="remove"' not in page and 'name="role"' not in page
    for data in (
        {"github_name": "bob", "role": "read"},  # an owner loses the role
        {"github_name": "carol", "role": "owner"},  # another one gets more
        {"github_name": "alice", "role": "owner"},  # oneself
        {"remove": ProjectMember.objects.get(user=carol).pk},
        {"remove": ProjectMember.objects.get(user=bob).pk},
    ):
        answer = client.post(address, data)
        assert answer.status_code == 403 and "Only the owners" in answer.content.decode()
    roles = dict(ProjectMember.objects.values_list("user__username", "role"))
    assert roles == {"bob": "owner", "alice": role, "carol": "read"}


@pytest.mark.parametrize(
    ("name", "role", "error"),
    [("nobody", "read", "Nobody with this GitHub handle"), ("alice", "boss", "Unknown role")],
)
def test_share_errors(client, project, bob, alice, name, role, error):
    client.force_login(bob)
    page = client.post(
        f"/projects/{project.slug}/collaborators/", {"github_name": name, "role": role}
    )
    assert page.status_code in (400, 404) and error in page.content.decode()


def test_the_people_are_the_collaborators_now(client, project, bob):
    """The tab People is called Collaborators; its old address leads there."""
    client.force_login(bob)
    page = client.get(f"/projects/{project.slug}/collaborators/").content.decode()
    assert "Collaborators of the project" in page and ">People<" not in page
    answer = client.get(f"/projects/{project.slug}/people/?a=1")
    assert answer.status_code == 301
    assert answer["Location"] == f"/projects/{project.slug}/collaborators/?a=1"


def test_the_only_owner_cannot_change_their_role_on_the_page(client, project, bob, alice):
    """The page offers no change and no removal for the only owner; with two, it does."""
    client.force_login(bob)
    url = f"/projects/{project.slug}/collaborators/"
    client.post(url, {"github_name": "alice", "role": "read"})
    page = client.get(url).content.decode()
    bob_row = page.split('data-member="bob"')[1].split("</tr>")[0]
    alice_row = page.split('data-member="alice"')[1].split("</tr>")[0]
    assert "data-only-owner" in bob_row and "<select" not in bob_row and "remove" not in bob_row
    assert "<select" in alice_row and 'name="remove"' in alice_row
    client.post(url, {"github_name": "alice", "role": "owner"})
    page = client.get(url).content.decode()
    assert "data-only-owner" not in page
    assert page.split('data-member="bob"')[1].split("</tr>")[0].count("<select") == 1


def test_a_project_keeps_an_owner(client, project, bob, alice):
    client.force_login(bob)
    owner = ProjectMember.objects.get(user=bob)
    page = client.post(f"/projects/{project.slug}/collaborators/", {"remove": owner.pk})
    assert "The project needs an owner" in page.content.decode()
    page = client.post(
        f"/projects/{project.slug}/collaborators/", {"github_name": "bob", "role": "read"}
    )
    assert "The project needs an owner" in page.content.decode()
    client.post(
        f"/projects/{project.slug}/collaborators/", {"github_name": "alice", "role": "owner"}
    )
    client.post(f"/projects/{project.slug}/collaborators/", {"github_name": "bob", "role": "read"})
    assert ProjectMember.objects.get(user=bob).role == "read"


def test_readers_see_the_collaborators_but_do_not_share(client, private_project, alice):
    ProjectEditor(ProjectAccess(private_project, private_project.created_by)).share("alice", "read")
    client.force_login(alice)
    page = client.get(f"/projects/{private_project.slug}/collaborators/").content.decode()
    assert "@bob" in page and "The owners of the project share it." in page
    assert "data-share" not in page


# repositories


def test_add_a_public_repository_by_name_or_link(client, project, bob, repositories):
    client.force_login(bob)
    page = add(client, project, "https://github.com/collective/icalendar/pulls").content.decode()
    assert "collective/icalendar is added." in page
    repository = Repository.objects.get()
    assert repository.installation.github_id == 11 and repository.app_installed
    assert "app installed" in page
    page = add(client, project, "collective/icalendar").content.decode()
    assert "collective/icalendar is in the project already." in page
    assert repositories.writes() == []


def test_add_repositories_errors(client, project, bob, repositories):
    client.force_login(bob)
    page = add(client, project, "not a name", "nobody/nothing").content.decode()
    assert "Not the name of a repository" in page and "Repository not found" in page


def test_the_install_step_names_the_repositories_without_the_app(
    client, project, bob, repositories
):
    client.force_login(bob)
    page = add(client, project, "PyCalendar/plann").content.decode()
    assert "1 repository has no GitHub App yet." in page and "app not installed" in page
    assert "https://github.com/apps/dashboard-test/installations/new" in page
    assert "https://docs.example.org/reference/permissions.html" in page
    assert "create and update a comment of the site on a pull request" in page


def test_the_install_step_is_shown_only_when_the_app_is_missing_or_out_of_date(
    client, project, bob
):
    """With the app and its permissions on every repository, there is nothing to install."""
    from pycal_dashboard.github.permissions import REQUIRED

    installation = Installation.objects.create(
        github_id=11,
        account_login="collective",
        account_type="Organization",
        permissions=dict(REQUIRED),
    )
    project.repositories.add(
        Repository.objects.create(full_name="collective/icalendar", installation=installation)
    )
    client.force_login(bob)
    page = client.get(f"/projects/{project.slug}/repositories/").content.decode()
    assert "data-install-step" not in page and "app installed" in page
    installation.permissions = {"metadata": "read"}
    installation.save()
    page = client.get(f"/projects/{project.slug}/repositories/").content.decode()
    assert "data-install-step" in page and "data-install-link" not in page
    assert "1 repository has the app without the permissions it needs now." in page
    assert installation.settings_url in page


def test_a_private_repository_needs_a_private_project(client, project, bob, repositories):
    client.force_login(bob)
    page = add(client, project, "bob/secret").content.decode()
    assert "A private repository needs a private project" in page


def test_add_a_private_repository(client, private_project, bob, alice, repositories):
    client.force_login(bob)
    page = add(client, private_project, "bob/secret").content.decode()
    assert "bob/secret is added." in page
    assert Repository.objects.get(full_name="bob/secret").private
    page = client.post(
        f"/projects/{private_project.slug}/settings/",
        {"name": "Secret", "visibility": "public"},
    )
    assert "The project has private repositories" in page.content.decode()


def test_a_private_repository_needs_access(client, alice, repositories):
    project = ProjectEditor.create(alice, "Alice", public=False)
    client.force_login(alice)
    page = add(client, project, "bob/secret").content.decode()
    assert "Repository not found" in page
    repositories.repositories["bob/secret"]["installation"] = None
    client.force_login(project.created_by)
    assert "Repository not found" in add(client, project, "bob/secret").content.decode()


def test_choose_from_an_organization_and_search(client, project, bob, repositories):
    repositories.organizations = ["PyCalendar"]
    client.force_login(bob)
    url = f"/projects/{project.slug}/repositories/"
    page = client.get(url, {"owner": "PyCalendar"}).content.decode()
    assert '<option value="PyCalendar" selected>' in page and '<option value="bob"' in page
    assert 'value="PyCalendar/plann"' in page
    page = client.get(url, {"search": "ical"}).content.decode()
    assert 'value="collective/icalendar"' in page
    page = client.get(url, {"search": "zzz"}).content.decode()
    assert "Nothing found." in page
    page = client.get(url, {"owner": "somebody"}).content.decode()
    assert "No repositories that you may see." in page


def test_without_a_token_the_page_says_to_sign_in_again(client, project, bob, repositories):
    from allauth.socialaccount.models import SocialToken

    SocialToken.objects.all().delete()
    client.force_login(bob)
    page = client.get(f"/projects/{project.slug}/repositories/").content.decode()
    assert "Sign in again to list your repositories" in page and "data-github-error" in page
    assert "Sign in again" in add(client, project, "collective/icalendar").content.decode()


def test_complete_a_repository_name(client, project, bob, repositories):
    client.force_login(bob)
    add(client, project, "PyCalendar/plann")
    names = client.get("/repositories/complete/", {"q": "pla"}).json()["repositories"]
    assert names == ["PyCalendar/plann"]
    names = client.get("/repositories/complete/", {"q": "collective/ic"}).json()["repositories"]
    assert names == ["collective/icalendar"]
    assert client.get("/repositories/complete/", {"q": "i"}).json() == {"repositories": []}


def test_remove_a_repository(client, project, bob, repositories):
    client.force_login(bob)
    add(client, project, "PyCalendar/plann")
    repository = Repository.objects.get()
    page = client.post(
        f"/projects/{project.slug}/repositories/", {"remove": repository.pk}, follow=True
    ).content.decode()
    assert "PyCalendar/plann is removed." in page
    assert Repository.objects.exists() and not project.repositories.exists()


def test_a_repository_that_became_private_is_hidden_from_visitors(client, project, bob):
    project.repositories.add(Repository.objects.create(full_name="o/closed", private=True))
    assert "o/closed" not in client.get(f"/projects/{project.slug}/").content.decode()
    client.force_login(bob)
    assert "o/closed" in client.get(f"/projects/{project.slug}/").content.decode()


# the update


def test_update_a_project(client, project, bob, repositories):
    client.force_login(bob)
    add(client, project, "collective/icalendar", "PyCalendar/plann")
    client.post(f"/projects/{project.slug}/update/")
    job = UpdateJob.objects.get()
    assert (job.status, job.percent) == ("queued", 0)
    page = client.get(f"/projects/{project.slug}/").content.decode()
    assert 'http-equiv="refresh"' in page and "data-progress" in page
    assert "0 of 2 repositories updated from GitHub" in page
    client.post(f"/projects/{project.slug}/update/")  # one at a time
    assert UpdateJob.objects.count() == 1
    assert UpdateQueue.work() == 1
    job.refresh_from_db()
    assert (job.status, job.done, job.total, job.errors, job.percent) == ("done", 2, 2, 0, 100)
    page = client.get(f"/projects/{project.slug}/").content.decode()
    assert "Up to date" in page and 'http-equiv="refresh"' not in page
    assert "<li data-open-issues><strong>4</strong>" in page
    assert "<strong>2</strong>" in page.split("data-open-pull-requests>")[1].split("</li>")[0]
    icalendar = Repository.objects.get(full_name="collective/icalendar")
    assert (icalendar.open_issues, icalendar.open_pull_requests) == (3, 2)
    assert repositories.writes() == []


def test_an_added_repository_is_read_at_once(client, project, bob, repositories):
    """Adding a repository queues an update; the worker reads it without pressing Update."""
    client.force_login(bob)
    add(client, project, "collective/icalendar")
    job = UpdateJob.objects.get()
    assert (job.status, job.requested_by) == (UpdateJob.QUEUED, bob)
    add(client, project, "PyCalendar/plann")  # the job waits: it reads both
    assert UpdateJob.objects.count() == 1
    assert UpdateQueue.work() == 1
    job.refresh_from_db()
    assert (job.status, job.done, job.total) == (UpdateJob.DONE, 2, 2)
    assert Repository.objects.get(full_name="PyCalendar/plann").open_issues == 1


def test_a_repository_added_while_an_update_runs_is_read_after_it(
    client, project, bob, repositories
):
    """An update that runs read the repositories before; another one reads the new one."""
    client.force_login(bob)
    running = UpdateJob.objects.create(project=project, status=UpdateJob.RUNNING)
    add(client, project, "collective/icalendar")
    queued = UpdateJob.objects.exclude(pk=running.pk).get()
    assert queued.status == UpdateJob.QUEUED
    client.post(f"/projects/{project.slug}/update/")  # Update joins the waiting one
    assert UpdateJob.objects.count() == 2


def test_nothing_added_reads_nothing(client, project, bob, repositories):
    client.force_login(bob)
    add(client, project, "nobody/nothing")
    assert not UpdateJob.objects.exists()


def test_the_update_reads_without_a_token_when_the_app_is_missing(project, repositories):
    project.repositories.add(Repository.objects.create(full_name="PyCalendar/plann"))
    UpdateQueue.add(project)
    UpdateQueue.work()
    pulls = [r for r in repositories.requests if r.url.path.endswith("/plann/pulls")]
    assert pulls and "Authorization" not in pulls[0].headers


def test_a_repository_that_cannot_be_read(client, project, repositories):
    project.repositories.add(Repository.objects.create(full_name="gone/away"))
    UpdateQueue.add(project)
    UpdateQueue.work()
    assert UpdateJob.objects.get().errors == 1
    page = client.get(f"/projects/{project.slug}/").content.decode()
    assert "Some repositories could not be updated" in page and "could not be updated" in page
    assert Repository.objects.get().error_code == "GitHubNotFound"


def test_status_out_of_date(project, repositories):
    project.repositories.add(Repository.objects.create(full_name="PyCalendar/plann"))
    UpdateQueue.add(project)
    UpdateQueue.work()
    project.refresh_from_db()
    assert ProjectStatus.of(project, list(project.repositories.all())).up_to_date
    Project.objects.update(updated=timezone.now() - timezone.timedelta(days=2))
    project.refresh_from_db()
    assert ProjectStatus.of(project, list(project.repositories.all())).state == "outdated"


def test_a_stuck_job_is_taken_again(project):
    job = UpdateJob.objects.create(
        project=project,
        status=UpdateJob.RUNNING,
        started=timezone.now() - timezone.timedelta(hours=1),
        done=3,
    )
    assert UpdateQueue.claim() == job
    job.refresh_from_db()
    assert job.done == 0 and UpdateQueue.claim() is None


def test_the_number_of_pull_requests_comes_from_the_last_page():
    class Answer:
        headers = {
            "link": '<https://api.github.com/x?page=2>; rel="next", <https://api.github.com/x?per_page=1&page=17>; rel="last"'
        }

    assert RepositoryUpdate.count(Answer()) == 17


def test_the_worker_starts_once(monkeypatch, project):
    from pycal_dashboard.services.update_worker import UpdateWorker

    started = []
    monkeypatch.setattr(UpdateWorker, "enabled", True)
    monkeypatch.setattr(UpdateWorker, "main", staticmethod(lambda: started.append(1)))
    monkeypatch.setattr(UpdateWorker, "_thread", None)
    assert UpdateWorker.start()
    UpdateWorker._thread.join()
    assert started == [1]


def test_the_fixture_starts_and_stops_the_worker(update_worker, monkeypatch):
    """The thread stops when asked; a stopped worker starts no other one."""
    import threading

    started = threading.Event()

    def main():
        started.set()
        while not update_worker.stopping():
            threading.Event().wait(0.01)

    monkeypatch.setattr(update_worker, "main", staticmethod(main))
    assert update_worker.start() and started.wait(5)
    update_worker.stop()
    assert not update_worker.enabled and update_worker._thread is None
    assert not update_worker.start()


def test_a_stopping_worker_leaves_the_queue(monkeypatch, project, repositories):
    from pycal_dashboard.services.update_worker import UpdateWorker

    project.repositories.add(Repository.objects.create(full_name="collective/icalendar"))
    UpdateQueue.add(project)
    monkeypatch.setattr(UpdateWorker, "stopping", classmethod(lambda cls: True))
    assert UpdateQueue.work() == 0
    assert UpdateJob.objects.get().status == UpdateJob.QUEUED


# the emails about permissions


def test_writers_of_projects_are_told_about_missing_permissions(project, alice, repositories):
    from allauth.account.models import EmailAddress

    EmailAddress.objects.create(user=alice, email="alice@example.org", verified=True, primary=True)
    editor = ProjectEditor(ProjectAccess(project, project.created_by))
    editor.share("alice", "write")
    repositories.app["permissions"] = {"metadata": "read"}
    installation = Installation.objects.create(
        github_id=11,
        account_login="collective",
        account_type="Organization",
        permissions={"metadata": "read"},
    )
    project.repositories.add(
        Repository.objects.create(full_name="collective/icalendar", installation=installation)
    )
    assert PermissionNotice(installation).send_if_needed() == 1
    message = mail.outbox[0]
    assert message.to == ["alice@example.org"]
    assert "https://github.com/organizations/collective/settings/installations/11" in message.body
    assert "a project with a repository it is installed on" in message.body


def test_busy_writes_are_tried_again(monkeypatch):
    from django.db import OperationalError

    from pycal_dashboard.services import update_queue

    monkeypatch.setattr(update_queue, "PAUSE", 0)
    tries = []

    def write():
        tries.append(1)
        if len(tries) < 3:
            raise OperationalError("database table is locked")
        return "written"

    assert update_queue.retrying(write) == "written" and len(tries) == 3
    with pytest.raises(OperationalError):
        update_queue.retrying(lambda: (_ for _ in ()).throw(OperationalError("locked")))


def test_a_job_that_fails_ends_as_failed(client, monkeypatch, project):
    def broken(job):
        raise RuntimeError("broken")

    monkeypatch.setattr(UpdateQueue, "run", staticmethod(broken))
    UpdateQueue.add(project)
    assert UpdateQueue.work() == 1
    assert UpdateJob.objects.get().status == UpdateJob.FAILED
    page = client.get(f"/projects/{project.slug}/").content.decode()
    assert 'data-status="failed"' in page and 'http-equiv="refresh"' not in page


def test_the_status_reads_the_update_after_the_job(project, repositories):
    """The update may end while the page is made: the status sees the job and its time."""
    project.repositories.add(Repository.objects.create(full_name="PyCalendar/plann"))
    shown = Project.objects.get(pk=project.pk)  # read before the update ends
    UpdateQueue.add(project)
    UpdateQueue.work()
    assert shown.updated is None
    assert ProjectStatus.of(shown, list(project.repositories.all())).up_to_date


def test_the_account_names_the_github_name(client, bob):
    client.force_login(bob)
    assert "GitHub handle: <strong>@bob</strong>" in client.get("/account/").content.decode()


@pytest.mark.django_db
def test_my_projects(client, bob, alice):
    from pycal_dashboard.services.project_editor import ProjectEditor

    ProjectEditor.create(bob, "Mine of Bob", slug="bobs")
    ProjectEditor.create(alice, "Of Alice", slug="alices")
    client.force_login(bob)
    menu = client.get("/").content.decode()
    assert 'href="/projects/?mine=1" data-my-projects>My projects<' in menu
    page = client.get("/projects/?mine=1").content.decode()
    assert 'data-project="bobs"' in page and 'data-project="alices"' not in page
    assert "<h1>My projects" in page
    every = client.get("/projects/").content.decode()
    assert 'data-project="bobs"' in every and 'data-project="alices"' in every
    client.logout()
    assert 'data-project="alices"' in client.get("/projects/?mine=1").content.decode()  # all


@pytest.mark.django_db
def test_a_refused_sign_in_asks_to_sign_in_again(client, github, bob, monkeypatch):
    """A token of the sign-in that GitHub refuses (401) is not an error of the GitHub App."""
    from pycal_dashboard.errors import GitHubLoginExpired
    from pycal_dashboard.github.client import GitHubClient

    def refused(self, method, path, **kwargs):
        raise GitHubLoginExpired(f"{method} {path}: 401 Bad credentials")

    monkeypatch.setattr(GitHubClient, "request", refused)
    from pycal_dashboard.errors import GitHubSignInExpired
    from pycal_dashboard.github.person_client import PersonClient

    with pytest.raises(GitHubSignInExpired):
        PersonClient("old-token", "bob").organizations()
