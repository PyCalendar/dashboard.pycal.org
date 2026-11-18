"""The public pages, the error pages and the switch of the colors."""

import pytest

from tests.conftest import REPOSITORY

PUBLIC = [
    "/",
    "/about/",
    "/contribute/",
    "/reviews/",
    "/repositories/",
    "/contributors/",
    "/labels/",
    f"/repositories/{REPOSITORY}/",
    "/contributors/alice/",
    "/accounts/login/",
    "/setup/github-app/",
    "/health/",
]


@pytest.mark.parametrize("path", PUBLIC)
def test_public_pages(client, synced, path):
    assert client.get(path).status_code == 200


def test_start_page(client, synced):
    content = client.get("/").content.decode()
    assert "Issue 1" in content  # good first issue
    assert "Pull request 4" in content  # waiting for a review
    assert "Pull request 3" in content  # a first contribution
    assert "dependabot" not in content.split("Most active")[1]
    assert "A private issue" not in content


def test_private_repositories_are_hidden(client, synced):
    assert client.get("/repositories/PyCalendar/secret/").status_code == 404
    assert b"secret" not in client.get("/repositories/").content
    assert client.get("/contributors/mallory/").status_code == 404


def test_repository_filters(client, synced):
    closed = client.get(f"/repositories/{REPOSITORY}/?state=closed").content.decode()
    assert "Pull request 5" in closed and "Issue 1" not in closed
    issues = client.get(f"/repositories/{REPOSITORY}/?kind=issues").content.decode()
    assert "Issue 1" in issues and "Pull request 4" not in issues


@pytest.mark.parametrize(
    ("path", "status", "error"),
    [
        ("/repositories/PyCalendar/nothing/", 404, "RepositoryNotFound"),
        ("/contributors/nobody/", 404, "ContributorNotFound"),
        ("/?days=0", 400, "InvalidDays"),
        ("/contributors/?days=abc", 400, "InvalidDays"),
        (f"/repositories/{REPOSITORY}/?state=merged", 400, "InvalidFilter"),
        (f"/repositories/{REPOSITORY}/?page=0", 400, "InvalidPageNumber"),
        (f"/repositories/{REPOSITORY}/?page=9", 400, "InvalidPageNumber"),
    ],
)
def test_error_pages_link_their_documentation(client, synced, path, status, error):
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


def test_labels_page(client, synced):
    content = client.get("/labels/").content.decode()
    assert 'data-rule="size"' in content and "size: XS" in content
    assert f"{REPOSITORY}#3" in content
