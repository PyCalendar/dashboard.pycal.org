"""Record the installations of the GitHub App with their permissions, from GitHub's answers."""

from pycal_dashboard.models import Installation


class InstallationStore:
    """Keep what GitHub says about an installation: its account, permissions and events."""

    @staticmethod
    def record(data: dict, sender: dict | None = None, removed: bool = False) -> Installation:
        """Record an installation as a webhook or ``GET /app/installations`` describes it.

        Parameters:
            data: The installation, with ``id``, ``account``, ``permissions`` and ``events``.
            sender: The person who installed or changed it, from a webhook; they get the
                emails about it.
            removed: Whether the app was uninstalled.

        Returns:
            The installation.
        """
        account = data.get("account") or {}
        installation, _created = Installation.objects.get_or_create(
            github_id=data["id"], defaults={"account_login": account.get("login", "")}
        )
        installation.account_login = account.get("login") or installation.account_login
        installation.account_type = account.get("type") or installation.account_type
        if "permissions" in data:
            installation.permissions = data["permissions"] or {}
        if "events" in data:
            installation.events = data["events"] or []
        installation.suspended = bool(data.get("suspended_at"))
        installation.removed = removed
        people = set(installation.admin_github_ids)
        if sender and sender.get("id") and sender.get("type", "User") == "User":
            people.add(sender["id"])
        if account.get("type") == "User" and account.get("id"):
            people.add(account["id"])  # a person who installed it on their own account
        installation.admin_github_ids = sorted(people)
        installation.save()
        return installation
