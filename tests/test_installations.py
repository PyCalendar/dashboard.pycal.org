"""The installations of the GitHub App: their permissions are recorded, and people are told."""

import pytest
from allauth.account.models import EmailAddress
from django.core import mail
from django.core.management import CommandError, call_command

from pycal_dashboard.github.permissions import REQUIRED
from pycal_dashboard.models import Installation, LogAction, Preferences
from tests.conftest import person, send_webhook

pytestmark = pytest.mark.django_db

ORGANIZATION = {"login": "PyCalendar", "id": 900, "type": "Organization"}


def installation(permissions=None, **extra) -> dict:
    return {
        "id": 5,
        "account": ORGANIZATION,
        "permissions": dict(REQUIRED) if permissions is None else permissions,
        "events": ["issues", "pull_request"],
        **extra,
    }


def webhook(client, action, data, sender_id=42, event="installation"):
    payload = {
        "action": action,
        "installation": data,
        "sender": {"login": "alice", "id": sender_id, "type": "User"},
    }
    return send_webhook(client, event, payload).json()


@pytest.fixture
def alice_with_email(alice):
    EmailAddress.objects.create(user=alice, email="alice@example.org", primary=True, verified=True)
    return alice


def test_an_installation_is_recorded(client, alice_with_email):
    done = webhook(client, "created", installation())
    assert done == {"done": "recorded the installation on PyCalendar"}
    recorded = Installation.objects.get()
    assert recorded.permissions == REQUIRED and recorded.events == ["issues", "pull_request"]
    assert recorded.admin_github_ids == [42] and recorded.account_type == "Organization"
    assert not mail.outbox


def test_missing_permissions_are_told_once(client, alice_with_email):
    done = webhook(client, "created", installation({"metadata": "read"}))
    assert done["done"] == (
        "recorded the installation on PyCalendar; it lacks checks:read, contents:read, "
        "issues:read, pull_requests:write, statuses:read; 1 email"
    )
    (message,) = mail.outbox
    assert message.to == ["alice@example.org"]
    assert (
        message.subject
        == "[dashboard.pycal.org] The GitHub App on PyCalendar needs more permissions"
    )
    assert "- issues: read" in message.body
    assert "https://github.com/organizations/PyCalendar/settings/installations/5" in message.body
    webhook(client, "new_permissions_accepted", installation({"metadata": "read"}))
    assert len(mail.outbox) == 1  # told already
    assert LogAction.objects.filter(kind="email").get().text.startswith("Email to 1 addresses")


def test_accepted_permissions_reset_the_notice(client, alice_with_email):
    webhook(client, "created", installation({"metadata": "read"}))
    webhook(client, "new_permissions_accepted", installation())
    assert Installation.objects.get().permissions_notified == ""
    webhook(client, "new_permissions_accepted", installation({"metadata": "read"}))
    assert len(mail.outbox) == 2  # a new lack is told again


def test_the_email_speaks_the_language_of_the_person(client, alice_with_email):
    Preferences.objects.create(user=alice_with_email, language="de")
    webhook(client, "created", installation({"metadata": "read"}))
    assert "braucht mehr Berechtigungen" in mail.outbox[0].subject


def test_people_switch_the_emails_off(client, alice_with_email):
    Preferences.objects.create(user=alice_with_email, email_permissions=False)
    webhook(client, "created", installation({"metadata": "read"}))
    assert not mail.outbox


def test_only_verified_addresses_get_emails(client, alice):
    EmailAddress.objects.create(user=alice, email="new@example.org", primary=True)
    EmailAddress.objects.create(user=alice, email="old@example.org", verified=True)
    webhook(client, "created", installation({"metadata": "read"}))
    assert mail.outbox[0].to == ["old@example.org"]


def test_people_without_an_account_get_no_email(client, db):
    webhook(client, "created", installation({"metadata": "read"}), sender_id=77)
    assert not mail.outbox and Installation.objects.get().admin_github_ids == [77]


def test_removed_and_suspended(client, alice_with_email):
    webhook(client, "created", installation())
    webhook(client, "suspend", installation(suspended_at="2026-11-18T10:00:00Z"))
    assert Installation.objects.get().suspended
    assert webhook(client, "deleted", installation())["done"].endswith(": removed")
    assert Installation.objects.get().removed


def test_the_repositories_of_an_installation_changed(client, alice_with_email):
    done = webhook(client, "added", installation(), event="installation_repositories")
    assert done["done"].startswith("recorded the installation")


def test_the_account_page_shows_the_installations(client, alice_with_email):
    webhook(client, "created", installation({"metadata": "read"}))
    client.force_login(alice_with_email)
    page = client.get("/account/?tab=app").content.decode()
    assert (
        'data-installation="5"' in page
        and '<span class="permission-name">Issues</span>: Read-only' in page
    )
    assert 'href="https://github.com/organizations/PyCalendar/settings/installations/5"' in page
    other = person(43, "bob")
    client.force_login(other)
    assert 'data-installation="5"' not in client.get("/account/?tab=app").content.decode()


def test_the_email_switch_is_saved(client, alice):
    client.force_login(alice)
    client.post("/account/", {"language": "", "theme": ""})
    assert not Preferences.objects.get(user=alice).email_permissions
    client.post("/account/", {"email_permissions": "yes"})
    assert Preferences.objects.get(user=alice).email_permissions


def test_every_start_checks_the_installations(github, alice_with_email, capsys):
    github.installations = [installation({"metadata": "read"}), installation(id=6)]
    Installation.objects.create(github_id=99, account_login="gone")
    call_command("check_installations")
    assert capsys.readouterr().out.strip() == "2 installations, 1 lack permissions, 0 emails sent"
    assert Installation.objects.get(github_id=99).removed
    assert Installation.objects.get(github_id=5).missing_permissions


def test_the_check_names_its_error(github, db):
    github.unreachable = True
    with pytest.raises(CommandError, match="GitHub could not be reached"):
        call_command("check_installations")
