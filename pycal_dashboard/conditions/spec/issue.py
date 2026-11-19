"""The pull request itself: whether it is open, closed or merged."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pycal_dashboard.conditions.spec.base import DataSpec

if TYPE_CHECKING:
    from pycal_dashboard.github.client import GitHubClient
    from pycal_dashboard.models import Issue, Repository


class IssueData(DataSpec):
    """The state of the pull request: open, closed, merged, as its issue was read.

    The update of the repository reads every issue and pull request anyway, so there is nothing
    more to fetch: the data is complete once the pull request is known.
    """

    id = "issue"
    title = "Whether the pull request is open, closed or merged"
    permissions = {"pull_requests": "read"}
    events = ("pull_request",)

    def fetch(self, client: GitHubClient, repository: Repository) -> int:
        """Nothing more: the issues of the repository were read with it.

        Parameters:
            client: The client.
            repository: The repository.

        Returns:
            0.
        """
        return 0

    def complete(self, issue: Issue) -> bool:
        """The pull request is known.

        Parameters:
            issue: The pull request.

        Returns:
            True.
        """
        return True
