"""The client of the API of GitHub translates the answers into errors of the site."""

import pytest

from pycal_dashboard import errors
from pycal_dashboard.github.client import GitHubClient


@pytest.mark.parametrize(
    ("status", "message", "error"),
    [
        (404, "Not Found", errors.GitHubNotFound),
        (401, "Bad credentials", errors.GitHubLoginExpired),
        (403, "API rate limit exceeded", errors.GitHubRateLimited),
        (429, "rate limit", errors.GitHubRateLimited),
        (403, "Resource not accessible by integration", errors.MissingPermissions),
        (500, "Server Error", errors.GitHubError),
    ],
)
def test_errors(github, settings, status, message, error):
    github.fail_with, github.fail_message = status, message
    with pytest.raises(error) as raised:
        GitHubClient("token").request("GET", "/meta")
    assert f"GET /meta: {status} {message}" in str(raised.value)
    assert github.requests[0].headers["Authorization"] == "Bearer token"


def test_unreachable(github):
    github.unreachable = True
    with pytest.raises(errors.GitHubUnreachable):
        GitHubClient().request("GET", "/meta")


def test_answer_that_is_no_json(github, monkeypatch):
    import httpx

    monkeypatch.setattr(
        github, "handle", lambda request: httpx.Response(502, text="<html>Bad gateway</html>")
    )
    from pycal_dashboard.github import client

    monkeypatch.setattr(client, "TRANSPORT", httpx.MockTransport(github.handle))
    with pytest.raises(errors.GitHubError) as raised:
        GitHubClient().request("GET", "/meta")
    assert str(raised.value) == "GET /meta: 502 Bad gateway"  # the text, not the HTML
