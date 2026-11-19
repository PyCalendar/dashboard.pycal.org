"""The OAuth app that signs people in: ``GITHUB_OAUTH_CLIENT_ID`` and ``GITHUB_OAUTH_SECRET``.

People sign in with a separate OAuth app, as on sign.pycal.org, not with the GitHub App:
GitHub then only tells the site who they are and their email addresses, read only, and never
asks to let the site act on their behalf. The people who run the site enter it on
``/setup/oauth-app/``, which keeps it in ``DATA_DIR/.env``, or set it in the environment.
"""

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class SignIn:
    """The client id and secret of the OAuth app."""

    client_id: str = ""
    secret: str = ""

    @classmethod
    def from_environment(cls, environ: Mapping[str, str]) -> "SignIn":
        """The OAuth app of the environment.

        Args:
            environ: The environment, such as ``os.environ``.

        Returns:
            The OAuth app; empty without one.

        Examples:
            >>> SignIn.from_environment({"GITHUB_OAUTH_CLIENT_ID": "o", "GITHUB_OAUTH_SECRET": "s"})
            SignIn(client_id='o', secret='s')
            >>> SignIn.from_environment({"GITHUB_CLIENT_ID": "of the GitHub App"}).configured
            False
        """
        return cls(
            environ.get("GITHUB_OAUTH_CLIENT_ID", ""), environ.get("GITHUB_OAUTH_SECRET", "")
        )

    @property
    def configured(self) -> bool:
        """Whether people can sign in."""
        return bool(self.client_id)

    def providers(self) -> dict:
        """``SOCIALACCOUNT_PROVIDERS`` of allauth with this OAuth app.

        Returns:
            The settings of the provider ``github``: the identity, the email addresses and the
            organizations.
        """
        # read only: the identity, the email addresses and the organizations of the person, whose
        # repositories they add to projects
        github: dict = {"SCOPE": ["user:email", "read:org"]}
        if self.configured:
            github["APP"] = {"client_id": self.client_id, "secret": self.secret}
        return {"github": github}
