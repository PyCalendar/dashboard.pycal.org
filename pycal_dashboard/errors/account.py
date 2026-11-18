"""Errors of the account page and the preferences, met by people who signed in."""

from django.utils.translation import gettext_lazy as _

from .base import DashboardError


class AccountError(DashboardError):
    """The account could not be changed.

    Go back to the page *Account*, reload it and try again.
    """

    title = _("The account could not be changed")
    guide = "tutorial/account.html"
    guide_title = _("Your account")


class NoGitHubAccount(AccountError):
    """The account has no GitHub identity.

    Accounts of the dashboard come from GitHub. This one was created another
    way, such as with ``manage.py createsuperuser``. Sign out and sign in with
    GitHub.
    """

    title = _("The account has no GitHub identity")
    status = 403
