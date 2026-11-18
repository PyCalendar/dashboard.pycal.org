"""The private pages: the account, preferences and email addresses, the deliveries, the log."""

from allauth.account.models import EmailAddress
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.shortcuts import render
from django.views.decorators.http import require_GET

from pycal_dashboard.errors import NoGitHubAccount
from pycal_dashboard.models import LogTrigger, WebhookDelivery
from pycal_dashboard.services.identity import GitHubIdentity


@login_required
@require_GET
def account(request):
    """The account: who you are on GitHub, your email addresses and preferences.

    The language and the colors are kept in cookies of the browser; the types of emails to
    switch on and off come with the features that send them.

    Args:
        request: The request of a person who signed in.

    Returns:
        The page.

    Raises:
        NoGitHubAccount: The account was not created with GitHub.
    """
    identity = GitHubIdentity.of(request.user)
    if identity is None:
        raise NoGitHubAccount(request.user.username)
    return render(
        request,
        "pycal_dashboard/account.html",
        {
            "identity": identity,
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
