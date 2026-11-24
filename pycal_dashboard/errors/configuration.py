"""Errors of the settings of the site, met by the people who run it when it starts.

The settings are environment variables, listed in :doc:`/reference/settings`.
"""

from django.utils.translation import gettext_lazy as _

from .base import DashboardError


class ConfigurationError(DashboardError):
    """A setting of the dashboard is wrong.

    Resolve:
        Correct the setting that the detail names in the environment, such as in ``.env``, and
        restart the dashboard.

    Context:
        :doc:`/reference/settings` describes every setting.
    """

    title = _("A setting of the site is wrong")
    status = 500
    guide = "reference/settings.html"
    guide_title = _("Settings")


class UnknownWorkerMode(ConfigurationError):
    """``FETCH_WORKER`` is none of the modes of the background work.

    Resolve:
        Set ``FETCH_WORKER`` to one of these modes and restart the dashboard:

        - ``internal``: a thread of the web process,
        - ``external-http-container``: a process of its own in the web container, the default of
          the image,
        - ``external-separate-container``: the worker service of ``docker-compose.yml``, or
        - ``inline``: for the tests.
    """

    title = _("Unknown mode of the background work")


class UnknownColor(ConfigurationError):
    """A ``COLOR_...`` setting names a color that the theme does not have.

    Resolve:
        Rename the setting to one of the colors that the detail lists, such as ``COLOR_PRIMARY``
        or ``COLOR_DARK_ACCENT``, and restart the dashboard.

    Context:
        The detail lists the known names in lower case, without ``COLOR_``.
        ``COLOR_DARK_...`` sets the same colors for the dark theme.
    """

    title = _("Unknown color")


class InvalidColor(ConfigurationError):
    """A ``COLOR_...`` setting is not a color.

    Resolve:
        Write the color with ``#`` and three or six hexadecimal digits, such as ``#3b79aa``, and
        restart the dashboard.

    Note:
        The detail names the setting and its value.
    """

    title = _("Invalid color")


class InvalidOrganizationSetting(ConfigurationError):
    """``GITHUB_ORGANIZATIONS`` contains something that is not a GitHub login.

    Resolve:
        Write the logins of the organizations, separated by commas, such as ``PyCalendar``, and
        restart the dashboard.

    Context:
        A login has at most 39 letters, digits and hyphens, and neither starts nor ends with a
        hyphen.

    Note:
        The detail names the login.
    """

    title = _("Invalid organization in the settings")


class FaviconNotFound(ConfigurationError):
    """The file of ``FAVICON`` does not exist.

    Resolve:
        Set ``FAVICON`` to one of these and restart the dashboard:

        - an address, such as ``https://pycal.org/favicon.png``,
        - the path of a PNG, ICO or SVG file inside the container, such as
          ``/app/data/favicon.png`` in the volume of the data, or
        - nothing, for the icon of pycal.

    Context:
        See :doc:`/reference/settings`.

    Note:
        The detail names the path.
    """

    title = _("The favicon was not found")


class UnsupportedFavicon(ConfigurationError):
    """The file of ``FAVICON`` is not a PNG, ICO or SVG file.

    Resolve:
        Convert the icon and name the file with its extension: ``.png``, ``.ico`` or ``.svg``.

    Context:
        Browsers show these formats as icon of the page. The dashboard tells the format by the
        extension of the file.
    """

    title = _("The favicon has an unsupported format")


class InvalidFooterLink(ConfigurationError):
    """An entry of ``FOOTER_LINKS`` is not ``Title=URL``.

    This happens when an entry has no title, or its address does not start with ``https://`` or
    ``http://``.

    Resolve:
        - Write each entry as a title, ``=`` and an address that starts with ``https://`` or
          ``http://``, separated by commas, such as
          ``FOOTER_LINKS=pycal.org=https://pycal.org,Blog=https://example.org/blog/``.
        - For no extra links, leave it empty.

        Then restart the dashboard.

    Context:
        ``FOOTER_LINKS`` lists the extra links of the footer. See :doc:`/reference/settings`.

    Note:
        The detail names the entry.
    """

    title = _("A link of the footer is invalid")


class ImageHostInvalid(DashboardError):
    """A host of images on the page *Settings* is not the name of a host, or there are too many.

    This happens when:

    - a line has a path, a port or ``http://``,
    - a ``*.`` has only one label after it, such as ``*.org``, or
    - there are more than 50 hosts.

    Resolve:
        - Give one host a line, such as ``insight.pycal.org``, without a path or a port.
          ``*.pycal.org`` stands for all hosts below pycal.org.
        - When there are more than 50, remove some.

    Context:
        The images of these hosts load in texts of Markdown, over HTTPS only. ``https://`` and a
        slash at the end of a line are taken away. ``*.pycal.org`` does not include pycal.org
        itself.

    Note:
        The detail names the line.
    """

    title = _("The host of images is not valid")
    status = 400
