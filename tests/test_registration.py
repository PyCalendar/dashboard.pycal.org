"""Registering the GitHub App on the site, and what the start of the site says."""

import re

import pytest
from django.core.management import call_command

from pycal_dashboard import registered_settings
from pycal_dashboard.github.permissions import manifest
from pycal_dashboard.services.app_registration import AppRegistration
from pycal_dashboard.sign_in import SignIn


@pytest.fixture
def no_app(settings, monkeypatch):
    settings.GITHUB_APP_ID = ""
    settings.GITHUB_APP_SLUG = ""
    settings.DEBUG = False
    settings.SIGN_IN = SignIn()
    settings.SOCIALACCOUNT_PROVIDERS = SignIn().providers()
    for name in (
        "GITHUB_APP_ID",
        "GITHUB_APP_SLUG",
        "GITHUB_CLIENT_ID",
        "GITHUB_SECRET",
        "GITHUB_WEBHOOK_SECRET",
        "GITHUB_APP_PRIVATE_KEY",
        "GITHUB_APP_PRIVATE_KEY_FILE",
        "GITHUB_OAUTH_CLIENT_ID",
    ):
        monkeypatch.delenv(name, raising=False)
    return settings


def test_start_prints_the_setup_code(no_app, db, capsys):
    call_command("prepare")
    output = capsys.readouterr().out
    code = AppRegistration.setup_code()
    assert f"/setup/github-app/ with the setup code {code}" in output
    assert f"/setup/oauth-app/ with the setup code {code}" in output


def test_start_with_an_app(db, capsys):
    call_command("prepare")
    output = capsys.readouterr().out
    assert "GitHub App dashboard-test" in output
    assert "People sign in with the OAuth app." in output


def test_every_page_asks_for_the_app(no_app, client, db):
    assert b"data-no-app" in client.get("/").content
    assert b"data-no-sign-in" in client.get("/accounts/login/").content


def test_wrong_setup_code(no_app, client, db):
    response = client.post("/setup/github-app/", {"name": "dash", "setup_code": "nope"})
    assert response.status_code == 403
    assert b'data-error="SetupCodeWrong"' in response.content


@pytest.mark.parametrize(
    ("data", "error"),
    [
        ({"name": ""}, "InvalidAppName"),
        ({"name": "x" * 35}, "InvalidAppName"),
        ({"name": "dash", "organization": "-bad-"}, "InvalidOrganization"),
    ],
)
def test_invalid_form(no_app, client, db, data, error):
    response = client.post(
        "/setup/github-app/", {**data, "setup_code": AppRegistration.setup_code()}
    )
    assert f'data-error="{error}"'.encode() in response.content


def test_register(no_app, client, github, db, monkeypatch, private_key):
    page = client.post(
        "/setup/github-app/",
        {
            "name": "dashboard",
            "organization": "PyCalendar",
            "setup_code": AppRegistration.setup_code(),
        },
    )
    content = page.content.decode()
    assert 'action="https://github.com/organizations/PyCalendar/settings/apps/new?state=' in content
    assert "/github/webhook/" in content and "pull_requests" in content
    state = re.search(r"state=([\w-]+)", content).group(1)
    github.manifest_codes["c0de"] = {
        "id": 77,
        "slug": "dashboard",
        "name": "dashboard",
        "client_id": "Iv1.abc",
        "client_secret": "s3cret",
        "webhook_secret": "hook",
        "pem": private_key,
        "html_url": "https://github.com/apps/dashboard",
        "owner": {"login": "PyCalendar"},
    }
    monkeypatch.setattr("os.environ", dict(__import__("os").environ))
    done = client.get(f"/setup/github-app/registered/?code=c0de&state={state}")
    assert done.status_code == 200
    assert b'data-registered-app="dashboard"' in done.content
    saved = registered_settings.read(AppRegistration.env_file())
    assert saved["GITHUB_APP_ID"] == "77" and saved["GITHUB_CLIENT_ID"] == "Iv1.abc"
    from django.conf import settings

    assert settings.SIGN_IN == SignIn()  # people sign in with the OAuth app only
    assert client.get("/setup/github-app/").context["source"] == "volume"


def test_return_from_another_browser(no_app, client, db):
    response = client.get("/setup/github-app/registered/?code=c&state=other")
    assert response.status_code == 400
    assert b"RegistrationExpired" in response.content


def test_settings_in_the_environment_block_it(no_app, client, db, monkeypatch):
    monkeypatch.setenv("GITHUB_APP_SLUG", "half")
    response = client.get("/setup/github-app/")
    assert b'data-registration-blocked="AppSettingsInEnvironment"' in response.content


def test_setup_code_command(no_app, db, capsys):
    call_command("github_app_setup_code")
    assert capsys.readouterr().out.strip() == AppRegistration.setup_code()


def test_manifest_command(capsys):
    call_command("app_manifest")
    output = capsys.readouterr().out
    assert '"pull_requests": "read"' in output and "email_addresses" not in output


def test_every_account_may_install_the_app():
    assert manifest("dashboard", "https://dashboard.example.org")["public"] is True


def test_the_app_only_reads():
    """The site writes nothing to GitHub for now: the app asks for no write permission."""
    permissions = manifest("dashboard", "https://dashboard.example.org")["default_permissions"]
    assert permissions["pull_requests"] == "read"
    assert set(permissions.values()) == {"read"}
