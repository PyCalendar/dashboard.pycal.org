"""GitHub returns here after the app was installed or its installation changed."""

from django.shortcuts import render

from pycal_dashboard.errors import DashboardError, InvalidFilter
from pycal_dashboard.middleware import error_page
from pycal_dashboard.models import Installation
from pycal_dashboard.services.identity import GitHubIdentity
from pycal_dashboard.services.repository_sync import RepositorySync


def installed(request):
    """Read a new installation at once, so that the dashboard shows its repositories.

    A known installation is read again only for the administrators of the site: the webhooks
    keep it up to date, and nobody else makes the site read everything again.

    Args:
        request: The request, with ``installation_id`` and ``setup_action`` of GitHub.

    Returns:
        The page with what was read, or the page of the error.
    """
    value = request.GET.get("installation_id", "")
    if not value.isdigit():
        return error_page(request, InvalidFilter(f"installation_id={value!r}"))
    installation_id = int(value)
    known = Installation.objects.filter(github_id=installation_id).first()
    summary = None
    if known is None or GitHubIdentity.is_site_admin(request.user):
        try:
            summary = RepositorySync(installation_id).run()
        except DashboardError as error:
            return error_page(request, error)
        known = Installation.objects.get(github_id=installation_id)
    return render(
        request,
        "pycal_dashboard/installed.html",
        {"installation": known, "summary": summary},
    )
