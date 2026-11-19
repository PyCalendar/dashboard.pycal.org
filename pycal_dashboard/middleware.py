"""Show the errors of the site with their title, detail and link to the documentation."""

from __future__ import annotations

import logging
from collections.abc import Callable

from allauth.socialaccount.models import SocialApp
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render

from .errors import DashboardError, SignInNotConfigured, UnexpectedError

log = logging.getLogger(__name__)


def is_json(request: HttpRequest) -> bool:
    """Whether a request is for the JSON of a page, which answers errors as JSON.

    Parameters:
        request: The request.

    Returns:
        True for ``<page>.json``, see :mod:`pycal_dashboard.public_json`.
    """
    return getattr(request, "public_json", False)


def error_page(request: HttpRequest, error: DashboardError, status: int | None = None):
    """The page of an error, or its JSON for ``<page>.json``.

    Parameters:
        request: The request.
        error: The error.
        status: The HTTP status; that of the error by default.

    Returns:
        The answer.
    """
    if is_json(request):
        return JsonResponse(error.as_json(), status=status or error.status)
    return render(
        request, "pycal_dashboard/error.html", {"error": error}, status=status or error.status
    )


class ErrorPageMiddleware:
    """Render :class:`~pycal_dashboard.errors.DashboardError` as a page that explains it."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        """The middleware.

        Parameters:
            get_response: The next step of Django.
        """
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        """Answer the request.

        Parameters:
            request: The request.

        Returns:
            The answer.
        """
        return self.get_response(request)

    def process_exception(self, request: HttpRequest, exception: Exception):
        """Show errors of the site; others are left to Django.

        Parameters:
            request: The request.
            exception: What was raised.

        Returns:
            The page of the error; None for other exceptions.
        """
        if isinstance(exception, SocialApp.DoesNotExist):
            exception = SignInNotConfigured("GITHUB_OAUTH_CLIENT_ID")
        if not isinstance(exception, DashboardError):
            return None
        if isinstance(exception, UnexpectedError):
            log.exception("unexpected error", exc_info=exception)
        return error_page(request, exception)
