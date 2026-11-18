"""Errors of the pages and the API of the dashboard, met by visitors.

The pages show them with the HTTP status; the API answers with the same name,
title and link as JSON, see :doc:`/reference/api`.
"""

from .base import DashboardError


class LookupFailed(DashboardError):
    """The page shows something that the dashboard does not know.

    Check the address. The dashboard knows the public repositories of the
    organizations where its GitHub App is installed.
    """

    title = "Not found"
    status = 404
    guide = "tutorial/use.html"
    guide_title = "Use the dashboard"


class RepositoryNotFound(LookupFailed):
    """The dashboard does not know this repository.

    The repository does not exist, is private, or the GitHub App is not
    installed on it. Private repositories are never shown. The list of
    repositories is on the page *Repositories*.
    """

    title = "Repository not found"


class ContributorNotFound(LookupFailed):
    """The dashboard knows no issue or pull request of this person.

    The handle is misspelled, or the person has not opened an issue or pull
    request in the public repositories of the dashboard yet.
    """

    title = "Contributor not found"


class ApiEndpointNotFound(LookupFailed):
    """The API has no such address.

    The addresses of the API start with ``/api/v1/`` and are listed in
    :doc:`/reference/api`.
    """

    title = "No such address in the API"
    guide = "reference/api.html"
    guide_title = "API"


class InvalidFilter(DashboardError):
    """A filter of the address has a value that the page does not know.

    The detail names the parameter and its allowed values, such as
    ``state=open`` or ``state=closed``. Remove the parameter to see everything.
    """

    title = "Invalid filter"


class InvalidPageNumber(InvalidFilter):
    """``page`` is not a positive whole number.

    Pages are counted from 1, such as ``?page=2``.
    """

    title = "Invalid page number"


class InvalidDays(InvalidFilter):
    """``days`` is not a whole number between 1 and 3650.

    ``days`` is the period of the statistics in days, such as ``?days=90``.
    """

    title = "Invalid number of days"
