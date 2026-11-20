"""What every page knows: the name of the site, its colors, its links and the visitor."""

from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from . import build_info
from .checks import is_url
from .import_guard import IMPORT_GUARD
from .services.app_registration import AppRegistration
from .services.identity import GitHubIdentity
from .theme import COOKIE, Theme

# the choices of the menu of the colors: value and title
THEMES = (("auto", _("As the system")), ("light", _("Light")), ("dark", _("Dark")))


def version_text() -> str:
    """The version and commit that run, for the details of errors.

    Returns:
        Such as ``1.2.3 (4cbfd3e)``.
    """
    build = build_info.get(settings.SOURCE_URL)
    if not build["commit"] or build["commit"] in build["version"]:
        return build["version"]
    return f"{build['version']} ({build['commit']})"


def unread_notifications(request: HttpRequest) -> int:
    """How many notifications of the person who signed in are unread and still ask something.

    Parameters:
        request: The request.

    Returns:
        The number; 0 for visitors.
    """
    user = getattr(request, "user", None)
    if not getattr(user, "is_authenticated", False):
        return 0
    with IMPORT_GUARD:  # see import_guard.py: the models are ready when pages are made
        from pycal_dashboard.models import Notification

    return Notification.objects.filter(user=user, read=None, resolved=None).count()


def site(request: HttpRequest) -> dict:
    """The context of every template.

    Parameters:
        request: The request.

    Returns:
        The name, the colors, the links of the site and the GitHub account of the visitor.
    """
    docs = settings.DOCS_URL.rstrip("/") + "/"
    chosen = getattr(getattr(request, "preferences", None), "theme", "")
    theme = Theme.choice(chosen or request.COOKIES.get(COOKIE))
    configured = bool(settings.GITHUB_APP_ID)
    return {
        "site_name": settings.SITE_NAME,
        "theme_choice": theme,
        "themes": THEMES,
        "languages": settings.LANGUAGES,
        "color_scheme": "light dark" if theme == "auto" else theme,
        "theme_css": settings.THEME.stylesheet(theme),
        "links": {
            "documentation": docs,
            "use": f"{docs}tutorial/use.html",
            "account": f"{docs}tutorial/account.html",
            "emails_help": f"{docs}tutorial/account.html#email-addresses",
            "app_setup": f"{docs}how-to/github-app.html",
            "install_help": f"{docs}how-to/install-app.html",
            "oauth_app": f"{docs}how-to/github-app.html#oauth-app",
            "log_help": f"{docs}tutorial/account.html#administrators",
            "notifications_help": f"{docs}tutorial/account.html#notifications",
            "new_permissions": f"{docs}how-to/install-app.html#new-permissions",
            "step_variables": f"{docs}tutorial/projects.html#step-variables",
            "delete_account": f"{docs}tutorial/account.html#delete-account",
            "json": f"{docs}reference/json.html",
            "projects": f"{docs}tutorial/projects.html",
            "project_roles": f"{docs}tutorial/projects.html#project-roles",
            "project_address": f"{docs}tutorial/projects.html#project-address",
            "add_repositories": f"{docs}tutorial/projects.html#add-repositories",
            "private_repositories": f"{docs}tutorial/projects.html#private-repositories",
            "permissions": f"{docs}reference/permissions.html",
            "licenses_help": f"{docs}contribute.html#license",
            "changelog": f"{docs}changelog.html",
            "source": settings.SOURCE_URL,
            "issues": f"{settings.SOURCE_URL.rstrip('/')}/issues/new",
            "organizations": [
                f"https://github.com/{login}" for login in settings.GITHUB_ORGANIZATIONS
            ],
        },
        "version": version_text(),
        "github_app_configured": configured,
        "favicon_url": settings.FAVICON if is_url(settings.FAVICON) else reverse("favicon"),
        "footer_links": settings.FOOTER_LINKS,
        # where people install the app on repositories; empty without an app
        "install_url": (
            f"https://github.com/apps/{settings.GITHUB_APP_SLUG}/installations/new"
            if configured and settings.GITHUB_APP_SLUG
            else ""
        ),
        "sign_in_configured": settings.SIGN_IN.configured,
        "app_registration_obstacle": None if configured else AppRegistration.obstacle(),
        "github": GitHubIdentity.of(getattr(request, "user", None)),
        "site_admin": GitHubIdentity.is_site_admin(getattr(request, "user", None)),
        "nav": getattr(request.resolver_match, "url_name", "") if request.resolver_match else "",
        "notification_count": unread_notifications(request),
    }
