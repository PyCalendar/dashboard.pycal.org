"""The private pages: the account with its preferences and email addresses, the deliveries."""

from allauth.account.models import EmailAddress
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from pycal_dashboard.errors import (
    ContributorNotFound,
    NoGitHubAccount,
    UnknownPreference,
    WatchedRepositoryUnknown,
)
from pycal_dashboard.models import Profile, WebhookDelivery
from pycal_dashboard.services.contributor_stats import ContributorStats
from pycal_dashboard.services.identity import GitHubIdentity
from pycal_dashboard.services.overview import Overview

DAYS = (30, 90, 365)


def save_preferences(profile: Profile, data) -> None:
    """Check and save the form of the preferences.

    Args:
        profile: The preferences of the person.
        data: ``request.POST``.

    Raises:
        UnknownPreference: ``days`` is not one of the choices.
        WatchedRepositoryUnknown: A repository to watch is not shown on the dashboard.
    """
    days = data.get("days", "90")
    if not days.isdigit() or int(days) not in DAYS:
        raise UnknownPreference(f"days={days!r}")
    ids = data.getlist("watched")
    public = Overview.public()
    watched = list(public.filter(pk__in=[i for i in ids if i.isdigit()]))
    if len(watched) != len(ids):
        raise WatchedRepositoryUnknown(", ".join(ids))
    profile.email_digest = data.get("email_digest") == "yes"
    profile.show_drafts = data.get("show_drafts") == "yes"
    profile.days = int(days)
    profile.save()
    profile.watched.set(watched)


@login_required
@require_http_methods(["GET", "POST"])
def account(request):
    """The account: who you are on GitHub, your email addresses, preferences and work.

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
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        save_preferences(profile, request.POST)
        messages.success(request, "Your preferences are saved.")
        return redirect("account")
    try:
        stats = ContributorStats(identity.login)
    except ContributorNotFound:
        stats = None
    return render(
        request,
        "pycal_dashboard/account.html",
        {
            "identity": identity,
            "profile": profile,
            "emails": EmailAddress.objects.filter(user=request.user).order_by("-primary", "email"),
            "repositories": Overview.public().filter(archived=False),
            "watched_ids": set(profile.watched.values_list("pk", flat=True)),
            "day_choices": DAYS,
            "open_pulls": stats.open_pulls() if stats else [],
            "review_requests": stats.review_requests() if stats else [],
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
