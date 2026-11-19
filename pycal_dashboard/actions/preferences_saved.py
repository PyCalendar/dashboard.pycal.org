"""A person saved their preferences."""

from .action import Action


class PreferencesSaved(Action):
    """The preferences of a person changed: the language and the colors."""

    kind = "preferences"

    def __init__(self, login: str, language: str, theme: str, email_permissions: bool = True):
        """The saved preferences.

        Parameters:
            login: The GitHub handle of the person.
            language: The language, such as ``de``; "" for the language of the browser.
            theme: The colors: ``auto``, ``light`` or ``dark``; "" for the choice of the menu.
            email_permissions: Whether the person wants the emails about the permissions of
                their installations.
        """
        self.login = login
        self.language = language
        self.theme = theme
        self.email_permissions = email_permissions

    def text(self) -> str:
        """What the person chose.

        Examples:
            >>> PreferencesSaved("alice", "de", "dark").text()
            '@alice saved the preferences: language de, colors dark, emails about permissions'
            >>> PreferencesSaved("bob", "", "", False).text()
            '@bob saved the preferences: language of the browser, colors of the menu, no emails'
        """
        language = f"language {self.language}" if self.language else "language of the browser"
        colors = f"colors {self.theme}" if self.theme else "colors of the menu"
        emails = "emails about permissions" if self.email_permissions else "no emails"
        return f"@{self.login} saved the preferences: {language}, {colors}, {emails}"
