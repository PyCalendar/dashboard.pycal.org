"""The OAuth app that signs people in, entered on /setup/oauth-app/."""

import os

import pytest
from django.conf import settings

from pycal_dashboard import registered_settings
from pycal_dashboard.services.app_registration import AppRegistration
from pycal_dashboard.sign_in import SignIn
from tests.conftest import person

CLIENT_ID = "Ov23liABCDEFGH"
SECRET = "0123456789abcdef0123456789abcdef01234567"


@pytest.fixture
def no_oauth_app(settings, monkeypatch):
    settings.SIGN_IN = SignIn()
    settings.SOCIALACCOUNT_PROVIDERS = SignIn().providers()
    settings.DEBUG = False
    monkeypatch.setattr("os.environ", dict(os.environ))
    os.environ.pop("GITHUB_OAUTH_CLIENT_ID", None)
    os.environ.pop("GITHUB_OAUTH_SECRET", None)
    return settings


def test_sign_in_asks_for_the_oauth_app(no_oauth_app, client, db):
    content = client.get("/accounts/login/").content.decode()
    assert "data-no-sign-in" in content and "/setup/oauth-app/" in content
    assert b"data-oauth-missing" in client.get("/setup/oauth-app/").content


def test_enter_the_oauth_app(no_oauth_app, client, db):
    page = client.get("/setup/oauth-app/").content.decode()
    assert "https://dashboard.example.org/accounts/github/login/callback/" in page
    data = {"client_id": CLIENT_ID, "secret": SECRET, "setup_code": AppRegistration.setup_code()}
    response = client.post("/setup/oauth-app/", data)
    assert response.status_code == 302 and response["Location"] == "/accounts/login/"
    saved = registered_settings.read(AppRegistration.env_file())
    assert saved["GITHUB_OAUTH_CLIENT_ID"] == CLIENT_ID
    assert settings.SIGN_IN == SignIn(CLIENT_ID, SECRET)
    assert settings.SOCIALACCOUNT_PROVIDERS["github"]["APP"]["client_id"] == CLIENT_ID
    assert settings.SOCIALACCOUNT_PROVIDERS["github"]["SCOPE"] == ["user:email"]
    assert b"Sign in with GitHub</button>" in client.get("/accounts/login/").content


def test_wrong_setup_code(no_oauth_app, client, db):
    data = {"client_id": CLIENT_ID, "secret": SECRET, "setup_code": "nope"}
    response = client.post("/setup/oauth-app/", data)
    assert response.status_code == 403 and b'data-error="SetupCodeWrong"' in response.content
    assert not settings.SIGN_IN.configured


@pytest.mark.parametrize(("client_id", "secret"), [("x", SECRET), (CLIENT_ID, "short")])
def test_invalid_oauth_app(no_oauth_app, client, db, client_id, secret):
    data = {"client_id": client_id, "secret": secret, "setup_code": AppRegistration.setup_code()}
    response = client.post("/setup/oauth-app/", data)
    assert response.status_code == 400 and b'data-error="invalid"' in response.content


def test_only_admins_change_it(client, db):
    assert client.get("/setup/oauth-app/").status_code == 302  # sign in first
    client.force_login(person(42, "alice"))
    assert client.get("/setup/oauth-app/").status_code == 403
    admin = person(7, "admin")
    client.force_login(admin)
    page = client.get("/setup/oauth-app/").content
    assert b"data-oauth-configured" in page and b'name="setup_code"' not in page


def test_set_in_the_environment(no_oauth_app, client, db):
    os.environ["GITHUB_OAUTH_CLIENT_ID"] = CLIENT_ID
    response = client.post("/setup/oauth-app/", {"client_id": "other-client", "secret": SECRET})
    assert b"data-oauth-environment" in response.content
    assert not registered_settings.read(AppRegistration.env_file())


def test_sign_in_never_uses_the_client_of_the_github_app():
    environ = {"GITHUB_CLIENT_ID": "Iv1.app", "GITHUB_SECRET": "secret"}
    assert not SignIn.from_environment(environ).configured
    assert "APP" not in SignIn.from_environment(environ).providers()["github"]


def test_the_error_of_a_missing_oauth_app_leads_to_its_setup(no_oauth_app, client, db):
    response = client.post("/accounts/github/login/")
    page = response.content.decode()
    assert response.status_code == 503 and 'data-error="SignInNotConfigured"' in page
    assert (
        '<a class="button button-accent" href="/setup/oauth-app/" data-setup>Set up signing in</a>'
        in page
    )


def test_the_error_of_a_missing_github_app_leads_to_its_setup(rf, db):
    from django.contrib.auth.models import AnonymousUser

    from pycal_dashboard.errors import GitHubAppNotConfigured
    from pycal_dashboard.middleware import error_page

    request = rf.get("/")
    request.user = AnonymousUser()
    page = error_page(request, GitHubAppNotConfigured("GITHUB_APP_ID")).content.decode()
    assert 'href="/setup/github-app/" data-setup>Register the GitHub App</a>' in page


def test_other_errors_have_no_setup_button(client, db):
    assert b"data-setup" not in client.get("/setup/installed/").content
