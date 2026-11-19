"""The webhook: signatures, events and the log of the deliveries."""

import pytest

from pycal_dashboard.models import WebhookDelivery
from tests.conftest import REPOSITORY, pull_payload, repository_payload, send_webhook


@pytest.mark.parametrize(
    ("secret", "event", "body", "status", "error"),
    [
        (None, "ping", {}, 401, "WebhookSignatureMissing"),
        ("wrong", "ping", {}, 401, "WebhookSignatureInvalid"),
        ("webhook-secret", "", {}, 400, "WebhookEventMissing"),
        ("webhook-secret", "ping", [], 400, "WebhookPayloadInvalid"),
    ],
)
def test_refused(client, db, secret, event, body, status, error):
    response = send_webhook(client, event, body, secret=secret)
    assert response.status_code == status
    assert response.json()["error"] == error
    assert response.json()["documentation"].endswith(error)
    assert WebhookDelivery.objects.get().outcome == "refused"


def test_no_secret(client, db, settings):
    settings.GITHUB_WEBHOOK_SECRET = ""
    response = send_webhook(client, "ping", {})
    assert response.status_code == 503
    assert response.json()["error"] == "WebhookSecretNotConfigured"


def test_not_json(client, db):
    from pycal_dashboard.github.webhook_signature import sign

    body = b"not json"
    response = client.post(
        "/github/webhook/",
        body,
        content_type="application/json",
        HTTP_X_GITHUB_EVENT="ping",
        HTTP_X_HUB_SIGNATURE_256=sign("webhook-secret", body),
    )
    assert response.json()["error"] == "WebhookPayloadInvalid"


def test_ping(client, db):
    assert send_webhook(client, "ping", {"zen": "Keep it simple."}).json() == {"done": "pong"}


EVENTS = [
    ("issues", {"action": "opened", "issue": {"number": 9}}),
    ("issue_comment", {"action": "created", "issue": {"number": 9}}),
    ("pull_request_review", {"action": "submitted", "pull_request": {"number": 6}}),
    ("repository", {"action": "renamed"}),
    ("star", {"action": "created"}),
]


@pytest.mark.parametrize(("event", "payload"), EVENTS)
def test_events_of_repositories_outside_projects_are_logged_only(
    client, github, db, event, payload
):
    """A repository in no project: the site asks GitHub nothing."""
    payload = {
        **payload,
        "repository": repository_payload(),
        "installation": {"id": 1, "account": {"login": "PyCalendar"}},
    }
    response = send_webhook(client, event, payload)
    assert response.json() == {"done": "received: no repository of a project"}
    assert github.requests == []
    delivery = WebhookDelivery.objects.get()
    assert (delivery.event, delivery.action, delivery.repository, delivery.outcome) == (
        event,
        payload["action"],
        REPOSITORY,
        "done",
    )


@pytest.mark.parametrize(
    "action", ["opened", "reopened", "synchronize", "edited", "ready_for_review", "closed"]
)
def test_pull_requests_are_not_labeled(client, github, db, action):
    response = send_webhook(client, "pull_request", pull_payload(action=action))
    assert response.json()["done"] == "received: no repository of a project"
    assert github.writes() == [] and github.requests == []


def test_other_accounts_may_install_the_app(client, db):
    payload = pull_payload(account="Elsewhere")
    payload["repository"] = repository_payload("Elsewhere/x")
    assert (
        send_webhook(client, "pull_request", payload).json()["done"]
        == "received: no repository of a project"
    )
    delivery = WebhookDelivery.objects.get()
    assert (delivery.repository, delivery.outcome) == ("Elsewhere/x", "done")


def test_webhooks_while_github_is_down(client, github, db):
    """The webhook brings everything: the site does not ask GitHub back."""
    github.unreachable = True
    response = send_webhook(client, "pull_request", pull_payload())
    assert response.status_code == 200


def test_failure_is_logged(client, db, monkeypatch):
    from pycal_dashboard.services.webhook_handler import WebhookHandler

    def broken(self):
        raise RuntimeError("broken")

    monkeypatch.setattr(WebhookHandler, "handle", broken)
    response = send_webhook(client, "pull_request", pull_payload())
    assert response.status_code == 500
    assert response.json()["error"] == "UnexpectedError"
    assert WebhookDelivery.objects.get().outcome == "failed"


@pytest.mark.parametrize("event", ["pull_request", "issues", "issue_comment", "repository"])
def test_activity_updates_the_repository_of_a_project(client, github, bob, event):
    """Activity on GitHub updates its repository in the background: only what changed."""
    from pycal_dashboard.models import Issue, Repository, UpdateJob
    from pycal_dashboard.services.project_editor import ProjectEditor
    from pycal_dashboard.services.repository_update import RepositoryUpdate
    from pycal_dashboard.services.update_queue import UpdateQueue

    github.add_repository(REPOSITORY, issues=1)
    repository = Repository.objects.create(full_name=REPOSITORY)
    ProjectEditor.create(bob, "iCalendar").repositories.add(repository)
    RepositoryUpdate(repository).run()
    UpdateJob.objects.all().delete()
    github.add_issue(REPOSITORY, "Opened just now", updated="2026-11-19T10:00:00Z")
    payload = {"action": "opened", "repository": repository_payload(REPOSITORY.lower())}
    assert send_webhook(client, event, payload).json()["done"] == (
        f"queued an update of {REPOSITORY}"
    )
    send_webhook(client, event, payload)  # a second one joins the waiting update
    job = UpdateJob.objects.get()
    assert (job.repository, job.project) == (repository, None)
    assert UpdateQueue.work() == 1
    assert Issue.objects.filter(title="Opened just now").exists()
    assert github.issue_requests[-1]["since"]  # only what changed
    assert github.writes() == []


def test_a_renamed_repository_is_found_by_its_id(client, github, bob):
    from pycal_dashboard.models import Repository, UpdateJob
    from pycal_dashboard.services.project_editor import ProjectEditor

    repository = Repository.objects.create(full_name="PyCalendar/old-name", github_id=1000)
    ProjectEditor.create(bob, "iCalendar").repositories.add(repository)
    send_webhook(client, "repository", {"action": "renamed", "repository": repository_payload()})
    assert UpdateJob.objects.get().repository == repository


def test_a_repository_update_does_not_mark_projects_updated(github, bob):
    from pycal_dashboard.models import Repository
    from pycal_dashboard.services.project_editor import ProjectEditor
    from pycal_dashboard.services.update_queue import UpdateQueue

    github.add_repository(REPOSITORY)
    repository = Repository.objects.create(full_name=REPOSITORY)
    project = ProjectEditor.create(bob, "iCalendar")
    project.repositories.add(repository)
    UpdateQueue.add_repository(repository)
    UpdateQueue.work()
    project.refresh_from_db()
    repository.refresh_from_db()
    assert project.updated is None and repository.updated is not None
