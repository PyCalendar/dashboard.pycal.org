"""The slug of a project in an address: letters, digits, hyphens and ``~``, in any case.

The page then leads to the address in lower case, or to the current one for an old slug.
"""


class ProjectSlugConverter:
    """The part ``<project_slug:slug>`` of the addresses of projects."""

    regex = r"[A-Za-z0-9~-]{1,80}"

    def to_python(self, value: str) -> str:
        """The slug, as written in the address.

        Parameters:
            value: The part of the address.

        Returns:
            The same text.
        """
        return value

    def to_url(self, value: str) -> str:
        """The part of the address of a slug.

        Parameters:
            value: The slug.

        Returns:
            The same text.
        """
        return value
