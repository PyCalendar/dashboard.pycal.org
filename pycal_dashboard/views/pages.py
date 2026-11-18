"""The general pages: start, about, health, the switch of the colors."""

from django.conf import settings
from django.db import connection
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from pycal_dashboard import build_info
from pycal_dashboard.github.permissions import EVENTS, REQUIRED
from pycal_dashboard.theme import COOKIE, Theme


def home(request):
    """The start page: what the site is and where it stands.

    Args:
        request: The request.

    Returns:
        The page.
    """
    return render(request, "pycal_dashboard/home.html")


def about(request):
    """What the site is, the version that runs and the permissions of its GitHub App.

    Args:
        request: The request.

    Returns:
        The page.
    """
    return render(
        request,
        "pycal_dashboard/about.html",
        {
            "build": build_info.get(settings.SOURCE_URL),
            "permissions": REQUIRED,
            "events": EVENTS,
            "organizations": settings.GITHUB_ORGANIZATIONS,
        },
    )


def health(request):
    """The health check of the container: the database answers.

    Args:
        request: The request.

    Returns:
        ``{"status": "ok"}``.
    """
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return JsonResponse({"status": "ok", "github_app": bool(settings.GITHUB_APP_ID)})


@require_POST
def theme(request):
    """Keep the choice of the colors in a cookie and return to the page.

    Args:
        request: POST with ``theme`` (auto, light or dark) and ``next``.

    Returns:
        A redirect to ``next`` on this site.
    """
    target = request.POST.get("next", "/")
    if not url_has_allowed_host_and_scheme(target, {request.get_host()}, request.is_secure()):
        target = "/"
    response = HttpResponseRedirect(target)
    response.set_cookie(
        COOKIE,
        Theme.choice(request.POST.get("theme")),
        max_age=365 * 24 * 3600,
        samesite="Lax",
        secure=request.is_secure(),
    )
    return response
