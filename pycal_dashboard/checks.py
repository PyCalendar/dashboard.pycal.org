"""The system checks of the settings: ``manage.py check`` and every start."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.checks import Error, register

from .errors import FaviconNotFound, UnknownWorkerMode, UnsupportedFavicon
from .worker_mode import MODES

FAVICON_TYPES = {".png": "image/png", ".ico": "image/x-icon", ".svg": "image/svg+xml"}


def is_url(value: str) -> bool:
    """Whether the icon is an address on the web, not a file.

    Parameters:
        value: The value of ``FAVICON``.

    Returns:
        True for ``https://`` and ``http://``.

    Examples:
        >>> is_url("https://pycal.org/favicon.png"), is_url("/app/data/favicon.png")
        (True, False)
    """
    return value.startswith(("https://", "http://"))


@register()
def check_favicon(app_configs: list | None | None = None, **kwargs: Any) -> list:
    """``FAVICON`` is an address, or a PNG, ICO or SVG file that exists.

    Parameters:
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


@register()
def check_worker_mode(app_configs: list | None = None, **kwargs: Any) -> list:
    """``FETCH_WORKER`` is one of the modes of the background work.

    Parameters:
        app_configs: The apps to check.
        **kwargs: More of Django.

    Returns:
        The errors.
    """
    if settings.FETCH_WORKER in MODES:
        return []
    error = UnknownWorkerMode
    hint = f"FETCH_WORKER={settings.FETCH_WORKER!r}; use one of: {', '.join(MODES)}"
    return [Error(error.title, hint=hint, id="pycal_dashboard.E003", obj=error.docs_url())]
