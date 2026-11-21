"""The data that a condition needs: how the background reads it, and whether it is complete."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from pycal_dashboard.github.permissions import EVENTS, LEVELS, REQUIRED

if TYPE_CHECKING:
    from pycal_dashboard.conditions.evidence import Evidence
    from pycal_dashboard.github.client import GitHubClient
    from pycal_dashboard.models import Issue, Repository


class DataSpec(ABC):
    """Data of a pull request that conditions check, such as its labels or its checks.

    The update of a repository in the background (``RepositoryUpdate``) asks every data spec
    that is :meth:`enabled` to :meth:`fetch` what it needs of the repository, and reads the open
    pull requests with one query of GraphQL made of the fields of every spec (``graphql``),
    which each spec keeps (:meth:`keep_pull_request`). A condition is checked only when
    every one of its data specs says that the data of the pull request is :meth:`complete`;
    else the condition cannot be assessed yet.

    Attributes:
        id: The name of the data, such as ``labels``.
        title: What the data is, for the documentation.
        permissions: The permissions of the GitHub App that reading it needs.
        events: The webhooks that tell of its changes, which update the repository.
        graphql: The fields of a ``PullRequest`` of GraphQL that it needs, "" for none.
    """

    id: str = ""
    title: str = ""
    permissions: dict[str, str] = {}
    events: tuple[str, ...] = ()
    graphql: str = ""

    def enabled(self, granted: dict[str, str] | None = None) -> bool:
        """Whether the GitHub App asks for every permission and webhook that the data needs.

        Data that needs more is described but not read until the app asks for it
        (``github/permissions.py``), nor while an installation has not accepted its permissions.

        Parameters:
            granted: The permissions of the installation of the repository, as its owners
                accepted them; None for those of the app.

        Returns:
            True if the background reads it.
        """
        for permissions in (REQUIRED, granted) if granted is not None else (REQUIRED,):
            if any(
                LEVELS.get(permissions.get(name, ""), 0) < LEVELS[level]
                for name, level in self.permissions.items()
            ):
                return False
        return all(event in EVENTS for event in self.events)

    def fetch(self, client: GitHubClient, repository: Repository) -> int:
        """Read the data of a repository from GitHub and keep it, in the background.

        Parameters:
            client: The client that reads the repository (``GitHubClient``).
            repository: The repository, after its issues and pull requests were read.

        Returns:
            How many things were read, such as labels; 0 for data of pull requests only.
        """
        return 0

    def keep_pull_request(self, issue: Issue, node: dict) -> None:
        """Keep what the query of GraphQL answered for an open pull request.

        Parameters:
            issue: The pull request.
            node: The pull request of GraphQL, with the fields of ``graphql``.
        """

    def evidence(self, issue: Issue) -> list[Evidence]:
        """Where people see the data of a pull request, for the evidence of its conditions.

        Parameters:
            issue: The pull request.

        Returns:
            The links, such as to the checks on GitHub; none by default.
        """
        return []

    @abstractmethod
    def complete(self, issue: Issue) -> bool:
        """Whether the data of a pull request is complete, so that a condition can be assessed.

        Parameters:
            issue: The pull request (``Issue``).

        Returns:
            True if the data is there and current.
        """

    def complete_in(self, repositories: list[Repository]) -> bool:
        """Whether the data of all pull requests of repositories is complete, for a state.

        A state counts in all repositories of a project, such as the reviews a person gave.

        Parameters:
            repositories: The repositories.

        Returns:
            True if the data of every repository is there; the data of single pull requests,
            such as their checks, does not need more.
        """
        return True

    def describe(self) -> dict:
        """The data spec for the JSON and the documentation.

        Returns:
            Its id, title, permissions, webhooks and whether it is read.
        """
        return {
            "id": self.id,
            "title": str(self.title),
            "permissions": dict(self.permissions),
            "events": list(self.events),
            "enabled": self.enabled(),
        }
