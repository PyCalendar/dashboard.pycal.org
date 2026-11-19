"""The data that a condition needs: how the background reads it, and whether it is complete."""

from abc import ABC, abstractmethod

from pycal_dashboard.github.permissions import EVENTS, LEVELS, REQUIRED


class DataSpec(ABC):
    """Data of a pull request that conditions check, such as its labels or its checks.

    The update of a repository in the background (``RepositoryUpdate``) asks every data spec
    that is :meth:`enabled` to :meth:`fetch` what it needs. A condition is checked only when
    every one of its data specs says that the data of the pull request is :meth:`complete`;
    else the condition cannot be assessed yet.

    Attributes:
        id: The name of the data, such as ``labels``.
        title: What the data is, for the documentation.
        permissions: The permissions of the GitHub App that reading it needs.
        events: The webhooks that tell of its changes, which update the repository.
    """

    id: str = ""
    title: str = ""
    permissions: dict[str, str] = {}
    events: tuple[str, ...] = ()

    def enabled(self) -> bool:
        """Whether the GitHub App asks for every permission and webhook that the data needs.

        Data that needs more is described but not read until the app asks for it
        (``github/permissions.py``).

        Returns:
            True if the background reads it.
        """
        granted = all(
            LEVELS.get(REQUIRED.get(name, ""), 0) >= LEVELS[level]
            for name, level in self.permissions.items()
        )
        return granted and all(event in EVENTS for event in self.events)

    @abstractmethod
    def fetch(self, client, repository) -> int:
        """Read the data of a repository from GitHub and keep it, in the background.

        Args:
            client: The client that reads the repository (``GitHubClient``).
            repository: The repository, after its issues and pull requests were read.

        Returns:
            How many things were read, such as labels or pull requests.
        """

    @abstractmethod
    def complete(self, issue) -> bool:
        """Whether the data of a pull request is complete, so that a condition can be assessed.

        Args:
            issue: The pull request (``Issue``).

        Returns:
            True if the data is there and current.
        """

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
