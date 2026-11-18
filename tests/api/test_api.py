"""The JSON API: what runs; errors as JSON with their documentation."""

import pytest


def test_index(client, db):
    data = client.get("/api/v1/").json()
    assert data["api"] == 1 and data["site"]
    assert data["github_app"] is True and data["sign_in"] is True
    assert data["organizations"] == ["pycalendar"]
    assert data["documentation"] == "https://docs.example.org/"


def test_index_without_app(client, db, settings):
    from pycal_dashboard.sign_in import SignIn

    settings.GITHUB_APP_ID = ""
    settings.SIGN_IN = SignIn()
    data = client.get("/api/v1/").json()
    assert data["github_app"] is False and data["sign_in"] is False


@pytest.mark.parametrize("path", ["/api/v1/nothing/", "/api/v1/repositories/", "/api/v1/overview/"])
def test_errors(client, db, path):
    response = client.get(path)
    assert response.status_code == 404
    data = response.json()
    assert data["error"] == "ApiEndpointNotFound" and data["title"] and data["detail"]
    assert data["documentation"].endswith(
        "reference/errors.html#pycal_dashboard.errors.dashboard.ApiEndpointNotFound"
    )
