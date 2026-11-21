"""The label of a step deleted in a repository on GitHub, with the step labels off."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import quote

from pycal_dashboard.errors import GitHubNotFound
from pycal_dashboard.github.installation_token import InstallationToken

from .action import Action

if TYPE_CHECKING:
    from pycal_dashboard.models import PullRequestStep, Repository


class StepLabelDeleted(Action):
    """Delete the label of a step in a repository on GitHub, and with it from its pull requests.

    A label that GitHub no longer has is gone already. The GitHub App needs to write to issues
    or pull requests, which it asks for.
    """

    kind = "label"

    def __init__(self, repository: Repository, step: PullRequestStep, name: str):
        """The label to delete.

        Parameters:
            repository: The repository, with the GitHub App.
            step: The step of the label.
            name: The name of the label on GitHub.
        """
        self.repository, self.step, self.name = repository, step, name

    def perform(self) -> None:
        """Delete the label with the token of the installation of the repository."""
        client = InstallationToken.client(self.repository.installation.github_id)
        path = f"/repos/{self.repository.full_name}/labels/{quote(self.name, safe='')}"
        try:
            client.request("DELETE", path)
        except GitHubNotFound:  # deleted on GitHub already
            pass

    def text(self) -> str:
        """Which label was deleted, and for which step."""
        where = self.repository.full_name
        return f"Label {self.name} deleted in {where}: the step labels of {self.step.name} are off"
