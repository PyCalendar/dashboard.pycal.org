"""The GitHub App as installed on a repository: its installation and a client with its token."""

from django.conf import settings

from pycal_dashboard.errors import GitHubNotFound

from .app_check import AppCheck
from .client import GitHubClient


class InstallationToken:
    """Requests to GitHub as an installation of the GitHub App.

    An installation reads the repositories it is installed on, also private ones, with the
    permissions its owners accepted.
    """

    @staticmethod
    def app_configured() -> bool:
        """Whether the site has a GitHub App that can speak for itself."""
        return bool(settings.GITHUB_APP_ID and settings.GITHUB_APP_PRIVATE_KEY)

    @classmethod
    def installation_of(cls, full_name: str) -> dict | None:
        """The installation of the GitHub App on a repository.

        Parameters:
            full_name: The repository, such as ``collective/icalendar``.

        Returns:
            The installation as GitHub describes it, None if the app is not installed on it or
            the site has no app.
        """
        if not cls.app_configured():
            return None
        try:
            return (
                GitHubClient(AppCheck.token()).request("GET", f"/repos/{full_name}/installation")
            ).json()
        except GitHubNotFound:
            return None

    @staticmethod
    def client(installation_id: int) -> GitHubClient:
        """A client with a token of an installation, valid for an hour.

        Parameters:
            installation_id: The id of the installation on GitHub.

        Returns:
            The client.
        """
        answer = GitHubClient(AppCheck.token()).request(
            "POST", f"/app/installations/{installation_id}/access_tokens"
        )
        return GitHubClient(answer.json()["token"])
