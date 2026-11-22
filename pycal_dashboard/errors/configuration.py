"""Errors of the settings of the site, met by the people who run it when it starts.

The settings are environment variables, listed in :doc:`/reference/settings`.
"""

from django.utils.translation import gettext_lazy as _

from .base import DashboardError


class ConfigurationError(DashboardError):
    """A setting of the site is wrong.

    The detail names the setting. Correct it in the environment, such as in
    ``.env``, and restart the site.
    """

    title = _("A setting of the site is wrong")
    status = 500
    guide = "reference/settings.html"
    guide_title = _("Settings")


class UnknownWorkerMode(ConfigurationError):
    """``FETCH_WORKER`` is none of the modes of the background work.

    Set it to ``internal`` (a thread of the web process), ``external-http-container`` (a
    process of its own in the web container, the default of the image),
    ``external-separate-container`` (the worker service of ``docker-compose.yml``) or
    ``inline`` (for the tests).
    """

    title = _("Unknown mode of the background work")


class UnknownColor(ConfigurationError):
    """A ``COLOR_...`` setting names a color that the theme does not have.

    The detail lists the known names. Use one of them, such as
    ``COLOR_PRIMARY`` or ``COLOR_DARK_ACCENT``.
    """

    title = _("Unknown color")


class InvalidColor(ConfigurationError):
    """A ``COLOR_...`` setting is not a color.

    Write colors with ``#`` and three or six hexadecimal digits, such as
    ``#3b79aa``.
    """

    title = _("Invalid color")


class InvalidOrganizationSetting(ConfigurationError):
    """``GITHUB_ORGANIZATIONS`` contains something that is not a GitHub login.

    Write the logins of the organizations, separated by commas, such as
    ``PyCalendar``.
    """

    title = _("Invalid organization in the settings")


class FaviconNotFound(ConfigurationError):
    """The file of ``FAVICON`` does not exist.

    ``FAVICON`` is an address such as ``https://pycal.org/favicon.png``, or the
    path of a PNG, ICO or SVG file inside the container, such as
    ``/app/data/favicon.png`` in the volume of the data. See
    :doc:`/reference/settings`.
    """

    title = _("The favicon was not found")


class UnsupportedFavicon(ConfigurationError):
    """The file of ``FAVICON`` is not a PNG, ICO or SVG file.

    Browsers show these formats as icon of the page. Convert the icon and name
    the file with its extension: ``.png``, ``.ico`` or ``.svg``.
    """

    title = _("The favicon has an unsupported format")


class InvalidFooterLink(ConfigurationError):
    """An entry of ``FOOTER_LINKS`` is not ``Title=URL``.

    ``FOOTER_LINKS`` lists the extra links of the footer, separated by commas,
    each as a title, ``=`` and an address that starts with ``https://`` or
    ``http://``, such as
    ``FOOTER_LINKS=pycal.org=https://pycal.org,Blog=https://example.org/blog/``.
    Leave it empty for no extra links. See :doc:`/reference/settings`.
    """

    title = _("A link of the footer is invalid")


class ImageHostInvalid(DashboardError):
    """A host of images on the page Settings is not the name of a host.

    Give one host a line, such as ``insight.pycal.org``: without ``https://``, a path or a
    port. Its images load in texts of Markdown, over HTTPS only.
    """

    title = _("The host of images is not valid")
    status = 400
