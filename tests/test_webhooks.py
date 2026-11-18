"""The webhook: signatures, events and the log of the deliveries."""

import pytest

from pycal_dashboard.models import Installation, Item, Repository, WebhookDelivery
from tests.conftest import OTHER, REPOSITORY, pull_payload, send_webhook


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


def test_unknown_event(client, db):
    response = send_webhook(client, "star", {"action": "created"})
    assert response.json()["done"] == "ignored: the event star"
    assert WebhookDelivery.objects.get().outcome == "ignored"


def test_installation_reads_everything(client, organization):
    payload = {"action": "created", "installation": {"id": 1, "account": {"login": "PyCalendar"}}}
    response = send_webhook(client, "installation", payload)
    assert "3 repositories" in response.json()["done"]
    assert Item.objects.filter(repository__full_name=REPOSITORY).count() == 5
    send_webhook(client, "installation", {**payload, "action": "deleted"})
    assert not Installation.objects.exists()


def test_other_organizations_are_ignored(client, organization):
    payload = {"action": "created", "installation": {"id": 1, "account": {"login": "Elsewhere"}}}
    assert send_webhook(client, "installation", payload).json()["done"].startswith("ignored")
    assert not Installation.objects.exists()


@pytest.mark.parametrize(
    "action", ["opened", "reopened", "synchronize", "edited", "ready_for_review"]
)
def test_pull_request_is_stored_but_not_labeled(client, synced, action):
    synced.pull(REPOSITORY, 6, "dave", additions=30, author_association="FIRST_TIME_CONTRIBUTOR")
    synced.requests.clear()
    response = send_webhook(client, "pull_request", pull_payload(synced, 6, action=action))
    assert response.json()["done"] == f"updated {REPOSITORY}#6"
    assert synced.writes() == []
    assert synced.find(REPOSITORY, 6)["labels"] == []
    assert Item.objects.get(repository__full_name=REPOSITORY, number=6).labels == []
    delivery = WebhookDelivery.objects.get()
    assert (delivery.event, delivery.action, delivery.repository) == (
        "pull_request",
        action,
        REPOSITORY,
    )


def test_pull_request_closed_is_stored_only(client, synced):
    pull = synced.find(REPOSITORY, 3)
    pull.update(state="closed", merged=True, merged_at="2026-11-18T10:00:00Z")
    response = send_webhook(client, "pull_request", pull_payload(synced, 3, action="closed"))
    assert response.json()["done"] == f"updated {REPOSITORY}#3"
    assert Item.objects.get(repository__full_name=REPOSITORY, number=3).status == "merged"


def test_issue_events(client, synced):
    repository = synced.repositories[REPOSITORY]
    issue = synced.issue(REPOSITORY, 9, "erin", title="New idea")
    payload = {
        "action": "opened",
        "issue": issue,
        "repository": repository,
        "installation": {"id": 1},
    }
    send_webhook(client, "issues", payload)
    assert Item.objects.get(number=9, repository__full_name=REPOSITORY).title == "New idea"
    issue["comments"] = 1
    send_webhook(client, "issue_comment", {**payload, "action": "created"})
    assert Item.objects.get(number=9, repository__full_name=REPOSITORY).comments == 1
    send_webhook(client, "issues", {**payload, "action": "deleted"})
    assert not Item.objects.filter(number=9, repository__full_name=REPOSITORY).exists()


def test_review_updates_reviewers(client, synced):
    pull = synced.find(REPOSITORY, 4)
    pull["requested_reviewers"] = []
    payload = pull_payload(synced, 4, action="submitted")
    send_webhook(client, "pull_request_review", payload)
    assert Item.objects.get(repository__full_name=REPOSITORY, number=4).requested_reviewers == []


def test_repository_events(client, synced):
    data = dict(synced.repositories[OTHER], full_name="PyCalendar/plann2", archived=True)
    send_webhook(
        client, "repository", {"action": "renamed", "repository": data, "installation": {"id": 1}}
    )
    assert Repository.objects.get(github_id=data["id"]).full_name == "PyCalendar/plann2"
    send_webhook(
        client, "repository", {"action": "deleted", "repository": data, "installation": {"id": 1}}
    )
    assert not Repository.objects.filter(github_id=data["id"]).exists()


def test_incomplete_payload(client, synced):
    response = send_webhook(
        client, "issues", {"action": "opened", "repository": synced.repositories[REPOSITORY]}
    )
    assert response.status_code == 200
    assert response.json()["error"] == "WebhookPayloadIncomplete"
    assert WebhookDelivery.objects.get().outcome == "failed"


def test_pull_request_while_github_is_down(client, synced):
    """The webhook brings everything: the site does not ask GitHub back."""
    synced.pull(REPOSITORY, 6, "dave")
    payload = pull_payload(synced, 6)
    synced.unreachable = True
    response = send_webhook(client, "pull_request", payload)
    assert response.status_code == 200
    assert response.json()["done"] == f"updated {REPOSITORY}#6"
