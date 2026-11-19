"""The private pages: the account, preferences and email addresses, the deliveries, the log."""

from __future__ import annotations

from datetime import timedelta

from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import HttpRequest
from django.shortcuts import redirect, render
from django.utils import timezone, translation
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods, require_POST

from pycal_dashboard.actions import PreferencesSaved, Trigger
from pycal_dashboard.context import THEMES
from pycal_dashboard.errors import NoGitHubAccount, UnknownPreference
from pycal_dashboard.models import (
    Installation,
    LogTrigger,
    Notification,
    Preferences,
    WebhookDelivery,
)
from pycal_dashboard.services.account_removal import AccountRemoval
from pycal_dashboard.services.app_notice import AppNotice
from pycal_dashboard.services.identity import GitHubIdentity
from pycal_dashboard.theme import CHOICES


def installations_of(identity: GitHubIdentity | None) -> list[Installation]:
    """The installations of the GitHub App that a person manages.

    Parameters:
        identity: The GitHub account of the person.

    Returns:
        Those the person installed or changed, and those on their own account.
    """
    github_id = int(identity.github_id)
    return [
        installation
        for installation in Installation.objects.filter(removed=False)
        if github_id in installation.admin_github_ids
        or installation.account_login.lower() == identity.login.lower()
    ]


def save_preferences(request: HttpRequest, login: str) -> None:
    """Check and save the form of the preferences: the language and the colors.

    Parameters:
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
    email_permissions = request.POST.get("email_permissions") == "yes"
    with Trigger.start("preferences", f"@{login} saved the preferences", actor_login=login):
        Preferences.objects.update_or_create(
            user=request.user,
            defaults={"language": language, "theme": theme, "email_permissions": email_permissions},
        )
        PreferencesSaved(login, language, theme, email_permissions).run()


@login_required
@require_http_methods(["GET", "POST"])
def account(request: HttpRequest):
    """The account: who you are on GitHub, your email addresses and preferences.

    The language and the colors: a choice here applies on every device; without one, the
    browser and the menus decide. The types of emails to switch on and off come with the
    features that send them.

    Parameters:
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
            "installations": installations_of(identity),
            "language_choices": settings.LANGUAGES,
            "theme_choices": THEMES,
            "emails": EmailAddress.objects.filter(user=request.user).order_by("-primary", "email"),
            "removal": AccountRemoval(request.user, identity.login),
        },
    )


@login_required
@require_POST
def account_delete(request: HttpRequest):
    """Delete the account of the person who signed in, after they typed their GitHub name.

    Parameters:
        request: The request, with ``confirm``, the GitHub name.

    Returns:
        A redirect to the start page, signed out.

    Raises:
        NoGitHubAccount: The account was not created with GitHub.
    """
    identity = GitHubIdentity.of(request.user)
    if identity is None:
        raise NoGitHubAccount(request.user.username)
    removal = AccountRemoval(request.user, identity.login)
    projects = removal.delete(request.POST.get("confirm", ""))
    logout(request)
    if projects:
        messages.success(
            request,
            _("Your account is deleted, with the projects %(names)s.")
            % {"names": ", ".join(projects)},
        )
    else:
        messages.success(request, _("Your account is deleted."))
    return redirect("home")


@login_required
@require_http_methods(["GET", "POST"])
def notifications(request: HttpRequest):
    """The notifications of the person who signed in; POST marks them as read.

    Parameters:
        request: The request; POST with ``read``, the number of a notification, or ``all``.

    Returns:
        The page, or a redirect after marking.
    """
    mine = Notification.objects.filter(user=request.user)
    if request.method == "POST" and "check" in request.POST:
        AppNotice.refresh_in_background()  # GitHub tells no change of the app itself
        messages.info(
            request, _("The site asks GitHub now. Reload this page in a moment to see the result.")
        )
        return redirect("notifications")
    if request.method == "POST":
        unread = mine.filter(read=None)
        chosen = request.POST.get("read", "")
        if chosen != "all":
            unread = unread.filter(pk=int(chosen) if chosen.isdigit() else 0)
        unread.update(read=timezone.now())
        return redirect("notifications")
    recent = timezone.now() - timedelta(days=30)
    return render(
        request,
        "pycal_dashboard/notifications.html",
        {
            # the app first: the owners of the installations can accept only after it
            "active": sorted(
                mine.filter(resolved=None),
                key=lambda n: n.kind != Notification.APP_PERMISSIONS,
            ),
            "resolved": mine.filter(resolved__gte=recent),
        },
    )


@login_required
def deliveries(request: HttpRequest):
    """The latest webhooks of GitHub, for the administrators of the site.

    Parameters:
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
def logs(request: HttpRequest):
    """The log of the site: what triggered what, for the administrators of the site.

    Parameters:
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
