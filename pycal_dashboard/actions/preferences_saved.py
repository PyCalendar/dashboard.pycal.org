"""A person saved their preferences."""

from .action import Action


class PreferencesSaved(Action):
    """The preferences of a person changed; they stay private, so only their names are logged."""

    kind = "preferences"

    def __init__(self, login: str, email_notifications: bool):
        """The saved preferences.

        Args:
            login: The GitHub handle of the person.
            email_notifications: Whether the person wants emails.
        """
        self.login = login
        self.email_notifications = email_notifications

    def text(self) -> str:
        """What the person chose.

        Examples:
            >>> PreferencesSaved("alice", False).text()
            '@alice saved the preferences: no emails about the account and the site'
        """
        choice = "emails" if self.email_notifications else "no emails"
        return f"@{self.login} saved the preferences: {choice} about the account and the site"
