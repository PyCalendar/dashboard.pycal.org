"""Handle the webhooks of the GitHub App.

The site receives the webhooks and logs them, but does nothing with them yet: it keeps no
data of GitHub and writes nothing to GitHub. The automation is designed later.
"""


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
        """Say what the site did with the webhook.

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
        return "received: no automation yet"
