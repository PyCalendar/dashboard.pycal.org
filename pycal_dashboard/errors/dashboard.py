"""Errors of the pages and the API of the dashboard, met by visitors.

The pages show them with the HTTP status; the API answers with the same name,
title and link as JSON, see :doc:`/reference/api`.
"""

from .base import DashboardError


class LookupFailed(DashboardError):
    """The page does not exist.

    Check the address, or start again from the start page.
    """

    title = "Not found"
    status = 404
    guide = "tutorial/use.html"
    guide_title = "Use the dashboard"


class ApiEndpointNotFound(LookupFailed):
    """The API has no such address.

    The addresses of the API start with ``/api/v1/`` and are listed in
    :doc:`/reference/api`.
    """

    title = "No such address in the API"
    guide = "reference/api.html"
    guide_title = "API"


class InvalidInstallationId(DashboardError):
    """GitHub returned to the site without the number of the installation.

    GitHub opens ``/setup/installed/?installation_id=...`` after the GitHub App
    was installed. The address was changed or opened by hand. Install the app
    again from its page on GitHub, see :doc:`/how-to/github-app`.
    """

    title = "Invalid installation"
    status = 400
    guide = "how-to/github-app.html"
    guide_title = "Register the GitHub App"
