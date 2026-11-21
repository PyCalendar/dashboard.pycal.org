"""The email addresses of an account, on the tab Email addresses of the account."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from allauth.account import app_settings
from allauth.account.views import EmailView
from django.shortcuts import redirect
from django.urls import reverse

from pycal_dashboard.errors import NoGitHubAccount
from pycal_dashboard.services.identity import GitHubIdentity

from .account import account_page

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


class AccountEmailView(EmailView):
    """What ``/accounts/email/`` of allauth does, with the tab Email addresses as its page.

    It adds an address and sends the link to verify it, sends the link again, makes a verified
    address the primary one, and removes one. Its forms are on the tab, and each leads back to
    it; an address that cannot be added shows its error there.
    """

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:  # noqa: ANN401
        """The tab Email addresses of the account.

        Parameters:
            request: The request.
            *args: Not used.
            **kwargs: Not used.

        Returns:
            A redirect to the tab.
        """
        return redirect(reverse("account") + "?tab=emails")

    def get_success_url(self) -> str:
        """Back to the tab, unless allauth asks for a code that it sent.

        Returns:
            The address.
        """
        if self._did_send_verification_email and app_settings.EMAIL_VERIFICATION_BY_CODE_ENABLED:
            return super().get_success_url()
        return reverse("account") + "?tab=emails"

    def form_invalid(self, form: Any) -> HttpResponse:  # noqa: ANN401 - a form of allauth
        """The tab with the error of the address that could not be added.

        Parameters:
            form: The form of the new address, with its errors.

        Returns:
            The page of the account.

        Raises:
            NoGitHubAccount: The account was not created with GitHub.
        """
        identity = GitHubIdentity.of(self.request.user)
        if identity is None:
            raise NoGitHubAccount(self.request.user.username)
        return account_page(self.request, identity, "emails", email_form=form)
