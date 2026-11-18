"""The log of the site: what triggered what, for the administrators."""

import pytest
from django.contrib.auth.signals import user_logged_in

from pycal_dashboard.actions import Action, Trigger
from pycal_dashboard.models import LogAction, LogTrigger
from tests.conftest import pull_payload, send_webhook

pytestmark = pytest.mark.django_db


def test_a_webhook_is_a_trigger(client):
    payload = {**pull_payload(), "sender": {"login": "dave"}}
    send_webhook(client, "pull_request", payload, delivery="d-42")
    trigger = LogTrigger.objects.get(kind="webhook")
    assert trigger.summary == "Pull request #6 opened: Pull request 6: received: no automation yet"
    assert (trigger.repository, trigger.actor_login, trigger.delivery) == (
        "PyCalendar/icalendar",
        "dave",
        "d-42",
    )


def test_a_failed_webhook_names_its_error(client, monkeypatch):
    from pycal_dashboard.services.webhook_handler import WebhookHandler

    monkeypatch.setattr(WebhookHandler, "handle", lambda self: 1 / 0)
    send_webhook(client, "pull_request", pull_payload())
    assert LogTrigger.objects.get(kind="webhook").summary.endswith(": UnexpectedError")


def test_signing_in_gives_the_rights_and_logs_them(admin):
    user_logged_in.send(sender=type(admin), request=None, user=admin)
    trigger = LogTrigger.objects.get(kind="sign-in")
    assert trigger.summary == "@admin signed in"
    (action,) = trigger.actions.all()
    assert action.kind == "admin-rights" and "@admin gets the rights" in action.text


def test_a_change_of_site_admins_is_logged(client, alice, settings):
    client.force_login(alice)
    settings.SITE_ADMINS = ["alice"]
    client.get("/")
    trigger = LogTrigger.objects.get(kind="site-admins")
    assert "@alice gets the rights" in trigger.actions.get().text
    client.get("/")
    assert LogTrigger.objects.filter(kind="site-admins").count() == 1  # nothing changed


def test_preferences_are_logged_without_the_address(client, alice):
    client.force_login(alice)
    client.post("/account/", {})
    action = LogAction.objects.get(kind="preferences")
    assert action.text == "@alice saved the preferences: no emails about the account and the site"


def test_the_oauth_app_is_logged_without_its_secret(client, admin, settings):
    from pycal_dashboard.sign_in import SignIn

    settings.SIGN_IN = SignIn()
    client.force_login(admin)
    secret = "0123456789abcdef0123456789abcdef01234567"
    client.post("/setup/oauth-app/", {"client_id": "Ov23liABCDEFGH", "secret": secret})
    action = LogAction.objects.get(kind="settings")
    assert "GITHUB_OAUTH_SECRET" in action.text and secret not in action.text
    assert action.trigger.summary == "OAuth app for signing in entered"


def test_an_action_outside_of_a_trigger_is_kept():
    class Note(Action):
        kind = "note"

        def text(self):
            return "a note"

    Note().run()
    assert LogAction.objects.get().trigger.kind == "background"
    with Trigger.start("test", "a test") as trigger:
        Note().run()
    assert trigger.actions.get().text == "a note"


def test_only_administrators_read_the_log(client, alice, admin):
    assert client.get("/logs/").status_code == 302
    client.force_login(alice)
    assert client.get("/logs/").status_code == 403
    client.force_login(admin)
    with Trigger.start("test", "Something happened"):
        pass
    page = client.get("/logs/").content.decode()
    assert "Something happened" in page and 'data-trigger="test"' in page
    assert 'href="/logs/"' in client.get("/").content.decode()


def test_the_log_has_pages(client, admin):
    client.force_login(admin)
    for number in range(55):
        LogTrigger.objects.create(kind="test", summary=f"entry {number}")
    assert "Older" in client.get("/logs/").content.decode()
    assert "Newer" in client.get("/logs/?page=2").content.decode()
