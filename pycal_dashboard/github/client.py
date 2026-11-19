"""Requests to the API of GitHub, with its errors translated.

httpx is imported with the first request, so that the idle site does not keep it in memory.
"""

from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING, Any

from django.conf import settings

from pycal_dashboard.errors import (
    GitHubError,
    GitHubLoginExpired,
    GitHubNotFound,
    GitHubQueryFailed,
    GitHubRateLimited,
    GitHubUnavailable,
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
# GitHub is busy or a query took too long: ask again after these seconds (the tests: none)
BUSY = (502, 503, 504)
RETRY_DELAYS = (1.0, 3.0)


class GitHubClient:
    """Requests to GitHub with a token: of an installation, of a person or of the app."""

    def __init__(self, token: str = "", scheme: str = "Bearer"):
        """A client.

        Parameters:
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
        # what the last query of GraphQL cost: cost, remaining and resetAt, as GitHub says
        self.rate: dict = {}

    def request(self, method: str, path: str, retry: bool = True, **kwargs: Any) -> httpx.Response:
        """Send a request and check the answer; ask again while GitHub is busy.

        Parameters:
            method: GET, POST, DELETE ...
            path: The path of the API, such as ``/repos/o/r``.
            retry: Ask again after 502, 503 and 504 (``RETRY_DELAYS``); False when the caller
                asks differently instead, such as GraphQL with smaller pages.
            **kwargs: For httpx, such as ``json`` or ``headers``.

        Returns:
            The answer, if it is a success.

        Raises:
            GitHubUnreachable: GitHub could not be reached.
            GitHubUnavailable: 502, 503 or 504, also when asked again.
            GitHubNotFound: 404.
            GitHubLoginExpired: 401 for the token of a person.
            GitHubRateLimited: No requests left.
            MissingPermissions: The app may not do this.
            GitHubError: Another error.
        """
        with IMPORT_GUARD:  # see import_guard.py
            import httpx  # loaded by __init__ already

        for delay in (*(RETRY_DELAYS if retry else ()), None):
            try:
                response = self.http.request(method, path, **kwargs)
            except httpx.TransportError as error:
                raise GitHubUnreachable(f"{method} {path}: {error}") from error
            if response.status_code not in BUSY or delay is None:
                break
            time.sleep(delay)
        if response.is_success:
            return response
        message = self.message(response)
        detail = f"{method} {path}: {response.status_code} {message}"
        request_id = response.headers.get("x-github-request-id")
        if request_id:  # GitHub finds the request by it, such as in a question to its support
            detail += f" (GitHub request {request_id})"
        if response.status_code in BUSY:
            raise GitHubUnavailable(detail)
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
    def graphql_url() -> str:
        """The address of GraphQL: next to the REST API, also of GitHub Enterprise Server.

        Returns:
            Such as ``https://api.github.com/graphql`` or ``https://ghe.example/api/graphql``.
        """
        api = settings.GITHUB_API.rstrip("/")
        return api.removesuffix("/v3") + "/graphql"

    def graphql(self, query: str, **variables: Any) -> dict:
        """Ask GraphQL of GitHub: much data with one request, which costs few points.

        The query should ask for ``rateLimit { cost remaining resetAt }``, which the client
        keeps in :attr:`rate`.

        Parameters:
            query: The query.
            **variables: Its variables.

        Returns:
            The data of the answer.

        Raises:
            GitHubRateLimited: No points left.
            GitHubNotFound: The repository or pull request does not exist or is not visible.
            MissingPermissions: The token may not read it.
            GitHubQueryFailed: Another error of the query.
        """
        answer = self.request(
            "POST",
            self.graphql_url(),
            retry=False,  # a query too slow for GitHub is asked again with smaller pages
            json={"query": query, "variables": variables},
        ).json()
        data = answer.get("data") or {}
        self.rate = data.get("rateLimit") or self.rate
        errors = answer.get("errors") or []
        if errors:
            kind = str(errors[0].get("type", ""))
            detail = f"GraphQL {kind}: {errors[0].get('message', '')}"
            if kind == "RATE_LIMITED":
                raise GitHubRateLimited(detail)
            if kind == "NOT_FOUND":
                raise GitHubNotFound(detail)
            if kind == "FORBIDDEN":
                raise MissingPermissions(detail)
            raise GitHubQueryFailed(detail)
        return data

    @staticmethod
    def message(response: httpx.Response) -> str:
        """The message of an answer with an error.

        Parameters:
            response: The answer.

        Returns:
            The message of GitHub, or the start of the answer.
        """
        try:
            data = response.json()
        except ValueError:  # such as a page of HTML of a proxy: its title, else its text
            text = response.text
            title = re.search(r"<title>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
            text = title[1] if title else re.sub(r"<[^>]+>", " ", text)
            return " ".join(text.split())[:200]
        return str(data.get("message", "")) if isinstance(data, dict) else ""
