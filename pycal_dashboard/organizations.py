"""The organizations that the dashboard shows: ``GITHUB_ORGANIZATIONS``."""

import re

from pycal_dashboard.errors import InvalidOrganizationSetting

LOGIN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?")


def parse_organizations(value: str) -> list[str]:
    """The logins of the setting, checked.

    Args:
        value: The logins, separated by commas.

    Returns:
        The logins in lower case; an empty list allows every account.

    Raises:
        InvalidOrganizationSetting: A login is not a GitHub login.

    Examples:
        >>> parse_organizations("PyCalendar, collective")
        ['pycalendar', 'collective']
        >>> parse_organizations("")
        []
    """
    logins = [login.strip() for login in value.split(",") if login.strip()]
    for login in logins:
        if not LOGIN.fullmatch(login):
            raise InvalidOrganizationSetting(f"GITHUB_ORGANIZATIONS: {login!r}")
    return [login.lower() for login in logins]


def is_shown(login: str, organizations: list[str]) -> bool:
    """Whether the dashboard shows an account.

    Args:
        login: The login of the account of an installation.
        organizations: The setting ``GITHUB_ORGANIZATIONS``.

    Returns:
        True if it is one of them, or if the setting allows every account.

    Examples:
        >>> is_shown("PyCalendar", ["pycalendar"]), is_shown("other", ["pycalendar"])
        (True, False)
    """
    return not organizations or login.lower() in organizations
