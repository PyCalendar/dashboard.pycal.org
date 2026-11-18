"""The OAuth app that signs people in, entered on the site: ``/setup/oauth-app/``.

GitHub has no manifest for OAuth apps: the people who run the site create one on GitHub and
enter its client ID and secret here, with the setup code of the log. They are kept in
``DATA_DIR/.env``; settings of the environment take precedence. Afterwards only the
administrators of the site (``SITE_ADMINS``) change it.
"""

import os
import re

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from pycal_dashboard import registered_settings
from pycal_dashboard.services.app_registration import AppRegistration
from pycal_dashboard.services.identity import GitHubIdentity
from pycal_dashboard.sign_in import SignIn

CLIENT_ID = re.compile(r"[A-Za-z0-9._-]{8,100}")
SECRET = re.compile(r"[A-Za-z0-9._-]{20,200}")
TEMPLATE = "pycal_dashboard/oauth_app.html"


def from_environment() -> bool:
    """Whether the OAuth app is set in the environment rather than in ``DATA_DIR/.env``.

    Returns:
        True if only the environment sets ``GITHUB_OAUTH_CLIENT_ID``.
    """
    stored = registered_settings.read(AppRegistration.env_file())
    return bool(os.environ.get("GITHUB_OAUTH_CLIENT_ID")) and not stored.get(
        "GITHUB_OAUTH_CLIENT_ID"
    )


def apply(client_id: str, secret: str) -> None:
    """Keep the OAuth app in ``DATA_DIR/.env`` and use it in this process.

    Args:
        client_id: The client ID of the OAuth app.
        secret: Its client secret.
    """
    values = {"GITHUB_OAUTH_CLIENT_ID": client_id, "GITHUB_OAUTH_SECRET": secret}
    registered_settings.write(AppRegistration.env_file(), values)
    os.environ.update(values)
    settings.SIGN_IN = SignIn(client_id, secret)
    settings.SOCIALACCOUNT_PROVIDERS = settings.SIGN_IN.providers()


@require_http_methods(["GET", "POST"])
def oauth_app(request):
    """Enter the OAuth app that signs people in.

    Args:
        request: The request; POST with ``client_id``, ``secret`` and ``setup_code``.

    Returns:
        The page, or the sign-in page after saving.

    Raises:
        PermissionDenied: The site has an OAuth app and the person is not in ``SITE_ADMINS``.
    """
    admin = GitHubIdentity.is_site_admin(request.user)
    if settings.SIGN_IN.configured and not admin:
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        raise PermissionDenied("the OAuth app is changed by the administrators of the site")
    context = {
        "configured": settings.SIGN_IN.configured,
        "from_environment": from_environment(),
        "needs_code": not admin and AppRegistration.needs_setup_code(),
        "callback_url": f"{settings.SITE_URL}/accounts/github/login/callback/",
        "site_url": settings.SITE_URL,
        "nav": "oauth_app",
    }
    if request.method == "GET" or context["from_environment"]:
        return render(request, TEMPLATE, context)
    client_id = request.POST.get("client_id", "").strip()
    secret = request.POST.get("secret", "").strip()
    if context["needs_code"] and not AppRegistration.code_matches(
        request.POST.get("setup_code", "")
    ):
        context["code_error"] = True
        return render(request, TEMPLATE, context, status=403)
    if not CLIENT_ID.fullmatch(client_id) or not SECRET.fullmatch(secret):
        context["error"] = True
        return render(request, TEMPLATE, context, status=400)
    apply(client_id, secret)
    AppRegistration.reload_workers(request)
    messages.success(request, "People now sign in with the OAuth app.")
    return redirect("account_login")
