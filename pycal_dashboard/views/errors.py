"""The pages of the HTTP errors: in the design of the site, with a way back.

Django calls these views for the errors that no page of the site handles itself; the errors of
the site (:class:`~pycal_dashboard.errors.DashboardError`) have their own page with a link to their
documentation (``pycal_dashboard/error.html``), in the same design.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.http import HttpRequest, HttpResponseServerError
from django.shortcuts import render
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.utils.translation import gettext_lazy as _

log = logging.getLogger(__name__)

PAGES = {
    400: (
        _("Bad request"),
        _("The site could not understand the request. Go back, reload the page and try again."),
    ),
    403: (
        _("Access denied"),
        _(
            "You may not open this page. It shows private information: sign in with the "
            "GitHub account it belongs to."
        ),
    ),
    404: (
        _("Page not found"),
        _("This page does not exist or has moved. Check the address, or start again."),
    ),
    500: (
        _("Something went wrong"),
        _(
            "The site could not answer this time. The problem was logged. "
            "Please try again in a few minutes."
        ),
    ),
}
CSRF = (
    _("The form has expired"),
    _(
        "The site accepts a form only from its own pages, with its cookie. Go back, reload the "
        "page and send the form again. Allow cookies for this site if this happens again."
    ),
)


def status_page(
    request: HttpRequest, status: int, title: str | None = None, explanation: str | None = None
):
    """The page of an HTTP error in the design of the site.

    Parameters:
        request: The request.
        status: The HTTP status, such as 404.
        title: The title; that of the status by default.
        explanation: What happened and what to do; that of the status by default.

    Returns:
        The page, with the status.
    """
    default_title, default_explanation = PAGES[status]
    context = {
        "status": status,
        "title": title or default_title,
        "explanation": explanation or default_explanation,
    }
    return render(request, "pycal_dashboard/status.html", context, status=status)


def bad_request(request: HttpRequest, exception: Exception | None = None):
    """400: the request could not be understood.

    Parameters:
        request: The request.
        exception: What Django raised.

    Returns:
        The page.
    """
    return status_page(request, 400)


def permission_denied(request: HttpRequest, exception: Exception | None = None):
    """403: the visitor may not open the page.

    Parameters:
        request: The request.
        exception: What Django raised.

    Returns:
        The page.
    """
    return status_page(request, 403)


def page_not_found(request: HttpRequest, exception: Exception | None = None):
    """404: there is no such page.

    Parameters:
        request: The request.
        exception: What Django raised.

    Returns:
        The page.
    """
    return status_page(request, 404)


def csrf_failure(request: HttpRequest, reason: str = ""):
    """403 for a form without a valid CSRF token, such as one left open too long.

    Parameters:
        request: The request.
        reason: Why Django refused the form; it is logged, not shown.

    Returns:
        The page.
    """
    log.info("CSRF failure: %s", reason)
    return status_page(request, 403, *CSRF)


def server_error(request: HttpRequest):
    """500: the site failed. Shown even if the database or a template is the cause.

    The page of the site needs the database for its menu; if that fails, a page without the
    menu in the same colors is shown, and if even that fails, plain text.

    Parameters:
        request: The request.

    Returns:
        The page.
    """
    try:
        return status_page(request, 500)
    except Exception:  # noqa: BLE001 - the error page must not fail
        log.exception("the error page with the menu failed")
    title, explanation = PAGES[500]
    try:
        page = render_to_string(
            "500.html",
            {
                "status": 500,
                "title": title,
                "explanation": explanation,
                "site_name": settings.SITE_NAME,
                "stylesheet": static("style.css"),
                "theme_css": settings.THEME.stylesheet(),
                "links": {
                    "documentation": settings.DOCS_URL,
                    "issues": f"{settings.SOURCE_URL.rstrip('/')}/issues/new",
                },
            },
        )
    except Exception:  # noqa: BLE001 - the error page must not fail
        log.exception("the plain error page failed")
        page = f"{title}\n\n{explanation}\n"
        return HttpResponseServerError(page, content_type="text/plain; charset=utf-8")
    return HttpResponseServerError(page)
