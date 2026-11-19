"""Read a repository from GitHub: whether it is private, its open issues and pull requests."""

import re

from django.utils import timezone

from pycal_dashboard.errors import DashboardError, translate
from pycal_dashboard.github.client import GitHubClient
from pycal_dashboard.github.installation_token import InstallationToken
from pycal_dashboard.models import Repository

from .installation_store import InstallationStore

LAST_PAGE = re.compile(r'[?&]page=(\d+)[^>]*>;\s*rel="last"')


class RepositoryUpdate:
    """One reading of a repository, in the background (``UpdateJob``).

    With the GitHub App installed on it, the site reads with the token of the installation, also
    private repositories; else without a token, which sees public repositories.
    """

    def __init__(self, repository: Repository):
        """An update of a repository.

        Args:
            repository: The repository.
        """
        self.repository = repository

    @staticmethod
    def count(response) -> int:
        """The number of items of a list of GitHub read with one item per page.

        Args:
            response: The answer to a request with ``per_page=1``.

        Returns:
            The number of items: the number of the last page.
        """
        found = LAST_PAGE.search(response.headers.get("link", ""))
        return int(found[1]) if found else len(response.json())

    def client(self) -> GitHubClient:
        """The client that reads the repository, and its installation recorded.

        Returns:
            A client with the token of the installation, else without a token.
        """
        installation = InstallationToken.installation_of(self.repository.full_name)
        self.repository.installation = (
            InstallationStore.record(installation) if installation else None
        )
        return InstallationToken.client(installation["id"]) if installation else GitHubClient()

    def run(self) -> bool:
        """Read the repository and keep what GitHub says, or the error.

        Returns:
            True if it was read, False if an error was kept.
        """
        repository = self.repository
        try:
            client = self.client()
            data = client.request("GET", f"/repos/{repository.full_name}").json()
            pulls = self.count(
                client.request(
                    "GET",
                    f"/repos/{repository.full_name}/pulls",
                    params={"state": "open", "per_page": 1},
                )
            )
        except Exception as exception:  # every error is kept and shown on the project
            error: DashboardError = translate(exception)
            repository.error_code, repository.error_detail = error.code, str(error)[:500]
            repository.save()
            return False
        repository.full_name = data.get("full_name") or repository.full_name  # renamed
        repository.github_id = data.get("id") or repository.github_id
        repository.private = bool(data.get("private"))
        repository.description = data.get("description") or ""
        # GitHub counts the open pull requests among the open issues
        repository.open_pull_requests = pulls
        repository.open_issues = max(0, int(data.get("open_issues_count") or 0) - pulls)
        repository.error_code = repository.error_detail = ""
        repository.updated = timezone.now()
        repository.save()
        return True
