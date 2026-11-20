"""The background work: webhooks recorded by the web process, handled by the worker process."""

from datetime import timedelta
from io import StringIO

import pytest
from django.core.cache import cache
from django.core.management import call_command
from django.utils import timezone

from pycal_dashboard import errors, worker_mode
from pycal_dashboard.checks import check_worker_mode
from pycal_dashboard.models import Repository, UpdateJob, WebhookDelivery
from pycal_dashboard.services.project_editor import ProjectEditor
from pycal_dashboard.services.update_worker import UpdateWorker
from pycal_dashboard.services.webhook_queue import WebhookQueue
from tests.conftest import REPOSITORY, repository_payload, send_webhook

pytestmark = pytest.mark.django_db


@pytest.fixture
def external(settings):
    settings.FETCH_WORKER = worker_mode.HTTP_CONTAINER


@pytest.fixture
def project(github, bob):
    github.add_repository(REPOSITORY, issues=1, installation=11)
    project = ProjectEditor.create(bob, "iCalendar")
    project.repositories.add(Repository.objects.create(full_name=REPOSITORY, github_id=1000))
    return project


def push(client):
    return send_webhook(client, "issues", {"action": "opened", "repository": repository_payload()})


def test_a_webhook_is_recorded_and_answered_at_once(client, project, external):
    answer = push(client)
    assert answer.status_code == 202
    delivery = WebhookDelivery.objects.get()
    assert answer.json() == {"queued": delivery.pk}
    assert (delivery.outcome, delivery.action, delivery.repository) == (
        "queued",
        "opened",
        REPOSITORY,
    )
    assert '"opened"' in delivery.payload
    assert not UpdateJob.objects.exists()  # nothing done in the request


def test_the_worker_handles_the_webhooks_and_the_updates(client, project, external):
    push(client)
    out = StringIO()
    call_command("fetch_worker", "--once", stdout=out)
    delivery = WebhookDelivery.objects.get()
    assert delivery.outcome == "done" and delivery.payload == "" and delivery.handled
    assert delivery.detail == f"queued an update of {REPOSITORY}"
    assert UpdateJob.objects.get().status == UpdateJob.DONE  # and the update ran
    assert "fetch worker: external-http-container" in out.getvalue()


def test_a_stopped_handling_is_taken_again(project, external):
    delivery = WebhookDelivery.objects.create(
        event="ping", outcome="handling", payload="{}", handled=timezone.now() - timedelta(hours=1)
    )
    assert WebhookQueue.work() == 1
    delivery.refresh_from_db()
    assert (delivery.outcome, delivery.detail) == ("done", "pong")
    WebhookDelivery.objects.create(event="ping", outcome="handling", handled=timezone.now())
    assert WebhookQueue.work() == 0  # handled now by another process


def test_a_broken_payload_fails_without_stopping_the_queue(external):
    WebhookDelivery.objects.create(event="issues", outcome="queued", payload="not json")
    WebhookDelivery.objects.create(event="ping", outcome="queued", payload="{}")
    assert WebhookQueue.work() == 2
    assert sorted(WebhookDelivery.objects.values_list("outcome", flat=True)) == ["done", "done"]


def test_no_thread_of_gunicorn_in_the_external_modes(external, monkeypatch):
    monkeypatch.setattr(UpdateWorker, "enabled", True)
    assert UpdateWorker.start() is False


def test_check_again_asks_the_worker(external, monkeypatch):
    from pycal_dashboard.services.app_notice import AppNotice

    checked = []
    monkeypatch.setattr(AppNotice, "refresh", classmethod(lambda cls: checked.append(1)))
    assert AppNotice.refresh_in_background() is None
    assert cache.get("app-check-requested")
    call_command("fetch_worker", "--once", stdout=StringIO())
    assert checked == [1] and not cache.get("app-check-requested")


def test_inline_handles_the_webhook_in_the_request(client, project):
    answer = push(client)
    assert answer.status_code == 200 and answer.json()["done"].startswith("queued an update")
    assert WebhookDelivery.objects.get().outcome == "done"


def test_an_unknown_mode(settings):
    settings.FETCH_WORKER = "somewhere"
    with pytest.raises(errors.UnknownWorkerMode):
        worker_mode.mode()
    (error,) = check_worker_mode()
    assert error.id == "pycal_dashboard.E003" and "somewhere" in error.hint
    settings.FETCH_WORKER = "internal"
    assert check_worker_mode() == []


def test_the_image_runs_the_worker_as_a_process_of_its_own():
    from pathlib import Path

    root = Path(__file__).parent.parent
    assert "ENV FETCH_WORKER=external-http-container" in (root / "Dockerfile").read_text()
    script = (root / "docker" / "start-service.sh").read_text()
    assert "(while true; do python manage.py fetch_worker || true; sleep 5; done) &" in script


def test_the_worker_runs_without_a_github_app(settings, external):
    """The check of the installations fails without an app: the worker does not stop."""
    settings.GITHUB_APP_ID = ""
    out = StringIO()
    call_command("fetch_worker", "--once", stdout=out)
    assert "no check of the installations:" in out.getvalue()
    assert "fetch worker: nothing waits" in out.getvalue()


def test_no_app_is_no_warning(settings, caplog):
    """A site whose GitHub App is not registered yet has nothing to check: no traceback."""
    from pycal_dashboard.services.app_notice import AppNotice

    settings.GITHUB_APP_ID = ""
    with caplog.at_level("WARNING"):
        assert AppNotice.refresh() is None
    assert "could not be checked" not in caplog.text
