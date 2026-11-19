"""Find a repository that a person adds to a project, public or private, and record it."""

import re

from pycal_dashboard.errors import GitHubNotFound, RepositoryNameInvalid, RepositoryNotFound
from pycal_dashboard.github.installation_token import InstallationToken
from pycal_dashboard.github.person_client import PersonClient
from pycal_dashboard.models import Repository

from .installation_store import InstallationStore

# who may read a repository, as GitHub names the permissions of a collaborator
READERS = {"admin", "maintain", "write", "triage", "read"}
NAME = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})/[A-Za-z0-9._-]{1,100}")


class RepositoryLookup:
    """The repositories that a person may add to a project.

    Public repositories are found with the token of the person. A private repository is found
    only through the GitHub App installed on it, and only if the person may read it there.
    """

    def __init__(self, person: PersonClient):
        """A lookup for a person.

        Args:
            person: GitHub with the token of the person.
        """
        self.person = person

    @staticmethod
    def full_name(text: str) -> str:
        """The ``owner/name`` of a repository from what a person entered.

        Args:
            text: The name or a link to the repository on GitHub.

        Returns:
            The full name.

        Raises:
            RepositoryNameInvalid: It names no repository.

        Examples:
            >>> RepositoryLookup.full_name(" https://github.com/collective/icalendar/pulls ")
            'collective/icalendar'
            >>> RepositoryLookup.full_name("collective/icalendar.git")
            'collective/icalendar'
        """
        name = text.strip().removeprefix("https://").removeprefix("http://")
        name = name.removeprefix("www.").removeprefix("github.com/")
        name = "/".join(name.split("/")[:2]).removesuffix(".git")
        if not NAME.fullmatch(name):
            raise RepositoryNameInvalid(text.strip()[:200])
        return name

    def find(self, text: str) -> Repository:
        """The repository, read from GitHub and recorded, if the person may see it.

        Args:
            text: Its name or a link to it.

        Returns:
            The repository, recorded with what GitHub said.

        Raises:
            RepositoryNameInvalid: The text names no repository.
            RepositoryNotFound: The person may not see a repository of this name.
        """
        full_name = self.full_name(text)
        data = self.person.repository(full_name)
        installation = InstallationToken.installation_of(full_name)
        if data is None:
            data = self.private(full_name, installation)
        return self.record(data, installation)

    def private(self, full_name: str, installation: dict | None) -> dict:
        """A private repository that the GitHub App is installed on, if the person may read it.

        Args:
            full_name: The repository.
            installation: The installation on it, None if the app is not installed on it.

        Returns:
            The repository.

        Raises:
            RepositoryNotFound: The app is not installed on it, or the person may not read it.
        """
        if installation is None:
            raise RepositoryNotFound(full_name)
        client = InstallationToken.client(installation["id"])
        try:
            data = client.request("GET", f"/repos/{full_name}").json()
            permission = client.request(
                "GET", f"/repos/{full_name}/collaborators/{self.person.login}/permission"
            ).json()
        except GitHubNotFound as error:
            raise RepositoryNotFound(full_name) from error
        if permission.get("permission") not in READERS:
            raise RepositoryNotFound(full_name)
        return data

    @staticmethod
    def record(data: dict, installation: dict | None = None) -> Repository:
        """Record a repository as GitHub describes it.

        Args:
            data: The repository, from ``GET /repos/{owner}/{name}``.
            installation: The installation of the GitHub App on it, None if there is none.

        Returns:
            The repository.
        """
        repository = (
            Repository.objects.filter(github_id=data["id"]).first()
            or Repository.objects.filter(full_name__iexact=data["full_name"]).first()
            or Repository()
        )
        repository.github_id = data["id"]
        repository.full_name = data["full_name"]
        repository.private = bool(data.get("private"))
        repository.description = data.get("description") or ""
        repository.installation = InstallationStore.record(installation) if installation else None
        repository.save()
        return repository
