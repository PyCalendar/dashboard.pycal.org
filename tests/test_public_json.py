"""Every public page has its information as JSON at <page>.json, readable by other sites."""

import pytest

from pycal_dashboard.public_json import CORS, JSON_PAGES, json_address

pytestmark = pytest.mark.django_db


def read(client, path: str, status: int = 200) -> dict:
    response = client.get(path)
    assert response.status_code == status, (path, response.content[:300])
    assert response["Content-Type"] == "application/json"
    for name, value in CORS.items():
        assert response[name] == value
    return response.json()


def test_the_start_page(client):
    found = read(client, "/index.json")
    assert found["github_app"] is True and found["sign_in"] is True
    assert found["organizations"] == ["pycalendar"]
    assert found["documentation"] == "https://docs.example.org/"
    assert found["pages"] == {
        "home": "/index.json",
        "about": "/about.json",
        "licenses": "/licenses.json",
    }


def test_the_start_page_without_apps(client, settings):
    from pycal_dashboard.sign_in import SignIn

    settings.GITHUB_APP_ID = ""
    settings.SIGN_IN = SignIn()
    found = read(client, "/index.json")
    assert found["github_app"] is False and found["sign_in"] is False


def test_the_about_and_licenses(client):
    about = read(client, "/about.json")
    assert (
        about["build"]["version"] and about["github_app"]["permissions"]["pull_requests"] == "read"
    )
    licenses = read(client, "/licenses.json")
    assert licenses["license"] == "AGPL-3.0-or-later" and licenses["packages"]


def test_the_json_is_public_also_with_a_session(client, alice):
    client.force_login(alice)
    assert "Install the GitHub App" in client.get("/").content.decode()
    assert read(client, "/index.json")["sign_in"] is True


def test_personal_pages_have_no_json(client, alice):
    client.force_login(alice)
    for path in ("/account.json", "/account/deliveries.json", "/setup/oauth-app.json"):
        assert read(client, path, status=404)["error"] == "NotFound"


def test_unknown_addresses(client):
    assert read(client, "/nothing.json", status=404)["error"] == "NotFound"
    assert read(client, "/api/v1.json", status=404)["error"] == "NotFound"
    assert client.get("/api/v1/").status_code == 404  # the pages have JSON instead


def test_javascript_of_other_sites_may_read_it(client):
    response = client.options("/about.json", HTTP_ORIGIN="https://example.org")
    assert response.status_code == 204
    assert response["Access-Control-Allow-Origin"] == "*"
    assert "GET" in response["Access-Control-Allow-Methods"]


def test_the_json_can_only_be_read(client):
    response = client.post("/about.json")
    assert response.status_code == 405 and response.json()["error"] == "MethodNotAllowed"


def test_the_html_is_unchanged(client):
    response = client.get("/about/")
    assert response["Content-Type"].startswith("text/html")
    assert "Access-Control-Allow-Origin" not in response


def test_every_page_with_json_exists():
    from django.urls import get_resolver

    names = {name for name in get_resolver().reverse_dict if isinstance(name, str)}
    assert names >= JSON_PAGES


@pytest.mark.parametrize(
    ("page", "json"), [("/", "/index.json"), ("/about/", "/about.json"), ("/a/b/", "/a/b.json")]
)
def test_the_address_of_the_json(page, json):
    assert json_address(page) == json
