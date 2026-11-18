"""The JSON API: public data only, errors as JSON with their documentation."""

import pytest

from tests.conftest import REPOSITORY


def test_index(client, db):
    data = client.get("/api/v1/").json()
    assert data["version"] == 1 and data["repositories"] == "/api/v1/repositories/"


def test_overview(client, synced):
    data = client.get("/api/v1/overview/?days=30").json()
    assert data == {
        "repositories": 2,
        "open_issues": 2,
        "open_pulls": 3,
        "starter_issues": 1,
        "waiting_for_review": 2,
        "unanswered": 1,
        "merged": 1,
        "contributors": 3,
        "days": 30,
    }


def test_repositories(client, synced):
    rows = client.get("/api/v1/repositories/").json()["repositories"]
    assert [row["full_name"] for row in rows] == [REPOSITORY, "PyCalendar/plann"]
    assert rows[0]["open_pulls"] == 2 and rows[0]["api"] == f"/api/v1/repositories/{REPOSITORY}/"


def test_repository(client, synced):
    data = client.get(f"/api/v1/repositories/{REPOSITORY}/?kind=pulls").json()
    assert [item["number"] for item in data["items"]] == [3, 4]
    assert data["items"][0]["labels"] == ["first contribution", "size: XS"]
    assert data["pages"] == 1
    closed = client.get(f"/api/v1/repositories/{REPOSITORY}/?state=closed").json()
    assert [(i["number"], i["status"]) for i in closed["items"]] == [(5, "merged")]


def test_lists(client, synced):
    assert [i["number"] for i in client.get("/api/v1/starter-issues/").json()["items"]] == [1]
    assert {i["number"] for i in client.get("/api/v1/reviews/").json()["items"]} == {3, 4}
    people = client.get("/api/v1/contributors/").json()["contributors"]
    assert people[0] == {"login": "bob", "pulls": 1, "merged": 1, "issues": 1}


def test_contributor(client, synced):
    data = client.get("/api/v1/contributors/bob/").json()
    assert data["merged"] == 1 and data["review_requests"][0]["number"] == 4
    assert data["since"].startswith("2026-11-18")


@pytest.mark.parametrize(
    ("path", "status", "error"),
    [
        ("/api/v1/repositories/PyCalendar/secret/", 404, "RepositoryNotFound"),
        ("/api/v1/contributors/nobody/", 404, "ContributorNotFound"),
        ("/api/v1/overview/?days=-1", 400, "InvalidDays"),
        (f"/api/v1/repositories/{REPOSITORY}/?kind=x", 400, "InvalidFilter"),
        (f"/api/v1/repositories/{REPOSITORY}/?page=x", 400, "InvalidPageNumber"),
        ("/api/v1/nothing/", 404, "ApiEndpointNotFound"),
    ],
)
def test_errors(client, synced, path, status, error):
    response = client.get(path)
    assert response.status_code == status
    data = response.json()
    assert data["error"] == error and data["title"] and data["detail"]
    assert data["documentation"].endswith(
        f"reference/errors.html#{data['documentation'].split('#')[1]}"
    )
    assert data["documentation"].split("#")[1].endswith(f".{error}")
