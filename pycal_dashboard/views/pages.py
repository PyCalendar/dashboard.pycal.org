"""The general pages: start, about, licenses, health, the icon, the switch of the colors."""

from dataclasses import asdict
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders
from django.db import connection
from django.http import FileResponse, Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_POST

from pycal_dashboard import build_info, licenses
from pycal_dashboard.checks import FAVICON_TYPES, is_url
from pycal_dashboard.github.permissions import EVENTS, REQUIRED
from pycal_dashboard.public_json import json_address
from pycal_dashboard.theme import COOKIE, Theme
from pycal_dashboard.views.json_page import page


def home(request):
    """The start page: what the site is and where it stands; ``/index.json``.

    Args:
        request: The request.

    Returns:
        The page or its JSON.
    """
    build = build_info.get(settings.SOURCE_URL)
    return page(
        request,
        "pycal_dashboard/home.html",
        {},
        lambda: {
            "site": settings.SITE_NAME,
            "version": build["version"],
            "commit": build["commit"],
            "github_app": bool(settings.GITHUB_APP_ID),
            "sign_in": settings.SIGN_IN.configured,
            "organizations": settings.GITHUB_ORGANIZATIONS,
            "documentation": settings.DOCS_URL,
            "pages": {name: json_address(reverse(name)) for name in ("home", "about", "licenses")},
        },
    )


def about(request):
    """The version that runs and the GitHub App; ``/about.json``.

    Args:
        request: The request.

    Returns:
        The page or its JSON.
    """
    build = build_info.get(settings.SOURCE_URL)
    return page(
        request,
        "pycal_dashboard/about.html",
        {
            "build": build,
            "permissions": REQUIRED,
            "events": EVENTS,
            "organizations": settings.GITHUB_ORGANIZATIONS,
        },
        lambda: {
            "build": {key: str(value) if value else value for key, value in build.items()},
            "github_app": {
                "permissions": REQUIRED,
                "events": EVENTS,
                "organizations": settings.GITHUB_ORGANIZATIONS,
            },
        },
    )


def licenses_page(request):
    """The licenses of the site: of the project, of code from other projects, of packages.

    Args:
        request: The request.

    Returns:
        The page or ``/licenses.json``.
    """
    context = {
        "project_license": licenses.PROJECT_LICENSE,
        "license_names": licenses.license_names(),
        "reused": licenses.reused(),
        "packages": licenses.packages(),
    }
    return page(
        request,
        "pycal_dashboard/licenses.html",
        context,
        lambda: {
            "license": context["project_license"],
            "licenses": [
                {"name": name, "text": reverse("license_text", args=[name])}
                for name in context["license_names"]
            ],
            "reused": [asdict(package) for package in context["reused"]],
            "packages": [asdict(package) for package in context["packages"]],
        },
    )


def license_text(request, name: str):
    """The text of a license of ``LICENSES/``, as plain text.

    Args:
        request: The request.
        name: The SPDX identifier, such as ``MIT``.

    Returns:
        The text.

    Raises:
        Http404: The project has no such license.
    """
    path = licenses.license_file(name)
    if path is None:
        raise Http404(name)
    return HttpResponse(path.read_text(), content_type="text/plain; charset=utf-8")


def package_license(request, name: str):
    """The text of the license of an installed Python package, as plain text.

    Args:
        request: The request.
        name: The name of the package.

    Returns:
        The text.

    Raises:
        Http404: The package is not installed or ships no license file.
    """
    text = licenses.package_license_text(name)
    if text is None:
        raise Http404(name)
    return HttpResponse(text, content_type="text/plain; charset=utf-8")


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


@cache_control(max_age=86400, public=True)
def favicon(request):
    """The icon of the site: ``FAVICON`` (an address or a file), or the icon of pycal.

    Args:
        request: The request.

    Returns:
        The image, or a redirect to the address of the icon.
    """
    if is_url(settings.FAVICON):
        return HttpResponseRedirect(settings.FAVICON)
    path = Path(settings.FAVICON) if settings.FAVICON else None
    if not path or not path.is_file():
        path = Path(finders.find("img/favicon.png"))
    return FileResponse(
        path.open("rb"), content_type=FAVICON_TYPES.get(path.suffix.lower(), "image/png")
    )


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
