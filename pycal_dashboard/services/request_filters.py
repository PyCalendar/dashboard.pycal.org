"""Read the filters of an address, such as ``?days=30&state=open``, with clear errors."""

from pycal_dashboard.errors import InvalidDays, InvalidFilter, InvalidPageNumber


class RequestFilters:
    """The parameters of a request, checked."""

    def __init__(self, params):
        """The filters.

        Args:
            params: ``request.GET`` or a dict.
        """
        self.params = params

    def days(self, default: int = 90) -> int:
        """``days``: the period of the statistics.

        Args:
            default: Without the parameter.

        Returns:
            The days.

        Raises:
            InvalidDays: Not a whole number from 1 to 3650.

        Examples:
            >>> RequestFilters({"days": "30"}).days(), RequestFilters({}).days()
            (30, 90)
        """
        value = self.params.get("days", "")
        if value == "":
            return default
        if not value.isdigit() or not 1 <= int(value) <= 3650:
            raise InvalidDays(f"days={value!r}")
        return int(value)

    def page(self) -> int:
        """``page``: the page of a long list, from 1.

        Returns:
            The page.

        Raises:
            InvalidPageNumber: Not a positive whole number.

        Examples:
            >>> RequestFilters({"page": "2"}).page()
            2
        """
        value = self.params.get("page", "1")
        if not value.isdigit() or int(value) < 1:
            raise InvalidPageNumber(f"page={value!r}")
        return int(value)

    def choice(self, name: str, choices: tuple[str, ...], default: str) -> str:
        """A parameter with a few allowed values.

        Args:
            name: Such as ``state``.
            choices: The allowed values.
            default: Without the parameter.

        Returns:
            The value.

        Raises:
            InvalidFilter: Another value.

        Examples:
            >>> RequestFilters({"state": "closed"}).choice("state", ("open", "closed"), "open")
            'closed'
        """
        value = self.params.get(name, default) or default
        if value not in choices:
            raise InvalidFilter(f"{name}={value!r}; allowed: {', '.join(choices)}")
        return value
