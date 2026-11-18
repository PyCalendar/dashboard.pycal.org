"""The private pages: the account, preferences and email addresses, the deliveries, the log."""

from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.utils import translation
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from pycal_dashboard.actions import PreferencesSaved, Trigger
from pycal_dashboard.context import THEMES
from pycal_dashboard.errors import NoGitHubAccount, UnknownPreference
from pycal_dashboard.models import LogTrigger, Preferences, WebhookDelivery
from pycal_dashboard.services.identity import GitHubIdentity
from pycal_dashboard.theme import CHOICES


def save_preferences(request, login: str) -> None:
    """Check and save the form of the preferences: the language and the colors.

    Args:
        request: The POST of the form.
        login: The GitHub handle of the person, for the log.

    Raises:
        UnknownPreference: The language or the colors are not ones of the site.
    """
    language = request.POST.get("language", "")
    theme = request.POST.get("theme", "")
    if language and language not in dict(settings.LANGUAGES):
        raise UnknownPreference(f"language={language!r}")
    if theme and theme not in CHOICES:
        raise UnknownPreference(f"theme={theme!r}")
    with Trigger.start("preferences", f"@{login} saved the preferences", actor_login=login):
        Preferences.objects.update_or_create(
            user=request.user, defaults={"language": language, "theme": theme}
        )
        PreferencesSaved(login, language, theme).run()


@login_required
@require_http_methods(["GET", "POST"])
def account(request):
    """The account: who you are on GitHub, your email addresses and preferences.

    The language and the colors: a choice here applies on every device; without one, the
    browser and the menus decide. The types of emails to switch on and off come with the
    features that send them.

    Args:
        request: The request of a person who signed in; POST saves the preferences.

    Returns:
        The page, or a redirect after saving.

    Raises:
        NoGitHubAccount: The account was not created with GitHub.
    """
    identity = GitHubIdentity.of(request.user)
    if identity is None:
        raise NoGitHubAccount(request.user.username)
    if request.method == "POST":
        save_preferences(request, identity.login)
        preferences = Preferences.objects.get(user=request.user)
        if preferences.language:
            translation.activate(preferences.language)  # the message in the new language
        messages.success(request, _("Your preferences are saved."))
        return redirect("account")
    return render(
        request,
        "pycal_dashboard/account.html",
        {
            "identity": identity,
            "preferences": Preferences.of(request.user) or Preferences(),
            "language_choices": settings.LANGUAGES,
            "theme_choices": THEMES,
            "emails": EmailAddress.objects.filter(user=request.user).order_by("-primary", "email"),
        },
    )


@login_required
def deliveries(request):
    """The latest webhooks of GitHub, for the administrators of the site.

    Args:
        request: The request.

    Returns:
        The page.

    Raises:
        PermissionDenied: The person is not in ``SITE_ADMINS``.
    """
    if not GitHubIdentity.is_site_admin(request.user):
        raise PermissionDenied("the webhook deliveries are for the administrators")
    return render(
        request,
        "pycal_dashboard/deliveries.html",
        {"deliveries": WebhookDelivery.objects.all()[:100]},
    )


@login_required
def logs(request):
    """The log of the site: what triggered what, for the administrators of the site.

    Args:
        request: The request; ``page`` is the page of 50 triggers.

    Returns:
        The page.

    Raises:
        PermissionDenied: The person is not in ``SITE_ADMINS``.
    """
    if not GitHubIdentity.is_site_admin(request.user):
        raise PermissionDenied("the log is for the administrators")
    triggers = LogTrigger.objects.prefetch_related("actions")
    page = Paginator(triggers, 50).get_page(request.GET.get("page"))
    return render(request, "pycal_dashboard/logs.html", {"page": page})
