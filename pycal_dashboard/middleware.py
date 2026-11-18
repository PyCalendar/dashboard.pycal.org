"""Show the errors of the site with their title, detail and link to the documentation."""

import logging

from allauth.socialaccount.models import SocialApp
from django.http import JsonResponse
from django.shortcuts import render

from .errors import DashboardError, SignInNotConfigured, UnexpectedError

log = logging.getLogger(__name__)


def is_api(request) -> bool:
    """Whether a request is for the API, which answers errors as JSON.

    Args:
        request: The request.

    Returns:
        True for addresses that start with ``/api/``.
    """
    return request.path.startswith("/api/")


def error_page(request, error: DashboardError, status: int | None = None):
    """The page of an error, or its JSON for the API.

    Args:
        request: The request.
        error: The error.
        status: The HTTP status; that of the error by default.

    Returns:
        The answer.
    """
    if is_api(request):
        return JsonResponse(error.as_json(), status=status or error.status)
    return render(
        request, "pycal_dashboard/error.html", {"error": error}, status=status or error.status
    )


class ErrorPageMiddleware:
    """Render :class:`~pycal_dashboard.errors.DashboardError` as a page that explains it."""

    def __init__(self, get_response):
        """The middleware.

        Args:
            get_response: The next step of Django.
        """
        self.get_response = get_response

    def __call__(self, request):
        """Answer the request.

        Args:
            request: The request.

        Returns:
            The answer.
        """
        return self.get_response(request)

    def process_exception(self, request, exception):
        """Show errors of the site; others are left to Django.

        Args:
            request: The request.
            exception: What was raised.

        Returns:
            The page of the error; None for other exceptions.
        """
        if isinstance(exception, SocialApp.DoesNotExist):
            exception = SignInNotConfigured("GITHUB_CLIENT_ID, GITHUB_OAUTH_CLIENT_ID")
        if not isinstance(exception, DashboardError):
            return None
        if isinstance(exception, UnexpectedError):
            log.exception("unexpected error", exc_info=exception)
        return error_page(request, exception)
