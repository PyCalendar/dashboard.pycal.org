"""GitHub as a person sees it, with the token of their sign in: organizations and repositories."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pycal_dashboard.errors import (
    GitHubLoginExpired,
    GitHubNotFound,
    GitHubSignInExpired,
    GitHubTokenMissing,
)
from pycal_dashboard.import_guard import IMPORT_GUARD

from .client import GitHubClient

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser
    from django.contrib.auth.models import AnonymousUser


PER_PAGE = 100
PAGES = 5  # at most 500 repositories of an account are listed
SEARCH_RESULTS = 10


class PersonClient:
    """Reads GitHub with the token of a person: only reads, scopes ``user:email`` and ``read:org``.

    The token sees the public repositories and the organizations of the person; private
    repositories are found through the GitHub App, see ``RepositoryLookup``.
    """

    def __init__(self, token: str, login: str):
        """A client for a person.

        Parameters:
            token: The OAuth token of the person.
            login: The GitHub name of the person.
        """
        self.client = GitHubClient(token)
        self.login = login

    def request(self, method: str, path: str, **kwargs: Any) -> Any:  # noqa: ANN401
        """A request with the token of the person, see ``GitHubClient.request``.

        Parameters:
            method: GET, POST ...
            path: The path of the API.
            **kwargs: For httpx.

        Returns:
            The answer.

        Raises:
            GitHubSignInExpired: GitHub refused the token (401): the person signs in again.
        """
        try:
            return self.client.request(method, path, **kwargs)
        except GitHubLoginExpired as error:
            raise GitHubSignInExpired(str(error)) from error

    @classmethod
    def of(cls, user: AbstractBaseUser | AnonymousUser, login: str) -> PersonClient:
        """The client of a person who signed in with GitHub.

        Parameters:
            user: The user.
            login: Their GitHub name.

        Returns:
            The client.

        Raises:
            GitHubTokenMissing: The site has no token of the person: they sign in again.
        """
        with IMPORT_GUARD:  # see import_guard.py
            from allauth.socialaccount.models import SocialToken

        token = (
            SocialToken.objects.filter(account__user=user, account__provider="github")
            .order_by("-id")
            .first()
        )
        if token is None or not token.token:
            raise GitHubTokenMissing(f"@{login}")
        return cls(token.token, login)

    def all_pages(self, path: str, **params: Any) -> list[dict]:
        """The items of a list of GitHub, page by page.

        Parameters:
            path: The path, such as ``/user/orgs``.
            **params: More parameters of the request.

        Returns:
            The items.
        """
        found: list[dict] = []
        for number in range(1, PAGES + 1):
            page = self.request(
                "GET", path, params={**params, "per_page": PER_PAGE, "page": number}
            ).json()
            found.extend(page)
            if len(page) < PER_PAGE:
                break
        return found

    def organizations(self) -> list[str]:
        """The organizations of the person, sorted.

        Returns:
            Their names on GitHub.
        """
        return sorted((o["login"] for o in self.all_pages("/user/orgs")), key=str.lower)

    def repositories(self, owner: str) -> list[dict]:
        """The repositories of the person or of one of their organizations, sorted.

        Parameters:
            owner: The GitHub name of the person or of the organization.

        Returns:
            The repositories as GitHub describes them.
        """
        if owner.lower() == self.login.lower():
            found = self.all_pages("/user/repos", affiliation="owner")
        else:
            try:
                found = self.all_pages(f"/orgs/{owner}/repos")
            except GitHubNotFound:  # an account of a person, not an organization
                found = self.all_pages(f"/users/{owner}/repos")
        return sorted(found, key=lambda repository: repository["full_name"].lower())

    @staticmethod
    def query(text: str) -> str:
        """The search of GitHub for repositories whose name starts like the text.

        Parameters:
            text: What the person typed, such as ``ical`` or ``collective/ical``.

        Returns:
            The query of the search.

        Examples:
            >>> PersonClient.query("ical")
            'ical in:name'
            >>> PersonClient.query("collective/ical")
            'ical user:collective in:name'
            >>> PersonClient.query("collective/")
            'user:collective'
        """
        owner, _slash, name = text.strip().partition("/")
        if not _slash:
            return f"{owner} in:name"
        return f"{name} user:{owner} in:name" if name else f"user:{owner}"

    def search(self, text: str) -> list[str]:
        """Repositories of all of GitHub whose name is like the text.

        Parameters:
            text: What the person typed.

        Returns:
            Their full names, the most popular first.
        """
        answer = self.request(
            "GET",
            "/search/repositories",
            params={"q": self.query(text), "per_page": SEARCH_RESULTS},
        ).json()
        return [item["full_name"] for item in answer.get("items", [])]

    def repository(self, full_name: str) -> dict | None:
        """A repository as the person sees it.

        Parameters:
            full_name: Such as ``collective/icalendar``.

        Returns:
            The repository, None if the person cannot see it.
        """
        try:
            return self.request("GET", f"/repos/{full_name}").json()
        except GitHubNotFound:
            return None
