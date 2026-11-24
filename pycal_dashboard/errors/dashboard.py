"""Errors of the pages and the API of the dashboard, met by visitors.

The pages show them with the HTTP status; the JSON of a page answers with the
same name, title and link, see :doc:`/reference/json`.
"""

from django.utils.translation import gettext_lazy as _

from .base import DashboardError


class LookupFailed(DashboardError):
    """The page does not exist.

    Check the address, or start again from the start page.
    """

    title = _("Not found")
    status = 404
    guide = "tutorial/use.html"
    guide_title = _("Use the dashboard")


class InvalidInstallationId(DashboardError):
    """GitHub returned to the site without the number of the installation.

    GitHub opens ``/setup/installed/?installation_id=...`` after the GitHub App
    was installed. The address was changed or opened by hand. Install the app
    again from its page on GitHub, see :doc:`/how-to/github-app`.
    """

    title = _("Invalid installation")
    status = 400
    guide = "how-to/github-app.html"
    guide_title = _("Register the GitHub App")


class GitHubHandleInvalid(DashboardError):
    """The address of the page of a person has no GitHub handle.

    A GitHub handle has up to 39 letters a to z, digits and hyphens, such as
    ``niccokunzmann`` in ``/people/niccokunzmann/``. Check the address; every
    GitHub handle that dashboard.pycal.org shows links to this page.
    """

    title = _("Not a GitHub handle")
    status = 404
    guide = "tutorial/projects.html#person-page"
    guide_title = _("The page of a person")
