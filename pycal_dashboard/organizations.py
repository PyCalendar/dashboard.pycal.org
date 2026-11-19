"""The organizations of the community of the site: ``GITHUB_ORGANIZATIONS``."""

import re

from pycal_dashboard.errors import InvalidOrganizationSetting

LOGIN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?")


def parse_organizations(value: str) -> list[str]:
    """The logins of the setting, checked.

    Parameters:
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
