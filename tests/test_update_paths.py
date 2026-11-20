"""Every update takes the same path: a trigger queues it, the worker runs it, a signal follows."""

from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from pycal_dashboard.models import Project, Repository, UpdateJob
from pycal_dashboard.services.project_editor import ProjectEditor
from pycal_dashboard.services.repository_update import RepositoryUpdate
from pycal_dashboard.services.update_queue import UpdateQueue
from pycal_dashboard.update_signals import project_updated, repository_updated
from tests.conftest import REPOSITORY, repository_payload, send_webhook

pytestmark = pytest.mark.django_db


@pytest.fixture
def project(github, bob):
    github.add_repository(REPOSITORY, issues=1)
    project = ProjectEditor.create(bob, "iCalendar")
    project.repositories.add(Repository.objects.create(full_name=REPOSITORY))
    return project


@pytest.fixture
def signals():
    """The signals sent: (name, repository or project)."""
    sent = []

    def on_repository(sender, repository, **kwargs):
        sent.append(("repository", repository.full_name))

    def on_project(sender, project, **kwargs):
        sent.append(("project", project.name))

    repository_updated.connect(on_repository)
    project_updated.connect(on_project)
    yield sent
    repository_updated.disconnect(on_repository)
    project_updated.disconnect(on_project)


def make_stale(project):
    long_ago = timezone.now() - timedelta(days=2)
    Repository.objects.update(updated=long_ago)
    Project.objects.update(updated=long_ago)
    UpdateJob.objects.all().delete()


def trigger_button(client, project, bob):
    client.force_login(bob)
    client.post(project.path("update/"))


def trigger_webhook(client, project, bob):
    send_webhook(client, "issues", {"action": "opened", "repository": repository_payload()})


def trigger_routine(client, project, bob):
    call_command("update_projects", "--stale", stdout=StringIO())


def trigger_view(client, project, bob):
    client.get(project.path())  # a visitor sees that it may be out of date


@pytest.mark.parametrize(
    "trigger", [trigger_button, trigger_webhook, trigger_routine, trigger_view]
)
def test_every_trigger_takes_the_same_path(client, project, bob, signals, monkeypatch, trigger):
    """The button, a webhook, the hourly routine and a view: a job, the update, the signals."""
    RepositoryUpdate(project.repositories.get()).run()
    make_stale(project)
    signals.clear()
    runs = []
    original = RepositoryUpdate.run
    monkeypatch.setattr(RepositoryUpdate, "run", lambda self: runs.append(1) or original(self))
    trigger(client, project, bob)
    UpdateQueue.work()  # the worker, in the background
    assert runs == [1]
    assert sorted(signals) == [("project", "iCalendar"), ("repository", REPOSITORY)]
    project.refresh_from_db()
    assert project.updated > timezone.now() - timedelta(minutes=1)


def test_the_routine_renews_only_what_may_be_out_of_date(project, github):
    out = StringIO()
    call_command("update_projects", "--stale", stdout=out)
    assert "1 repositories may be out of date" in out.getvalue()  # never read
    assert "1 updates done" in out.getvalue()
    out = StringIO()
    call_command("update_projects", "--stale", stdout=out)
    assert "0 repositories may be out of date" in out.getvalue()  # read just now


def test_a_failing_repository_is_not_asked_at_every_view(client, project, github, bob):
    github.repositories.clear()  # GitHub does not find it
    client.get(project.path())
    UpdateQueue.work()
    assert Repository.objects.get().error_code == "GitHubNotFound"
    client.get(project.path())
    client.get(project.path())
    assert UpdateJob.objects.count() == 1  # only once in an hour (RETRY)


def test_repositories_outside_projects_are_not_renewed(github):
    Repository.objects.create(full_name="alone/one")
    assert UpdateQueue.stale() == 0


def test_a_project_is_as_fresh_as_its_oldest_repository(project, github, bob):
    github.add_repository("PyCalendar/plann")
    plann = Repository.objects.create(full_name="PyCalendar/plann")
    project.repositories.add(plann)
    RepositoryUpdate(project.repositories.get(full_name=REPOSITORY)).run()
    project.refresh_from_db()
    assert project.updated is None  # plann was never read
    RepositoryUpdate(plann).run()
    project.refresh_from_db()
    assert project.updated == Repository.objects.get(full_name=REPOSITORY).updated


def test_a_slow_receiver_says_so_in_the_log(caplog, monkeypatch):
    """The work after an update names what took long, such as on a small server."""
    from pycal_dashboard import receivers

    ticks = iter([0.0, 2.5])
    monkeypatch.setattr(receivers.time, "perf_counter", lambda: next(ticks))

    def prepare(sender, repository):
        """A receiver."""

    slow = receivers.timed(prepare)
    with caplog.at_level("INFO", logger="pycal_dashboard.receivers"):
        slow(sender=None, repository="collective/icalendar")
    assert "prepare for collective/icalendar took 2.5 s" in caplog.text
