"""A person saved their preferences."""

from .action import Action


class PreferencesSaved(Action):
    """The preferences of a person changed: the language and the colors."""

    kind = "preferences"

    def __init__(self, login: str, language: str, theme: str):
        """The saved preferences.

        Args:
            login: The GitHub handle of the person.
            language: The language, such as ``de``; "" for the language of the browser.
            theme: The colors: ``auto``, ``light`` or ``dark``; "" for the choice of the menu.
        """
        self.login = login
        self.language = language
        self.theme = theme

    def text(self) -> str:
        """What the person chose.

        Examples:
            >>> PreferencesSaved("alice", "de", "dark").text()
            '@alice saved the preferences: language de, colors dark'
            >>> PreferencesSaved("bob", "", "").text()
            '@bob saved the preferences: language of the browser, colors of the menu'
        """
        language = f"language {self.language}" if self.language else "language of the browser"
        colors = f"colors {self.theme}" if self.theme else "colors of the menu"
        return f"@{self.login} saved the preferences: {language}, {colors}"
