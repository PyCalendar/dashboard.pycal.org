"""People add email addresses, verify them with a link and choose the primary one."""

import re

import pytest
from allauth.account.models import EmailAddress
from django.core import mail

pytestmark = pytest.mark.django_db
TAB = "/account/?tab=emails"  # what /accounts/email/ did, on the account


def link_of(message) -> str:
    """The path of the link in an email."""
    url = re.search(r"https?://\S+/accounts/confirm-email/\S+/", message.body).group(0)
    return "/" + url.split("/", 3)[3]


def add(client, address: str):
    return client.post("/accounts/email/", {"action_add": "", "email": address})


def test_add_an_address_and_verify_it(client, alice, settings):
    settings.SITE_NAME = "dashboard.example.org"
    client.force_login(alice)
    assert add(client, "alice@example.org").status_code == 302
    (message,) = mail.outbox
    assert message.to == ["alice@example.org"]
    assert message.subject == "[dashboard.pycal.org] Verify your email address"
    assert "@alice on dashboard.example.org" in message.body and "example.com" not in message.body
    page = client.get(link_of(message)).content.decode()
    assert "<strong>alice@example.org</strong>" in page and ">Verify</button>" in page
    assert not EmailAddress.objects.get(email="alice@example.org").verified  # GET changes nothing
    response = client.post(link_of(message))
    assert response.status_code == 302 and response["Location"] == "/account/"
    assert EmailAddress.objects.get(email="alice@example.org").verified


def test_the_link_works_without_signing_in(client, alice):
    client.force_login(alice)
    add(client, "alice@example.org")
    client.logout()
    client.post(link_of(mail.outbox[0]))
    assert EmailAddress.objects.get(email="alice@example.org").verified


def test_an_invalid_link(client):
    page = client.get("/accounts/confirm-email/nonsense/").content.decode()
    assert "data-confirm-invalid" in page and 'href="/accounts/email/"' in page


def test_send_the_link_again_from_the_account(client, alice):
    EmailAddress.objects.create(user=alice, email="alice@example.org", primary=True)
    client.force_login(alice)
    account = client.get("/account/").content.decode()  # the first tab
    assert 'name="action_send"' in account
    answer = client.post("/accounts/email/", {"action_send": "", "email": "alice@example.org"})
    assert answer["Location"] == TAB  # back to the tab
    assert len(mail.outbox) == 1 and mail.outbox[0].to == ["alice@example.org"]


def test_add_another_address_and_make_it_primary(client, alice):
    EmailAddress.objects.create(user=alice, email="old@example.org", primary=True, verified=True)
    client.force_login(alice)
    add(client, "new@example.org")
    page = client.get(TAB).content.decode()
    new = page.split('data-address="new@example.org"')[1].split("</li>")[0]
    assert "action_send" in new and "action_primary" not in new  # verify it first
    client.post(link_of(mail.outbox[0]))
    page = client.get(TAB).content.decode()
    assert "action_primary" in page.split('data-address="new@example.org"')[1].split("</li>")[0]
    client.post("/accounts/email/", {"action_primary": "", "email": "new@example.org"})
    assert EmailAddress.objects.get(primary=True).email == "new@example.org"
    old = client.get(TAB).content.decode().split('data-address="old@example.org"')[1]
    assert "action_remove" in old.split("</li>")[0]


def test_an_unverified_address_does_not_become_primary(client, alice):
    EmailAddress.objects.create(user=alice, email="old@example.org", primary=True, verified=True)
    EmailAddress.objects.create(user=alice, email="new@example.org")
    client.force_login(alice)
    client.post("/accounts/email/", {"action_primary": "", "email": "new@example.org"})
    assert EmailAddress.objects.get(primary=True).email == "old@example.org"


def test_remove_an_address_but_not_the_primary(client, alice):
    EmailAddress.objects.create(user=alice, email="old@example.org", primary=True, verified=True)
    EmailAddress.objects.create(user=alice, email="new@example.org")
    client.force_login(alice)
    primary = client.get(TAB).content.decode().split('data-address="old@example.org"')[1]
    assert "action_remove" not in primary.split("</li>")[0]
    client.post("/accounts/email/", {"action_remove": "", "email": "new@example.org"})
    assert list(EmailAddress.objects.values_list("email", flat=True)) == ["old@example.org"]


def test_an_invalid_address_is_explained(client, alice):
    client.force_login(alice)
    answer = add(client, "not an address")
    page = answer.content.decode()
    assert answer.status_code == 200 and "data-email-error" in page and not mail.outbox
    assert 'aria-current="page" data-account-tab="emails"' in page  # on the tab
    assert 'value="not an address"' in page  # what was typed stays


def test_the_email_speaks_the_language_of_the_page(client, alice):
    client.force_login(alice)
    client.post(
        "/accounts/email/",
        {"action_add": "", "email": "alice@example.org"},
        HTTP_ACCEPT_LANGUAGE="de",
    )
    assert "Bestätige deine E-Mail-Adresse" in mail.outbox[0].subject


def test_every_function_of_the_email_page_is_on_the_tab(client, alice):
    """/accounts/email/ leads to the tab, which adds, verifies, makes primary and removes."""
    EmailAddress.objects.create(user=alice, email="old@example.org", primary=True, verified=True)
    EmailAddress.objects.create(user=alice, email="new@example.org", verified=True)
    EmailAddress.objects.create(user=alice, email="unverified@example.org")
    client.force_login(alice)
    answer = client.get("/accounts/email/")
    assert answer.status_code == 302 and answer["Location"] == TAB
    page = client.get(TAB).content.decode()
    for action in ("action_add", "action_send", "action_primary", "action_remove"):
        assert f'name="{action}"' in page, action
    assert "data-add-email" in page
    assert add(client, "third@example.org")["Location"] == TAB
