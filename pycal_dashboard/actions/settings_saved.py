"""Settings of the site were saved, such as the OAuth app or the GitHub App."""

from .action import Action


class SettingsSaved(Action):
    """Settings were written into ``DATA_DIR/.env``; the values are not logged."""

    kind = "settings"

    def __init__(self, names: list[str], reason: str):
        """The saved settings.

        Parameters:
            names: The names of the settings, such as ``GITHUB_OAUTH_CLIENT_ID``.
            reason: Why, such as ``the OAuth app for signing in was entered``.
        """
        self.names = names
        self.reason = reason

    def text(self) -> str:
        """Which settings and why, without their values.

        Examples:
            >>> SettingsSaved(["A", "B"], "a test").text()
            'Saved A, B in DATA_DIR/.env: a test'
        """
        return f"Saved {', '.join(self.names)} in DATA_DIR/.env: {self.reason}"
