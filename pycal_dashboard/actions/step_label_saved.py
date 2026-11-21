"""The status label of a step created or changed in a repository on GitHub."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import quote

from pycal_dashboard.github.installation_token import InstallationToken

from .action import Action

if TYPE_CHECKING:
    from pycal_dashboard.models import PullRequestStep, Repository


class StepLabelSaved(Action):
    """Create the label of a step in a repository, or change its name, color and description.

    The GitHub App needs to write to issues or pull requests, which it asks for. ``label`` is
    the answer of GitHub after :meth:`perform`, with the ``id`` of the label.
    """

    kind = "label"

    def __init__(
        self,
        repository: Repository,
        step: PullRequestStep,
        name: str,
        color: str,
        description: str,
        old: str = "",
    ):
        """The label to save.

        Parameters:
            repository: The repository, with the GitHub App.
            step: The step of the label.
            name: The name of the label, such as ``Step: Review``.
            color: Its color, such as ``d73a4a``.
            description: Its description, at most 100 characters.
            old: The name of the label on GitHub to change; "" to create it.
        """
        self.repository, self.step, self.name = repository, step, name
        self.color, self.description, self.old = color, description, old
        self.label: dict = {}

    def perform(self) -> None:
        """Create or change the label with the token of the installation of the repository."""
        client = InstallationToken.client(self.repository.installation.github_id)
        fields = {"color": self.color, "description": self.description}
        path = f"/repos/{self.repository.full_name}/labels"
        if self.old:
            answer = client.request(
                "PATCH", f"{path}/{quote(self.old, safe='')}", json={"new_name": self.name} | fields
            )
        else:
            answer = client.request("POST", path, json={"name": self.name} | fields)
        self.label = answer.json()

    def text(self) -> str:
        """Which label was created or changed, and for which step."""
        done = f"changed from {self.old}" if self.old else "created"
        where = self.repository.full_name
        return f"Label {self.name} {done} in {where} for the step {self.step.name}"
