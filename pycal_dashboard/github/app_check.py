"""What GitHub knows about the GitHub App of the site, compared with what the site needs.

The site reads ``GET /app`` with the token of the app itself, a JSON Web Token signed with its
private key. It keeps nothing of it: the check names the permissions and the events that the
app lacks, on the page *Register the GitHub App* and with ``manage.py check_app``.
"""

import time
from dataclasses import dataclass

import jwt
from django.conf import settings

from pycal_dashboard.errors import GitHubAppNotConfigured, InvalidPrivateKey

from . import permissions
from .client import GitHubClient


@dataclass(frozen=True)
class AppCheck:
    """The app as GitHub describes it, and what it lacks.

    Attributes:
        app: The answer of ``GET /app``.
    """

    app: dict

    @staticmethod
    def token() -> str:
        """The token with which the app speaks for itself, valid for nine minutes.

        Returns:
            The JSON Web Token.

        Raises:
            GitHubAppNotConfigured: There is no app.
            InvalidPrivateKey: The key cannot sign.
        """
        if not (settings.GITHUB_APP_ID and settings.GITHUB_APP_PRIVATE_KEY):
            raise GitHubAppNotConfigured("GITHUB_APP_ID, GITHUB_APP_PRIVATE_KEY")
        now = int(time.time())
        payload = {"iat": now - 60, "exp": now + 540, "iss": str(settings.GITHUB_APP_ID)}
        try:
            return jwt.encode(payload, settings.GITHUB_APP_PRIVATE_KEY, algorithm="RS256")
        except (ValueError, TypeError, jwt.PyJWTError) as error:
            raise InvalidPrivateKey(str(error)) from error

    @classmethod
    def read(cls) -> "AppCheck":
        """Read the app from GitHub.

        Returns:
            The check.
        """
        return cls(GitHubClient(cls.token()).request("GET", "/app").json())

    @property
    def missing_permissions(self) -> dict[str, str]:
        """The permissions of :data:`~pycal_dashboard.github.permissions.REQUIRED` it lacks."""
        return permissions.missing(self.app.get("permissions") or {})

    @property
    def missing_events(self) -> list[str]:
        """The events of :data:`~pycal_dashboard.github.permissions.EVENTS` it does not receive.

        Examples:
            >>> AppCheck({"events": ["issues", "pull_request"]}).missing_events
            ['issue_comment', 'pull_request_review', 'repository']
        """
        received = self.app.get("events") or []
        return [event for event in permissions.EVENTS if event not in received]

    @property
    def complete(self) -> bool:
        """Whether the app has every permission and event the site needs."""
        return not self.missing_permissions and not self.missing_events

    @property
    def settings_url(self) -> str:
        """The page of the permissions and events of the app on GitHub, for its owner.

        Examples:
            >>> owner = {"login": "O", "type": "Organization"}
            >>> AppCheck({"slug": "a", "owner": owner}).settings_url
            'https://github.com/organizations/O/settings/apps/a/permissions'
            >>> AppCheck({"slug": "a", "owner": {"login": "me", "type": "User"}}).settings_url
            'https://github.com/settings/apps/a/permissions'
        """
        owner = self.app.get("owner") or {}
        slug = self.app.get("slug", "")
        if owner.get("type") == "Organization":
            return f"https://github.com/organizations/{owner['login']}/settings/apps/{slug}/permissions"
        return f"https://github.com/settings/apps/{slug}/permissions"

    def describe(self) -> str:
        """What the app lacks, in one line.

        Returns:
            Such as ``the app lacks issues: read and does not receive the events
            repository: change them on <settings_url>``; "" if it lacks nothing.
        """
        parts = []
        if self.missing_permissions:
            needed = ", ".join(f"{k}: {v}" for k, v in self.missing_permissions.items())
            parts.append(f"lacks the permissions {needed}")
        if self.missing_events:
            parts.append(f"does not receive the events {', '.join(self.missing_events)}")
        if not parts:
            return ""
        return f"The GitHub App {' and '.join(parts)}: change them on {self.settings_url}"
