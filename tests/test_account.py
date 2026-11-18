"""The private pages: the account, its email addresses and the webhook deliveries."""

import pytest
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model

from tests.conftest import person


def test_account_needs_sign_in(client, db):
    response = client.get("/account/")
    assert response.status_code == 302 and response["Location"].startswith("/accounts/login/")


def test_account_page(client, bob):
    EmailAddress.objects.create(user=bob, email="bob@example.org", verified=True, primary=True)
    client.force_login(bob)
    content = client.get("/account/").content.decode()
    assert "@bob" in content and "bob@example.org" in content
    assert "data-no-emails" in content and "email_notifications" not in content


def test_account_without_github(client, db):
    user = get_user_model().objects.create(username="local")
    client.force_login(user)
    response = client.get("/account/")
    assert response.status_code == 403 and b'data-error="NoGitHubAccount"' in response.content


def test_email_page(client, alice):
    client.force_login(alice)
    response = client.get("/accounts/email/")
    assert response.status_code == 200 and b"Email addresses" in response.content


def test_deliveries_for_admins_only(client, admin, alice):
    client.force_login(alice)
    assert client.get("/account/deliveries/").status_code == 403
    client.force_login(admin)
    assert client.get("/account/deliveries/").status_code == 200


def test_site_admins_get_the_django_admin(client, db):
    from django.contrib.auth.signals import user_logged_in

    admin = person(7, "Admin")
    other = person(8, "other", is_staff=True, is_superuser=True)
    for user in (admin, other):
        user_logged_in.send(sender=type(user), request=None, user=user)
        user.refresh_from_db()
    assert admin.is_staff and admin.is_superuser
    assert not other.is_staff and not other.is_superuser


def test_sign_in_page(client, db):
    content = client.get("/accounts/login/").content.decode()
    assert "Sign in with GitHub" in content and "/accounts/github/login/" in content


def test_every_model_is_in_the_django_admin():
    """The administrators see every table of the site in the Django admin."""
    from django.apps import apps
    from django.contrib import admin

    models = apps.get_app_config("pycal_dashboard").get_models()
    assert [m.__name__ for m in models if not admin.site.is_registered(m)] == []


@pytest.mark.parametrize("model", ["logtrigger", "logaction", "webhookdelivery"])
def test_site_admins_open_the_django_admin(client, db, model):
    from django.contrib.auth.signals import user_logged_in

    admin = person(7, "admin")
    user_logged_in.send(sender=type(admin), request=None, user=admin)
    client.force_login(admin)
    assert client.get("/admin/").status_code == 200
    assert client.get(f"/admin/pycal_dashboard/{model}/").status_code == 200
    assert "Django admin" in client.get("/").content.decode()


def test_others_do_not_open_the_django_admin(client, alice):
    client.force_login(alice)
    assert client.get("/admin/").status_code == 302
    assert "Django admin" not in client.get("/").content.decode()


def test_install_the_app_when_signed_in(client, alice):
    install = "https://github.com/apps/dashboard-test/installations/new"
    assert install not in client.get("/").content.decode()  # visitors see no button
    client.force_login(alice)
    account = client.get("/account/").content.decode()
    assert install in account and "https://docs.example.org/how-to/install-app.html" in account
    assert install in client.get("/").content.decode()


def test_no_install_button_without_an_app(client, alice, settings):
    settings.GITHUB_APP_ID = ""
    client.force_login(alice)
    content = client.get("/account/").content.decode()
    assert "installations/new" not in content and "/setup/github-app/" in content
