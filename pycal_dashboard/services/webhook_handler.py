"""Handle the webhooks of the GitHub App.

The site records its installations with their permissions and tells the people of an
installation when it lacks some. Other webhooks are logged only: the site keeps no other data of
GitHub and writes nothing to GitHub. The automation is designed later.
"""

from .installation_store import InstallationStore
from .permission_notice import PermissionNotice

# the events whose payload describes the whole installation, with its permissions
INSTALLATION_EVENTS = {"installation", "installation_repositories"}


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

    @property
    def repository_name(self) -> str:
        """The full name of the repository of the webhook, or ""."""
        repository = self.payload.get("repository")
        return repository.get("full_name", "") if isinstance(repository, dict) else ""

    def handle(self) -> str:
        """Do what the webhook asks for.

        Returns:
            What was done, for the log of the deliveries.

        Examples:
            >>> WebhookHandler("ping", {"zen": "Keep it logically awesome."}).handle()
            'pong'
            >>> WebhookHandler("pull_request", {"action": "opened"}).handle()
            'received: no automation yet'
        """
        if self.event == "ping":
            return "pong"  # GitHub checks the webhook after the app was created
        installation = self.payload.get("installation")
        if (
            self.event in INSTALLATION_EVENTS
            and isinstance(installation, dict)
            and "id" in installation
        ):
            return self.record(installation)
        return "received: no automation yet"

    def record(self, data: dict) -> str:
        """Record the installation and tell its people if it lacks permissions.

        Args:
            data: The installation of the payload.

        Returns:
            What was done.
        """
        installation = InstallationStore.record(
            data, self.payload.get("sender"), removed=self.action == "deleted"
        )
        sent = PermissionNotice(installation).send_if_needed()
        lacks = installation.missing_permissions
        done = f"recorded the installation on {installation.account_login}"
        if installation.removed:
            return f"{done}: removed"
        if lacks:
            done += f"; it lacks {', '.join(f'{k}:{v}' for k, v in sorted(lacks.items()))}"
        return done + (f"; {sent} email{'s' if sent != 1 else ''}" if sent else "")
