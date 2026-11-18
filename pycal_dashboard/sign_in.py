"""The GitHub client that signs people in.

An OAuth app of ``GITHUB_OAUTH_CLIENT_ID`` and ``GITHUB_OAUTH_SECRET`` if they are set;
else the client of the GitHub App (``GITHUB_CLIENT_ID`` and ``GITHUB_SECRET``), which the
registration of the app stores. So people can sign in as soon as the app is registered.
"""

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class SignIn:
    """The client id and secret for signing in, and where they come from."""

    client_id: str = ""
    secret: str = ""
    source: str = ""  # "oauth-app", "github-app" or "" without a client

    @classmethod
    def from_environment(cls, environ: Mapping[str, str]) -> "SignIn":
        """The client of the environment.

        Args:
            environ: The environment, such as ``os.environ``.

        Returns:
            The client; empty without one.

        Examples:
            >>> SignIn.from_environment({"GITHUB_CLIENT_ID": "a", "GITHUB_SECRET": "b"}).source
            'github-app'
            >>> SignIn.from_environment({"GITHUB_OAUTH_CLIENT_ID": "o", "GITHUB_CLIENT_ID": "a"})
            SignIn(client_id='o', secret='', source='oauth-app')
            >>> SignIn.from_environment({}).configured
            False
        """
        if environ.get("GITHUB_OAUTH_CLIENT_ID"):
            return cls(
                environ["GITHUB_OAUTH_CLIENT_ID"],
                environ.get("GITHUB_OAUTH_SECRET", ""),
                "oauth-app",
            )
        if environ.get("GITHUB_CLIENT_ID"):
            return cls(environ["GITHUB_CLIENT_ID"], environ.get("GITHUB_SECRET", ""), "github-app")
        return cls()

    @property
    def configured(self) -> bool:
        """Whether people can sign in."""
        return bool(self.client_id)

    def providers(self) -> dict:
        """``SOCIALACCOUNT_PROVIDERS`` of allauth with this client.

        Returns:
            The settings of the provider ``github``: the identity and the email addresses.
        """
        github: dict = {"SCOPE": ["user:email"]}
        if self.configured:
            github["APP"] = {"client_id": self.client_id, "secret": self.secret}
        return {"github": github}
