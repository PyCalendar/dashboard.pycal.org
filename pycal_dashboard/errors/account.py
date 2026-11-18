"""Errors of the account page and the preferences, met by people who signed in."""

from .base import DashboardError


class AccountError(DashboardError):
    """The account could not be changed.

    Go back to the page *Account*, reload it and try again.
    """

    title = "The account could not be changed"
    guide = "tutorial/account.html"
    guide_title = "Your account"


class NoGitHubAccount(AccountError):
    """The account has no GitHub identity.

    Accounts of the dashboard come from GitHub. This one was created another
    way, such as with ``manage.py createsuperuser``. Sign out and sign in with
    GitHub.
    """

    title = "The account has no GitHub identity"
    status = 403


class UnknownPreference(AccountError):
    """The form of the preferences sent a value that the dashboard does not know.

    The detail names the field and its value. Reload the page *Account*; the
    form may be from an older version of the site.
    """

    title = "Unknown preference"


class WatchedRepositoryUnknown(AccountError):
    """A repository to watch is not one of the dashboard.

    You can watch the public repositories that the dashboard lists on the page
    *Repositories*. Reload the page *Account* and choose again.
    """

    title = "The repository to watch is unknown"
