"""Register the GitHub App of the site on the site: ``/setup/github-app/``.

Without JavaScript: the first form sends the name, the organization and the setup code to the
site, which answers with a form that sends the manifest to GitHub. GitHub returns to
``/setup/github-app/registered/``, where the site exchanges the code for the credentials.
"""

from __future__ import annotations

import json
import logging

from django.conf import settings
from django.http import HttpRequest
from django.shortcuts import render

from pycal_dashboard.errors import DashboardError, RegistrationError
from pycal_dashboard.github.app_check import AppCheck
from pycal_dashboard.middleware import error_page
from pycal_dashboard.services.app_registration import AppRegistration
from pycal_dashboard.services.identity import GitHubIdentity

log = logging.getLogger(__name__)


def app_check(request: HttpRequest) -> AppCheck | None:
    """What the GitHub App lacks, for the administrators of the site.

    Parameters:
        request: The request.

    Returns:
        The check of the app; None for other people, without an app, or if GitHub could
        not be asked.
    """
    if not AppRegistration.source() or not GitHubIdentity.is_site_admin(request.user):
        return None
    try:
        return AppCheck.read()
    except DashboardError as error:
        log.warning("the GitHub App could not be read: %s %s", error.code, error)
        return None


def register_app(request: HttpRequest):
    """The page *Register the GitHub App*: the form, or the app the site has.

    Parameters:
        request: The request; POST with ``name``, ``organization`` and ``setup_code``.

    Returns:
        The page; after a POST the form that sends the manifest to GitHub.
    """
    organizations = settings.GITHUB_ORGANIZATIONS
    context = {
        "source": AppRegistration.source(),
        "app_check": app_check(request),
        "slug": settings.GITHUB_APP_SLUG,
        "site_url": settings.SITE_URL,
        "local": AppRegistration.is_local(settings.SITE_URL),
        "needs_code": AppRegistration.needs_setup_code(),
        "name": request.POST.get("name", settings.SITE_NAME[:34]),
        "organization": request.POST.get("organization", organizations[0] if organizations else ""),
    }
    if request.method == "POST":
        try:
            started = AppRegistration.start(
                request.session,
                request.POST.get("name", ""),
                request.POST.get("organization", ""),
                request.POST.get("setup_code", ""),
            )
        except RegistrationError as error:
            context["error"] = error
            return render(
                request, "pycal_dashboard/register_app.html", context, status=error.status
            )
        context.update(
            started=started,
            manifest_json=json.dumps(started["manifest"]),
            manifest_preview=json.dumps(started["manifest"], indent=2),
        )
    return render(request, "pycal_dashboard/register_app.html", context)


def app_registered(request: HttpRequest):
    """GitHub returns here with ``code`` and ``state`` after it created the app.

    Parameters:
        request: The request.

    Returns:
        The page of the new app, or the page of the error with details to copy.
    """
    try:
        app = AppRegistration.finish(
            request.session, request.GET.get("code", ""), request.GET.get("state", "")
        )
    except DashboardError as error:
        log.warning("registration of the GitHub App: %s %s", error.code, error)
        return error_page(request, error)
    log.info("registered the GitHub App %s (%s)", app.get("slug"), app.get("id"))
    reloaded = AppRegistration.reload_workers(request)
    return render(
        request,
        "pycal_dashboard/app_registered.html",
        {
            "app": app,
            "install_url": f"{app.get('html_url')}/installations/new",
            "local": AppRegistration.is_local(settings.SITE_URL),
            "reloaded": reloaded,
            "env_file": AppRegistration.env_file(),
            "key_file": AppRegistration.key_file(),
        },
    )
