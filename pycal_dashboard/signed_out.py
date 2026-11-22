"""After signing out, stay on the page if visitors see it; else go up to the next one they see.

The menu of the account signs out with ``next``: the page with ``?signed_out=1``. That page is
tried as a visitor: when it answers, the visitor stays there; when it needs a sign-in, is
private or does not exist, the page a level higher is tried, such as the overview of a project
for its settings, up to the start page. Each step is a request of its own, so every page
decides itself what visitors see.
"""

from __future__ import annotations

from collections.abc import Callable
from urllib.parse import urlencode

from django.contrib import messages
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect

FLAG = "signed_out"


def parent(path: str) -> str:
    """The page a level higher.

    Parameters:
        path: Such as ``/projects/icalendar/settings/danger/``.

    Returns:
        Such as ``/projects/icalendar/settings/``; ``/`` for the start page.

    Examples:
        >>> parent("/projects/icalendar/settings/danger/"), parent("/projects/"), parent("/")
        ('/projects/icalendar/settings/', '/', '/')
    """
    trimmed = path.rstrip("/")
    return trimmed.rsplit("/", 1)[0] + "/" if trimmed else "/"


def signed_out_address(path: str, query: str = "") -> str:
    """The address to sign out to from a page: the page, marked to be tried as a visitor.

    Parameters:
        path: The path of the page.
        query: Its query, such as ``tab=reviews``; kept when visitors see the page.

    Returns:
        Such as ``/projects/icalendar/settings/?signed_out=1``.

    Examples:
        >>> signed_out_address("/projects/x/pull-requests/", "page=2")
        '/projects/x/pull-requests/?page=2&signed_out=1'
    """
    return f"{path}?{query + '&' if query else ''}{urlencode({FLAG: 1})}"


class SignedOutMiddleware:
    """Find the page to stay on after signing out, see the module."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        """The middleware.

        Parameters:
            get_response: The next step of Django.
        """
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Try a page marked ``signed_out`` as a visitor; stay on it or go a level higher.

        Parameters:
            request: The request.

        Returns:
            The answer; for a marked page, a redirect: to it without the mark when it answers,
            else to the page a level higher, marked.
        """
        if request.method != "GET" or FLAG not in request.GET:
            return self.get_response(request)
        response = self.get_response(request)
        path = request.path
        if response.status_code == 200 or path == "/":
            messages.get_messages(request).used = False  # "signed out" shows on the page
            query = request.GET.copy()
            query.pop(FLAG, None)
            return HttpResponseRedirect(path + (f"?{query.urlencode()}" if query else ""))
        return HttpResponseRedirect(signed_out_address(parent(path)))
