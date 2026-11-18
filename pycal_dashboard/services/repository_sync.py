"""Read the repositories, issues and pull requests of an installation from GitHub.

Webhooks keep the dashboard up to date; this reads everything again, such as after the
installation, after the site was down, or with ``manage.py sync_repositories``.
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from pycal_dashboard.errors import DashboardError, InstallationNotAllowed
from pycal_dashboard.github.app import GitHubApp
from pycal_dashboard.github.client import GitHubClient
from pycal_dashboard.models import Installation, Repository
from pycal_dashboard.organizations import is_shown

from .item_store import ItemStore
from .labeler import PullRequestLabeler

log = logging.getLogger(__name__)


class RepositorySync:
    """Reads one installation: its repositories and their issues and pull requests."""

    def __init__(self, installation_id: int):
        """A sync of an installation.

        Args:
            installation_id: The id of the installation on GitHub.
        """
        self.installation_id = installation_id
        self.summary = {"repositories": 0, "items": 0, "labeled": 0, "errors": []}

    @classmethod
    def everything(cls) -> list[dict]:
        """Read every installation of the app that the dashboard shows.

        Returns:
            The summaries of the installations.
        """
        summaries = []
        for data in GitHubApp.app_client().pages("/app/installations"):
            if not is_shown(data["account"]["login"], settings.GITHUB_ORGANIZATIONS):
                log.info("ignored the installation on %s", data["account"]["login"])
                continue
            summaries.append(cls(data["id"]).run())
        return summaries

    def installation(self) -> Installation:
        """Store the installation, if the dashboard shows its account.

        Returns:
            The installation.

        Raises:
            InstallationNotAllowed: The account is not in ``GITHUB_ORGANIZATIONS``.
        """
        data = GitHubApp.installation(self.installation_id)
        login = data["account"]["login"]
        if not is_shown(login, settings.GITHUB_ORGANIZATIONS):
            raise InstallationNotAllowed(login)
        installation, _ = Installation.objects.update_or_create(
            github_id=self.installation_id,
            defaults={
                "account_login": login,
                "account_type": data["account"].get("type", "Organization"),
                "permissions": data.get("permissions", {}),
                "suspended": bool(data.get("suspended_at")),
            },
        )
        return installation

    def run(self) -> dict:
        """Read the installation.

        Returns:
            How many repositories and items were read and pull requests labeled, and the
            errors of single repositories or pull requests.
        """
        installation = self.installation()
        client = GitHubApp.for_installation(self.installation_id)
        found = client.pages("/installation/repositories", key="repositories")
        kept = []
        for data in found:
            repository = ItemStore.repository(data, installation)
            kept.append(repository.pk)
            self.summary["repositories"] += 1
            if repository.private or repository.archived:
                continue  # never shown; archived ones do not change
            try:
                self.items(client, repository)
            except DashboardError as error:
                log.warning("sync of %s: %s %s", repository.full_name, error.code, error)
                self.summary["errors"].append(f"{repository.full_name}: {error.code}: {error}")
        # repositories removed from the installation are not shown any more
        installation.repositories.exclude(pk__in=kept).update(installation=None)
        return self.summary

    def items(self, client: GitHubClient, repository: Repository) -> None:
        """Read the issues and pull requests changed since the last sync; label the open pulls.

        Args:
            client: A client of the installation.
            repository: The repository.
        """
        started = timezone.now()
        params = {"state": "all"}
        if repository.synced_at:
            params["since"] = (repository.synced_at - timedelta(minutes=5)).isoformat()
        for data in client.pages(f"/repos/{repository.full_name}/issues", **params):
            ItemStore.item(repository, data)
            self.summary["items"] += 1
        labeler = PullRequestLabeler(client, repository)
        for pull in client.pages(f"/repos/{repository.full_name}/pulls", state="open"):
            ItemStore.item(repository, pull)
            try:
                added, removed = labeler.label(pull)
            except DashboardError as error:
                self.summary["errors"].append(
                    f"{repository.full_name}#{pull['number']}: {error.code}: {error}"
                )
                continue
            self.summary["labeled"] += bool(added or removed)
        repository.synced_at = started
        repository.save(update_fields=["synced_at"])
