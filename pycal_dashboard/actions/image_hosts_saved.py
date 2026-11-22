"""The administrators changed the hosts whose images texts of Markdown show."""

from .action import Action


class ImageHostsSaved(Action):
    """The hosts of images of the page Settings were saved."""

    kind = "settings"

    def __init__(self, hosts: list[str]):
        """The saved hosts.

        Parameters:
            hosts: The hosts, such as ``insight.pycal.org``.
        """
        self.hosts = hosts

    def text(self) -> str:
        """Which hosts are allowed now.

        Examples:
            >>> ImageHostsSaved(["insight.pycal.org"]).text()
            'The images of these hosts load in Markdown: insight.pycal.org'
            >>> ImageHostsSaved([]).text()
            'The images of no other host load in Markdown'
        """
        if not self.hosts:
            return "The images of no other host load in Markdown"
        return f"The images of these hosts load in Markdown: {', '.join(self.hosts)}"
