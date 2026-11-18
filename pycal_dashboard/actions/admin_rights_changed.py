"""The rights of the Django admin of a person changed, as ``SITE_ADMINS`` says."""

from .action import Action


class AdminRightsChanged(Action):
    """A person got or lost the rights of the Django admin."""

    kind = "admin-rights"

    def __init__(self, login: str, admin: bool):
        """The change of the rights.

        Args:
            login: The GitHub handle of the person.
            admin: Whether the person is an administrator now.
        """
        self.login = login
        self.admin = admin

    def text(self) -> str:
        """What changed and why.

        Examples:
            >>> AdminRightsChanged("alice", True).text()
            '@alice gets the rights of the Django admin: the handle is in SITE_ADMINS'
            >>> AdminRightsChanged("bob", False).text()
            '@bob loses the rights of the Django admin: the handle is not in SITE_ADMINS'
        """
        if self.admin:
            return (
                f"@{self.login} gets the rights of the Django admin: the handle is in SITE_ADMINS"
            )
        return (
            f"@{self.login} loses the rights of the Django admin: the handle is not in SITE_ADMINS"
        )
