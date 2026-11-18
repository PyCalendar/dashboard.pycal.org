"""Errors of the settings of the site, met by the people who run it when it starts.

The settings are environment variables, listed in :doc:`/reference/settings`.
"""

from .base import DashboardError


class ConfigurationError(DashboardError):
    """A setting of the site is wrong.

    The detail names the setting. Correct it in the environment, such as in
    ``.env``, and restart the site.
    """

    title = "A setting of the site is wrong"
    status = 500
    guide = "reference/settings.html"
    guide_title = "Settings"


class UnknownColor(ConfigurationError):
    """A ``COLOR_...`` setting names a color that the theme does not have.

    The detail lists the known names. Use one of them, such as
    ``COLOR_PRIMARY`` or ``COLOR_DARK_ACCENT``.
    """

    title = "Unknown color"


class InvalidColor(ConfigurationError):
    """A ``COLOR_...`` setting is not a color.

    Write colors with ``#`` and three or six hexadecimal digits, such as
    ``#3b79aa``.
    """

    title = "Invalid color"


class InvalidOrganizationSetting(ConfigurationError):
    """``GITHUB_ORGANIZATIONS`` contains something that is not a GitHub login.

    Write the logins of the organizations, separated by commas, such as
    ``PyCalendar``.
    """

    title = "Invalid organization in the settings"
