"""Errors of the account page, met by people who signed in."""

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


class UnknownPreference(AccountError):
    """The form of the preferences sent a value that the site does not know.

    The detail names the field and its value. Reload the page *Account*: the
    form may be from an older version of the site, which knew other languages
    or colors.
    """

    title = _("Unknown preference")


class AccountDeletionNotConfirmed(AccountError):
    """The account was not deleted: the GitHub name typed to confirm it does not match.

    Type your GitHub name, as the page *Account* shows it after *@*, into the field of the red
    area, and press the button again.
    """

    title = _("Type your GitHub name to delete the account")
    status = 400


class AccountOwnsSharedProjects(AccountError):
    """The account was not deleted: it is the only owner of projects that others share.

    A project always has an owner. On the tab *Collaborators* of each project the page
    lists, give another person the role *own*, or delete the project, then delete the account.
    """

    title = _("You are the only owner of shared projects")
    status = 409
