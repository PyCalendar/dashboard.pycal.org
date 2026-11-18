"""Requests to the API of GitHub, with its errors translated.

httpx is imported with the first request, so that the idle site does not keep it in memory.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings

from pycal_dashboard.errors import (
    GitHubError,
    GitHubLoginExpired,
    GitHubNotFound,
    GitHubRateLimited,
    GitHubUnreachable,
    MissingPermissions,
)
from pycal_dashboard.import_guard import IMPORT_GUARD

if TYPE_CHECKING:
    import httpx

# The tests replace it with a fake GitHub (tests/fakes/github.py); None: the network.
TRANSPORT: httpx.BaseTransport | None = None
TIMEOUT = 20.0
API_VERSION = "2022-11-28"


class GitHubClient:
    """Requests to GitHub with a token: of an installation, of a person or of the app."""

    def __init__(self, token: str = "", scheme: str = "Bearer"):
        """A client.

        Args:
            token: The token; "" for requests without one.
            scheme: How the token is sent, ``Bearer`` for all tokens of a GitHub App.
        """
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": f"{settings.SITE_NAME} dashboard",
        }
        if token:
            headers["Authorization"] = f"{scheme} {token}"
        with IMPORT_GUARD:  # see import_guard.py
            import httpx  # only when the site speaks with GitHub

        self.http = httpx.Client(
            base_url=settings.GITHUB_API,
            headers=headers,
            timeout=TIMEOUT,
            transport=TRANSPORT,
        )

    def request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Send a request and check the answer.

        Args:
            method: GET, POST, DELETE ...
            path: The path of the API, such as ``/repos/o/r``.
            **kwargs: For httpx, such as ``json`` or ``headers``.

        Returns:
            The answer, if it is a success.

        Raises:
            GitHubUnreachable: GitHub could not be reached.
            GitHubNotFound: 404.
            GitHubLoginExpired: 401 for the token of a person.
            GitHubRateLimited: No requests left.
            MissingPermissions: The app may not do this.
            GitHubError: Another error.
        """
        with IMPORT_GUARD:  # see import_guard.py
            import httpx  # loaded by __init__ already

        try:
            response = self.http.request(method, path, **kwargs)
        except httpx.TransportError as error:
            raise GitHubUnreachable(f"{method} {path}: {error}") from error
        if response.is_success:
            return response
        message = self.message(response)
        detail = f"{method} {path}: {response.status_code} {message}"
        if response.status_code == 404:
            raise GitHubNotFound(detail)
        if response.status_code == 401:
            raise GitHubLoginExpired(detail)
        if response.status_code in (403, 429) and (
            response.headers.get("x-ratelimit-remaining") == "0" or "rate limit" in message.lower()
        ):
            raise GitHubRateLimited(detail)
        if response.status_code == 403 and "not accessible by integration" in message.lower():
            raise MissingPermissions(detail)
        raise GitHubError(detail)

    @staticmethod
    def message(response: httpx.Response) -> str:
        """The message of an answer with an error.

        Args:
            response: The answer.

        Returns:
            The message of GitHub, or the start of the answer.
        """
        try:
            data = response.json()
        except ValueError:
            return response.text[:200]
        return str(data.get("message", "")) if isinstance(data, dict) else ""
