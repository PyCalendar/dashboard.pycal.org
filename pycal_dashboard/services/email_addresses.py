"""The addresses for the emails of the site: one for each person, verified, if they want it."""

from collections.abc import Iterable

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount

from pycal_dashboard.models import Preferences


def recipients(github_ids: Iterable[str], switch: str) -> list[tuple[str, str]]:
    """The addresses of people for a type of email, with the language of each.

    A person gets an email at their primary address if it is verified; otherwise at their
    newest verified address, so that switching the primary address to one that is not
    verified yet does not stop the emails, nor sends them to an address nobody confirmed.
    People who switched the type of email off, and people without a verified address or an
    account on the site, get none.

    Parameters:
        github_ids: The GitHub ids of the people.
        switch: The field of :class:`~pycal_dashboard.models.Preferences` that switches the
            type of email on and off, such as ``email_permissions``.

    Returns:
        The address and the language ("" for the default) of each person, sorted.
    """
    users = list(
        SocialAccount.objects.filter(
            provider="github", uid__in=[str(i) for i in github_ids]
        ).values_list("user_id", flat=True)
    )
    preferences = {p.user_id: p for p in Preferences.objects.filter(user_id__in=users)}
    chosen: dict[int, str] = {}
    for address in EmailAddress.objects.filter(user_id__in=users, verified=True).order_by(
        "-primary", "-pk"
    ):
        wanted = getattr(preferences.get(address.user_id), switch, True)
        if wanted:
            chosen.setdefault(address.user_id, address.email)
    return sorted(
        (email, getattr(preferences.get(user), "language", "")) for user, email in chosen.items()
    )
