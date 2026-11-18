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
    ("installation", {"action": "created"}),
    ("installation_repositories", {"action": "added"}),
    ("issues", {"action": "opened", "issue": {"number": 9}}),
    ("issue_comment", {"action": "created", "issue": {"number": 9}}),
    ("pull_request_review", {"action": "submitted", "pull_request": {"number": 6}}),
    ("repository", {"action": "renamed"}),
    ("star", {"action": "created"}),
]


@pytest.mark.parametrize(("event", "payload"), EVENTS)
def test_events_are_logged_only(client, github, db, event, payload):
    """The site keeps no data of GitHub and asks GitHub nothing back."""
    payload = {
        **payload,
        "repository": repository_payload(),
        "installation": {"id": 1, "account": {"login": "PyCalendar"}},
    }
    response = send_webhook(client, event, payload)
    assert response.json() == {"done": "received: no automation yet"}
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
    assert response.json()["done"] == "received: no automation yet"
    assert github.writes() == [] and github.requests == []


def test_other_accounts_may_install_the_app(client, db):
    payload = pull_payload(account="Elsewhere")
    payload["repository"] = repository_payload("Elsewhere/x")
    assert (
        send_webhook(client, "pull_request", payload).json()["done"]
        == "received: no automation yet"
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
