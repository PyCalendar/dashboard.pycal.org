"""A label added on GitHub to a pull request that completed a step."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pycal_dashboard.github.installation_token import InstallationToken

from .action import Action

if TYPE_CHECKING:
    from pycal_dashboard.models import Issue, PullRequestStep


class LabelAdded(Action):
    """Add a label to a pull request on GitHub, with the GitHub App, and record it.

    GitHub creates the label in the repository when it has none of the name. The app needs to
    write to pull requests (``pull_requests: write``), which it asks for.
    """

    kind = "label"

    def __init__(self, issue: Issue, label: str, step: PullRequestStep, trigger: str = "complete"):
        """The label to add.

        Parameters:
            issue: The pull request, of a repository with the GitHub App.
            label: The name of the label.
            step: The step it entered or completed.
            trigger: ``enter`` or ``complete``; ``status`` for the status label of a step.
        """
        self.issue, self.label, self.step, self.trigger = issue, label, step, trigger

    def perform(self) -> None:
        """Add the label with the token of the installation of the repository."""
        installation = self.issue.repository.installation
        client = InstallationToken.client(installation.github_id)
        client.request(
            "POST",
            f"/repos/{self.issue.repository.full_name}/issues/{self.issue.number}/labels",
            json={"labels": [self.label]},
        )

    def text(self) -> str:
        """What was added, to which pull request, and why."""
        if self.trigger == "status":  # the status label of the step it is in, or was in
            return (
                f"Label {self.label} added to {self.issue.repository.full_name}#"
                f"{self.issue.number}: it is in the step {self.step.name}"
            )
        why = "entered" if self.trigger == "enter" else "left"
        return (
            f"Label {self.label} added to {self.issue.repository.full_name}#{self.issue.number}: "
            f"it {why} the step {self.step.name}"
        )
