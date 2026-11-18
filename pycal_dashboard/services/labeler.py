"""Label a pull request with the rules of ``PULL_REQUEST_LABELS``."""

import logging
from urllib.parse import quote

from django.conf import settings

from pycal_dashboard.errors import (
    CannotWriteLabels,
    GitHubError,
    GitHubNotFound,
    MissingPermissions,
)
from pycal_dashboard.github.client import GitHubClient
from pycal_dashboard.models import Item, LabelChange, Repository

log = logging.getLogger(__name__)


class PullRequestLabeler:
    """Adds the labels of the rules to a pull request and removes those that do not apply."""

    def __init__(self, client: GitHubClient, repository: Repository):
        """A labeler.

        Args:
            client: A client with the rights of the installation.
            repository: The repository of the pull requests.
        """
        self.client = client
        self.repository = repository
        self.rules = settings.PULL_REQUEST_LABELS

    def complete(self, pull: dict) -> dict:
        """The pull request with the numbers of lines, read from GitHub if they are missing.

        Args:
            pull: The pull request, such as of a list, which has no numbers of lines.

        Returns:
            The pull request with ``additions`` and ``deletions``.
        """
        if isinstance(pull.get("additions"), int) or not self.rules.rules:
            return pull
        return self.client.get(f"/repos/{self.repository.full_name}/pulls/{pull['number']}")

    def label(self, pull: dict) -> tuple[set[str], set[str]]:
        """Set the labels of the rules on an open pull request.

        Args:
            pull: The pull request as GitHub describes it.

        Returns:
            The labels added and removed.

        Raises:
            CannotWriteLabels: The installation may not write labels.
        """
        if pull.get("state") != "open" or not self.rules.rules:
            return set(), set()
        pull = self.complete(pull)
        current = {label["name"] for label in pull.get("labels", [])}
        added, removed = self.rules.changes(pull, current)
        path = f"/repos/{self.repository.full_name}/issues/{pull['number']}/labels"
        try:
            for label in sorted(added):
                self.create(label)
            if added:
                self.client.request("POST", path, json={"labels": sorted(added)})
            for label in sorted(removed):
                try:
                    self.client.request("DELETE", f"{path}/{quote(label, safe='')}")
                except GitHubNotFound:
                    pass  # removed by somebody meanwhile
        except MissingPermissions as error:
            raise CannotWriteLabels(f"{self.repository.full_name}#{pull['number']}") from error
        self.record(pull["number"], added, removed, (current | added) - removed)
        return added, removed

    def create(self, label: str) -> None:
        """Create a label of the rules in the repository, with its color, if it is new.

        Args:
            label: The name of the label.

        Raises:
            MissingPermissions: The installation may not create labels.
        """
        color, description = self.rules.color(label)
        try:
            self.client.request(
                "POST",
                f"/repos/{self.repository.full_name}/labels",
                json={"name": label, "color": color, "description": description},
            )
        except MissingPermissions:
            raise
        except GitHubError:
            pass  # it exists: GitHub answers 422; adding it to the pull request still works

    def record(self, number: int, added: set[str], removed: set[str], labels: set[str]) -> None:
        """Log the changes and keep the labels of the pull request.

        Args:
            number: The number of the pull request.
            added: The labels added.
            removed: The labels removed.
            labels: The labels it has now.
        """
        for label, was_added in [(label, True) for label in sorted(added)] + [
            (label, False) for label in sorted(removed)
        ]:
            rule = next((r.name for r in self.rules.rules if label in r.labels), "")
            LabelChange.objects.create(
                repository=self.repository, number=number, label=label, added=was_added, rule=rule
            )
            log.info("%s#%s %s%s", self.repository.full_name, number, "+-"[not was_added], label)
        Item.objects.filter(repository=self.repository, number=number).update(labels=sorted(labels))
