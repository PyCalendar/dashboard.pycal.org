"""The message of a project written on GitHub as a comment on a pull request, or updated."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pycal_dashboard.errors import GitHubNotFound

from .action import Action

if TYPE_CHECKING:
    from pycal_dashboard.github.client import GitHubClient
    from pycal_dashboard.models import Issue


class MessageWritten(Action):
    """Write the message as a comment on a pull request, or update the comment, and record it.

    A comment that was deleted on GitHub is written again. The GitHub App needs to write to
    pull requests (``pull_requests: write``), which it asks for.

    Attributes:
        github_id: The id of the comment on GitHub after :meth:`perform`.
    """

    kind = "message"

    def __init__(
        self, client: GitHubClient, issue: Issue, body: str, comment_id: int | None = None
    ):
        """The comment to write.

        Parameters:
            client: The client of the installation of the repository.
            issue: The pull request.
            body: The text of the comment, in Markdown.
            comment_id: The id of the comment that the site wrote before; None for a new one.
        """
        self.client, self.issue, self.body = client, issue, body
        self.github_id = comment_id
        self.updated = False

    def perform(self) -> None:
        """Update the comment, or write a new one."""
        repository = self.issue.repository.full_name
        if self.github_id:
            try:
                self.client.request(
                    "PATCH",
                    f"/repos/{repository}/issues/comments/{self.github_id}",
                    json={"body": self.body},
                )
                self.updated = True
                return
            except GitHubNotFound:  # deleted on GitHub: a new one
                pass
        answer = self.client.request(
            "POST",
            f"/repos/{repository}/issues/{self.issue.number}/comments",
            json={"body": self.body},
        )
        self.github_id = answer.json()["id"]

    def text(self) -> str:
        """Which pull request got the message."""
        what = "updated on" if self.updated else "written on"
        pull = f"{self.issue.repository.full_name}#{self.issue.number}"
        return f"The message of the project {what} {pull}"
