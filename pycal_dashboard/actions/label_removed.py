"""A label removed on GitHub from a pull request that entered or completed a step."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import quote

from pycal_dashboard.errors import GitHubNotFound
from pycal_dashboard.github.installation_token import InstallationToken

from .action import Action

if TYPE_CHECKING:
    from pycal_dashboard.models import Issue, PullRequestStep


class LabelRemoved(Action):
    """Remove a label from a pull request on GitHub, with the GitHub App, and record it.

    A pull request without the label stays as it is. The app needs to write to pull requests
    (``pull_requests: write``), which it asks for.
    """

    kind = "label"

    def __init__(self, issue: Issue, label: str, step: PullRequestStep, trigger: str = "complete"):
        """The label to remove.

        Parameters:
            issue: The pull request, of a repository with the GitHub App.
            label: The name of the label.
            step: The step it entered or completed.
            trigger: ``enter`` or ``complete``; ``status`` for the status label of a step.
        """
        self.issue, self.label, self.step, self.trigger = issue, label, step, trigger

    def perform(self) -> None:
        """Remove the label with the token of the installation of the repository."""
        installation = self.issue.repository.installation
        client = InstallationToken.client(installation.github_id)
        path = (
            f"/repos/{self.issue.repository.full_name}/issues/{self.issue.number}/labels/"
            f"{quote(self.label, safe='')}"
        )
        try:
            client.request("DELETE", path)
        except GitHubNotFound:  # it did not have the label
            pass

    def text(self) -> str:
        """What was removed, from which pull request, and why."""
        if self.trigger == "status":  # the status label of the step it is in, or was in
            return (
                f"Label {self.label} removed from {self.issue.repository.full_name}#"
                f"{self.issue.number}: it is not in the step {self.step.name}"
            )
        why = "entered" if self.trigger == "enter" else "completed"
        return (
            f"Label {self.label} removed from {self.issue.repository.full_name}#"
            f"{self.issue.number}: it {why} the step {self.step.name}"
        )
