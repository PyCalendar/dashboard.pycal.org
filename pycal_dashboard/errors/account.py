"""Errors of the account page, met by people who signed in."""

from django.utils.translation import gettext_lazy as _

from .base import DashboardError


class AccountError(DashboardError):
    """The account could not be changed.

    Resolve:
        Go back to the page *Account*, reload it and try again.
    """

    title = _("The account could not be changed")
    guide = "tutorial/account.html"
    guide_title = _("Your account")


class NoGitHubAccount(AccountError):
    """The account has no GitHub identity, as it was created another way than with GitHub.

    Resolve:
        Sign out and sign in with GitHub.

    Context:
        Accounts of the dashboard come from GitHub. An account without a GitHub identity was
        created another way, such as with ``manage.py createsuperuser``.

    Note:
        The detail is the name of the account.
    """

    title = _("The account has no GitHub identity")
    status = 403


class UnknownPreference(AccountError):
    """The form of the preferences sent a language or colors that the dashboard does not know.

    Resolve:
        Reload the page *Account*, choose the preferences again and save them.

    Context:
        The form may be from an older version of the dashboard, which knew other languages or
        colors.

    Note:
        The detail names the field and its value.
    """

    title = _("Unknown preference")


class AccountDeletionNotConfirmed(AccountError):
    """The account was not deleted: the GitHub handle typed to confirm it does not match.

    Resolve:
        Type your GitHub handle, as the page *Account* shows it after *@*, into the field of the
        red area, and press the button again.

    Context:
        The case of the letters and an *@* before the GitHub handle do not matter.

    Note:
        The detail is the text that was typed.
    """

    title = _("Type your GitHub handle to delete the account")
    status = 400


class AccountOwnsSharedProjects(AccountError):
    """The account was not deleted: it is the only owner of projects that others share.

    Resolve:
        On the tab *Settings → Collaborators* of each project the page lists, give another
        person the role *own*, or delete the project; then delete the account.

    Context:
        A project always has an owner.

    Note:
        The detail lists the projects by the names in their addresses.
    """

    title = _("You are the only owner of shared projects")
    status = 409
