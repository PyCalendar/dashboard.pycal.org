"""Handle the webhooks of the GitHub App: keep the dashboard up to date.

The site only reads: it writes nothing to GitHub.
"""

import logging

from django.conf import settings

from pycal_dashboard.errors import WebhookPayloadIncomplete
from pycal_dashboard.models import Installation, Item, Repository
from pycal_dashboard.organizations import is_shown

from .item_store import ItemStore
from .repository_sync import RepositorySync

log = logging.getLogger(__name__)


class WebhookHandler:
    """What the site does with one webhook."""

    def __init__(self, event: str, payload: dict):
        """A webhook.

        Args:
            event: The header ``X-GitHub-Event``, such as ``pull_request``.
            payload: The JSON of the webhook.
        """
        self.event = event
        self.payload = payload
        self.action = str(payload.get("action", ""))

    def part(self, name: str) -> dict:
        """A part of the payload that the event always has.

        Args:
            name: Such as ``repository`` or ``pull_request``.

        Returns:
            The part.

        Raises:
            WebhookPayloadIncomplete: It is missing.
        """
        found = self.payload.get(name)
        if not isinstance(found, dict):
            raise WebhookPayloadIncomplete(f"{self.event}: {name}")
        return found

    @property
    def repository_name(self) -> str:
        """The full name of the repository of the webhook, or ""."""
        repository = self.payload.get("repository")
        return repository.get("full_name", "") if isinstance(repository, dict) else ""

    def shown(self) -> bool:
        """Whether the webhook is about an account that the dashboard shows.

        Returns:
            True for the organizations of ``GITHUB_ORGANIZATIONS``.
        """
        account = (self.payload.get("installation") or {}).get("account") or (
            self.payload.get("repository") or {}
        ).get("owner")
        if not isinstance(account, dict) or "login" not in account:
            return True  # nothing names an account, such as ping
        return is_shown(account["login"], settings.GITHUB_ORGANIZATIONS)

    def handle(self) -> str:
        """Do what the webhook asks for.

        Returns:
            What was done, for the log of the deliveries; it starts with ``ignored`` if
            nothing was done.
        """
        if not self.shown():
            return "ignored: the account is not in GITHUB_ORGANIZATIONS"
        method = getattr(self, f"on_{self.event}", None)
        if method is None:
            return f"ignored: the event {self.event}"
        return method()

    def on_ping(self) -> str:
        """GitHub checks the webhook after the app was created.

        Returns:
            ``pong``.
        """
        return "pong"

    def on_installation(self) -> str:
        """The app was installed, removed, suspended or got new permissions.

        Returns:
            What was done.
        """
        installation_id = self.part("installation")["id"]
        if self.action == "deleted":
            Installation.objects.filter(github_id=installation_id).delete()
            return f"removed the installation {installation_id}"
        summary = RepositorySync(installation_id).run()
        return f"read the installation {installation_id}: {summary['repositories']} repositories"

    def on_installation_repositories(self) -> str:
        """Repositories were added to or removed from the installation.

        Returns:
            What was done.
        """
        return self.on_installation()

    def repository(self) -> Repository:
        """Store the repository of the webhook.

        Returns:
            The repository.
        """
        installation = Installation.objects.filter(
            github_id=(self.payload.get("installation") or {}).get("id")
        ).first()
        return ItemStore.repository(self.part("repository"), installation)

    def on_repository(self) -> str:
        """A repository was renamed, transferred, archived, made private or public or deleted.

        Returns:
            What was done.
        """
        if self.action == "deleted":
            Repository.objects.filter(github_id=self.part("repository")["id"]).delete()
            return f"removed {self.repository_name}"
        repository = self.repository()
        return f"updated {repository.full_name}"

    def on_issues(self) -> str:
        """An issue was opened, closed, labeled, edited ...

        Returns:
            What was done.
        """
        repository = self.repository()
        if self.action == "deleted":
            Item.objects.filter(repository=repository, number=self.part("issue")["number"]).delete()
            return f"removed {repository.full_name}#{self.part('issue')['number']}"
        item = ItemStore.item(repository, self.part("issue"))
        return f"updated {item}"

    def on_issue_comment(self) -> str:
        """Somebody commented an issue or a pull request: the number of comments changed.

        Returns:
            What was done.
        """
        item = ItemStore.item(self.repository(), self.part("issue"))
        return f"updated {item}"

    def on_pull_request(self) -> str:
        """A pull request was opened, pushed to, closed ...: store it.

        Returns:
            What was done.
        """
        item = ItemStore.item(self.repository(), self.part("pull_request"))
        return f"updated {item}"

    def on_pull_request_review(self) -> str:
        """A pull request was reviewed: its requested reviewers changed.

        Returns:
            What was done.
        """
        item = ItemStore.item(self.repository(), self.part("pull_request"))
        return f"updated {item}"
