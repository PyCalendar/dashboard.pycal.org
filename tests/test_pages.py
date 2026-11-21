"""The public pages, the error pages and the switch of the colors."""

import pytest

from tests.conftest import person

PUBLIC = [
    "/",
    "/about/",
    "/licenses/",
    "/accounts/login/",
    "/setup/github-app/",
    "/health/",
    "/favicon.ico",
]
# the pages of GitHub data are gone: the site keeps no data of GitHub for now
REMOVED = [
    "/contribute/",
    "/reviews/",
    "/repositories/",
    "/repositories/PyCalendar/icalendar/",
    "/contributors/",
    "/contributors/alice/",
    "/labels/",
]


@pytest.mark.parametrize("path", PUBLIC)
def test_public_pages(client, db, path):
    assert client.get(path).status_code == 200


@pytest.mark.parametrize("path", REMOVED)
def test_no_pages_of_github_data(client, db, path):
    assert client.get(path).status_code == 404


def test_start_page(client, db):
    content = client.get("/").content.decode()
    assert "Welcome to the community of PyCalendar" in content
    assert "/accounts/login/" in content  # in the menu
    # the app and the account are in the menu: the start page has no cards of them
    assert "data-github-app" not in content and "data-sign-in" not in content
    assert "Install the GitHub App</a></p>" not in content
    assert "data-no-sign-in" not in content


def test_start_page_signed_in(client, db):
    client.force_login(person(77, "carol"))
    content = client.get("/").content.decode()
    assert "data-sign-in" not in content and "You are signed in" not in content


def test_start_page_without_sign_in(client, db, settings):
    from pycal_dashboard.sign_in import SignIn

    settings.SIGN_IN = SignIn()
    assert "dashboard.pycal.org has no OAuth app" in client.get("/").content.decode()


def test_installed(client, db):
    content = client.get("/setup/installed/?installation_id=5&setup_action=install").content
    assert b"The GitHub App is installed" in content and b'data-installation="5"' in content
    update = client.get("/setup/installed/?installation_id=5&setup_action=update").content
    assert b"is updated" in update


@pytest.mark.parametrize(
    ("path", "status", "error"),
    [
        ("/setup/installed/", 400, "InvalidInstallationId"),
        ("/setup/installed/?installation_id=abc", 400, "InvalidInstallationId"),
    ],
)
def test_error_pages_link_their_documentation(client, db, path, status, error):
    response = client.get(path)
    assert response.status_code == status
    content = response.content.decode()
    assert f'data-error="{error}"' in content
    assert "https://docs.example.org/reference/errors.html#pycal_dashboard.errors." in content
    assert f'.{error}"' in content
    assert "What this error means and how to solve it" in content
    assert "Details to copy" in content


def test_page_not_found(client, db):
    response = client.get("/no/such/page/")
    assert response.status_code == 404
    assert b"Page not found" in response.content and b"status-page" in response.content


def test_server_error_page(client, db, monkeypatch):
    from pycal_dashboard.views import errors

    def broken(*args, **kwargs):
        raise RuntimeError("database down")

    monkeypatch.setattr(errors, "status_page", broken)
    response = errors.server_error(client.get("/").wsgi_request)
    assert response.status_code == 500
    assert b"Something went wrong" in response.content


def test_csrf_failure_page(db):
    from django.test import Client

    response = Client(enforce_csrf_checks=True).post("/theme/", {"theme": "dark"})
    assert response.status_code == 403
    assert b"The form has expired" in response.content


def test_theme_switch(client, db):
    response = client.post("/theme/", {"theme": "dark", "next": "/about/"})
    assert response.status_code == 302 and response["Location"] == "/about/"
    assert response.cookies["theme"].value == "dark"
    assert b"color-scheme: dark;" in client.get("/").content
    away = client.post("/theme/", {"theme": "light", "next": "https://evil.example/"})
    assert away["Location"] == "/"


def test_colors_of_sign_pycal_org(client, db):
    content = client.get("/").content.decode()
    assert "--brand: #3b79aa;" in content and "--accent: #ffd43b;" in content


def test_health(client, db):
    assert client.get("/health/").json() == {"status": "ok", "github_app": True}


def test_about_has_the_tiles_and_the_tabs_of_the_version_and_the_app(client, db, settings):
    """Contact: the documentation, problems and feedback, the changelog; nothing else."""
    main = client.get("/about/").content.decode().split("<main")[1].split("</main>")[0]
    for tile in ("documentation", "feedback", "changelog"):
        assert f'data-tile="{tile}"' in main
    assert "Report a problem or leave feedback" in main
    assert "data-privacy-summary" not in main and "where to start" not in main
    version = client.get("/about/version/").content.decode()
    assert "data-version" in version and "Commit" in version or "Version" in version
    app = client.get("/about/github-app/").content.decode()
    assert "data-github-app" in app and "pull_requests" in app
    assert "writes nothing to GitHub" not in app and "the labels of steps" in app
