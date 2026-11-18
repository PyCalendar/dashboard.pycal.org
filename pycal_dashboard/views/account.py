"""The private pages: the account, preferences and email addresses, the deliveries, the log."""

from allauth.account.models import EmailAddress
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from pycal_dashboard.actions import PreferencesSaved, Trigger
from pycal_dashboard.errors import NoGitHubAccount
from pycal_dashboard.models import LogTrigger, Profile, WebhookDelivery
from pycal_dashboard.services.identity import GitHubIdentity


@login_required
@require_http_methods(["GET", "POST"])
def account(request):
    """The account: who you are on GitHub, your email addresses and preferences.

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
    profile, _created = Profile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        profile.email_notifications = request.POST.get("email_notifications") == "yes"
        with Trigger.start("preferences", f"@{identity.login} saved the preferences"):
            profile.save(update_fields=["email_notifications"])
            PreferencesSaved(identity.login, profile.email_notifications).run()
        messages.success(request, _("Your preferences are saved."))
        return redirect("account")
    return render(
        request,
        "pycal_dashboard/account.html",
        {
            "identity": identity,
            "profile": profile,
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
