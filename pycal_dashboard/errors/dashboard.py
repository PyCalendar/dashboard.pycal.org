"""Errors of the pages and the API of the dashboard, met by visitors.

The pages show them with the HTTP status; the JSON of a page answers with the
same name, title and link, see :doc:`/reference/json`.
"""

from django.utils.translation import gettext_lazy as _

from .base import DashboardError


class LookupFailed(DashboardError):
    """The page does not exist.

    Resolve:
        Check the address, or start again from the start page.
    """

    title = _("Not found")
    status = 404
    guide = "tutorial/use.html"
    guide_title = _("Use the dashboard")


class InvalidInstallationId(DashboardError):
    """GitHub returned to the dashboard without the number of the installation.

    Resolve:
        Install the GitHub App again from its page on GitHub, see :doc:`/how-to/github-app`.

    Context:
        GitHub opens ``/setup/installed/?installation_id=...`` after the GitHub App was
        installed. Without the number, the address was changed or opened by hand.

    Note:
        The detail is the value of ``installation_id`` in the address.
    """

    title = _("Invalid installation")
    status = 400
    guide = "how-to/github-app.html"
    guide_title = _("Register the GitHub App")


class GitHubHandleInvalid(DashboardError):
    """The address of the page of a person has no GitHub handle.

    Resolve:
        Check the address, or follow a GitHub handle that dashboard.pycal.org shows: each one
        links to the page of the person.

    Context:
        A GitHub handle has up to 39 letters a to z, digits and hyphens, such as
        ``niccokunzmann`` in ``/people/niccokunzmann/``.

    Note:
        The detail is the part of the address that is no GitHub handle.
    """

    title = _("Not a GitHub handle")
    status = 404
    guide = "tutorial/projects.html#person-page"
    guide_title = _("The page of a person")
