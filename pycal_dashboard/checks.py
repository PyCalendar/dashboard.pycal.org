"""The system checks of the settings: ``manage.py check`` and every start."""

from pathlib import Path

from django.conf import settings
from django.core.checks import Error, register

from .errors import FaviconNotFound, UnsupportedFavicon

FAVICON_TYPES = {".png": "image/png", ".ico": "image/x-icon", ".svg": "image/svg+xml"}


def is_url(value: str) -> bool:
    """Whether the icon is an address on the web, not a file.

    Args:
        value: The value of ``FAVICON``.

    Returns:
        True for ``https://`` and ``http://``.

    Examples:
        >>> is_url("https://pycal.org/favicon.png"), is_url("/app/data/favicon.png")
        (True, False)
    """
    return value.startswith(("https://", "http://"))


@register()
def check_favicon(app_configs=None, **kwargs) -> list:
    """``FAVICON`` is an address, or a PNG, ICO or SVG file that exists.

    Args:
        app_configs: The apps to check.
        **kwargs: More of Django.

    Returns:
        The errors.
    """
    path = settings.FAVICON
    if not path or is_url(path):
        return []
    if Path(path).suffix.lower() not in FAVICON_TYPES:
        error = UnsupportedFavicon
        return [Error(error.title, hint=path, id="pycal_dashboard.E002", obj=error.docs_url())]
    if not Path(path).is_file():
        error = FaviconNotFound
        return [Error(error.title, hint=path, id="pycal_dashboard.E001", obj=error.docs_url())]
    return []
