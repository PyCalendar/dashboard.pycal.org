"""The site names the permissions and events that its GitHub App lacks."""

import jwt
import pytest
from django.core.management import CommandError, call_command

from pycal_dashboard.errors import GitHubAppNotConfigured, InvalidPrivateKey
from pycal_dashboard.github.app_check import AppCheck
from pycal_dashboard.github.permissions import EVENTS
from tests.conftest import person


def test_the_app_has_everything(github):
    check = AppCheck.read()
    assert check.complete and check.describe() == ""
    token = github.requests[0].headers["Authorization"].removeprefix("Bearer ")
    assert jwt.decode(token, options={"verify_signature": False})["iss"] == "1"


def test_the_app_lacks_permissions_and_events(github):
    github.app["permissions"] = {"metadata": "read"}
    github.app["events"] = ["issues"]
    check = AppCheck.read()
    assert check.missing_permissions == {
        "issues": "read",
        "pull_requests": "write",
        "checks": "read",
        "statuses": "read",
        "contents": "read",
    }
    assert "repository" in check.missing_events and not check.complete
    assert check.describe() == (
        "The GitHub App lacks the permissions issues: read, pull_requests: write, checks: read, "
        "statuses: read, contents: read and does not receive the events issue_comment, "
        "pull_request, pull_request_review, repository, label, check_run, check_suite, status, "
        "push: change them on https://github.com/organizations/PyCalendar/settings/apps/"
        "dashboard-test/permissions"
    )


def test_without_an_app(settings):
    settings.GITHUB_APP_ID = ""
    with pytest.raises(GitHubAppNotConfigured):
        AppCheck.token()


def test_a_wrong_key(settings):
    settings.GITHUB_APP_PRIVATE_KEY = "not a key"
    with pytest.raises(InvalidPrivateKey):
        AppCheck.token()


def test_the_command(github, capsys):
    call_command("check_app")
    assert "has everything it needs" in capsys.readouterr().out
    github.app["events"] = []
    with pytest.raises(CommandError, match="does not receive the events issues"):
        call_command("check_app")
    github.unreachable = True
    with pytest.raises(CommandError, match="GitHub could not be reached"):
        call_command("check_app")


def test_the_setup_page_shows_it_to_administrators(client, github, db):
    github.app["events"] = ["issues"]
    assert b"data-app-lacks" not in client.get("/setup/github-app/").content  # visitors
    client.force_login(person(7, "admin"))
    page = client.get("/setup/github-app/").content.decode()
    assert "data-app-lacks" in page and "<code>repository</code>" in page
    github.app["events"] = list(EVENTS)
    assert b"data-app-complete" in client.get("/setup/github-app/").content


def test_the_setup_page_works_while_github_is_down(client, github, db):
    github.unreachable = True
    client.force_login(person(7, "admin"))
    assert client.get("/setup/github-app/").status_code == 200
