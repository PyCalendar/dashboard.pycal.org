"""What every page knows: the name of the site, its colors, its links and the visitor."""

from django.conf import settings
from django.urls import reverse

from . import build_info
from .checks import is_url
from .services.app_registration import AppRegistration
from .services.identity import GitHubIdentity
from .theme import COOKIE, Theme

# the choices of the menu of the colors: value and title
THEMES = (("auto", "As the system"), ("light", "Light"), ("dark", "Dark"))


def version_text() -> str:
    """The version and commit that run, for the details of errors.

    Returns:
        Such as ``1.2.3 (4cbfd3e)``.
    """
    build = build_info.get(settings.SOURCE_URL)
    if not build["commit"] or build["commit"] in build["version"]:
        return build["version"]
    return f"{build['version']} ({build['commit']})"


def site(request) -> dict:
    """The context of every template.

    Args:
        request: The request.

    Returns:
        The name, the colors, the links of the site and the GitHub account of the visitor.
    """
    docs = settings.DOCS_URL.rstrip("/") + "/"
    theme = Theme.choice(request.COOKIES.get(COOKIE))
    configured = bool(settings.GITHUB_APP_ID)
    return {
        "site_name": settings.SITE_NAME,
        "theme_choice": theme,
        "themes": THEMES,
        "color_scheme": "light dark" if theme == "auto" else theme,
        "theme_css": settings.THEME.stylesheet(theme),
        "links": {
            "documentation": docs,
            "use": f"{docs}tutorial/use.html",
            "account": f"{docs}tutorial/account.html",
            "app_setup": f"{docs}how-to/github-app.html",
            "install_help": f"{docs}how-to/install-app.html",
            "oauth_app": f"{docs}how-to/github-app.html#oauth-app",
            "json": f"{docs}reference/json.html",
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
    }
