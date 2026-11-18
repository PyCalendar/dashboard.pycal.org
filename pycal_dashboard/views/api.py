"""The JSON API of the dashboard.

docs/reference/api.rst describes it. Errors are JSON with ``error``, ``title``, ``detail``
and ``documentation``. The site keeps no data of GitHub yet, so the API tells what runs.
"""

from django.conf import settings
from django.http import JsonResponse

from pycal_dashboard import build_info


def index(request):
    """What runs: the version of the API and of the site, and what is set up.

    Args:
        request: The request.

    Returns:
        JSON with the site.
    """
    build = build_info.get(settings.SOURCE_URL)
    return JsonResponse(
        {
            "api": 1,
            "site": settings.SITE_NAME,
            "version": build["version"],
            "commit": build["commit"],
            "github_app": bool(settings.GITHUB_APP_ID),
            "sign_in": settings.SIGN_IN.configured,
            "organizations": settings.GITHUB_ORGANIZATIONS,
            "documentation": settings.DOCS_URL,
        }
    )
