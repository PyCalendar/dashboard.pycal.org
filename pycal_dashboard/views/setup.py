"""GitHub returns here after the app was installed or its installation changed."""

from __future__ import annotations

from django.http import HttpRequest
from django.shortcuts import render

from pycal_dashboard.errors import InvalidInstallationId
from pycal_dashboard.middleware import error_page


def installed(request: HttpRequest):
    """Confirm the installation; the site reads nothing of it from GitHub.

    Parameters:
        request: The request, with ``installation_id`` and ``setup_action`` of GitHub.

    Returns:
        The page, or the page of the error.
    """
    value = request.GET.get("installation_id", "")
    if not value.isdigit():
        return error_page(request, InvalidInstallationId(f"installation_id={value!r}"))
    return render(
        request,
        "pycal_dashboard/installed.html",
        {"installation_id": int(value), "action": request.GET.get("setup_action", "install")},
    )
