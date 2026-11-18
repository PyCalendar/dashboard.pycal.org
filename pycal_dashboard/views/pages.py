"""The general pages: start, about, health, the switch of the colors."""

from django.conf import settings
from django.db import connection
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from pycal_dashboard import build_info
from pycal_dashboard.github.permissions import EVENTS, REQUIRED, USER_PERMISSIONS
from pycal_dashboard.models import Profile
from pycal_dashboard.services.overview import Overview
from pycal_dashboard.services.request_filters import RequestFilters
from pycal_dashboard.theme import COOKIE, Theme


def home(request):
    """The start page: where to help, what waits, who contributes.

    Args:
        request: The request; ``days`` sets the period of the statistics.

    Returns:
        The page.
    """
    days = RequestFilters(request.GET).days()
    overview = Overview(days)
    watched = []
    if request.user.is_authenticated:
        profile = Profile.objects.filter(user=request.user).first()
        if profile:
            watched = Overview(days, profile.watched.filter(private=False)).per_repository()
    return render(
        request,
        "pycal_dashboard/home.html",
        {
            "counts": overview.counts(),
            "starter": overview.starter_issues(limit=8),
            "waiting": overview.waiting_for_review()[:8],
            "unanswered": overview.unanswered()[:8],
            "first": overview.first_contributions()[:5],
            "contributors": overview.contributors(limit=10),
            "watched": watched,
            "days": days,
        },
    )


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
            "permissions": {**REQUIRED, **USER_PERMISSIONS},
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
