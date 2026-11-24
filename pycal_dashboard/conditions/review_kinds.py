"""The kinds of reviews that conditions and states count: approved, commented, ...

The same choice of kinds is an input of every condition and state that counts reviews
(:class:`~pycal_dashboard.conditions.input.review_kinds.ReviewKindsInput`), and of the page of a
person in a project. All kinds of states count by default, but a review counts only when its
author is not the author of the pull request; the choice ``own`` counts those, too.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils.translation import gettext, gettext_noop

if TYPE_CHECKING:
    from collections.abc import Iterable

# the kinds by their names in configurations and addresses: the state of GitHub and the text
KINDS = {
    "approved": ("APPROVED", gettext_noop("approved")),
    "changes_requested": ("CHANGES_REQUESTED", gettext_noop("changes requested")),
    "commented": ("COMMENTED", gettext_noop("commented")),
    "dismissed": ("DISMISSED", gettext_noop("dismissed")),
}
ALL = tuple(KINDS)  # the default: all states, without the reviews of authors on their own
# the reviews of the author of a pull request on it, such as a comment as a review
OWN = "own"
# the choices of the switches: the kinds, then the reviews of authors; the state of GitHub and
# the text
CHOICES = {**KINDS, OWN: ("", gettext_noop("by the author of the pull request"))}
# what a dismissed review is, and which reviews count, for people
DISMISSED_HELP = gettext_noop(
    "By default, a review counts only when its author is not the author of the pull request. "
    "Dismissed: an approval or a request for changes that a maintainer dismissed later, such as "
    "after new commits; the review stays on GitHub, but no longer counts there."
)


def checked(kinds: Iterable[str] | None) -> tuple[str, ...]:
    """The kinds in their order, each once; all of them for none; ``own`` last, if chosen.

    Parameters:
        kinds: Names of kinds, such as ``("commented", "approved")``; unknown ones are left out.

    Returns:
        The kinds, such as ``("approved", "commented")``; all states when none is chosen.

    Examples:
        >>> checked(["commented", "approved", "commented"]), checked(None) == ALL
        (('approved', 'commented'), True)
        >>> checked(["own", "approved"]), checked(["own"]) == (*ALL, "own")
        (('approved', 'own'), True)
    """
    chosen = set(kinds or ())
    found = tuple(kind for kind in ALL if kind in chosen) or ALL
    return (*found, OWN) if OWN in chosen else found


def own(kinds: Iterable[str] | None) -> bool:
    """Whether the reviews of the author of a pull request on it count.

    Parameters:
        kinds: Names of kinds; None for the default.

    Returns:
        True when ``own`` is chosen; not by default.

    Examples:
        >>> own(None), own(["approved", "own"])
        (False, True)
    """
    return OWN in set(kinds or ())


def states(kinds: Iterable[str] | None) -> tuple[str, ...]:
    """The states of reviews on GitHub of kinds.

    Parameters:
        kinds: Names of kinds; all of them for none.

    Returns:
        Such as ``("APPROVED", "COMMENTED")``.

    Examples:
        >>> states(["changes_requested"])
        ('CHANGES_REQUESTED',)
    """
    return tuple(KINDS[kind][0] for kind in checked(kinds) if kind in KINDS)


def text(kinds: Iterable[str]) -> str:
    """The kinds of reviews for a sentence, such as ``approved or commented``.

    Parameters:
        kinds: The kinds.

    Returns:
        Their texts, translated; with ``own``, such as ``approved, also by the author of the
        pull request``.

    Examples:
        >>> text(["commented", "approved"]), text(["approved", "own"])
        ('approved or commented', 'approved, also by the author of the pull request')
    """
    chosen = checked(kinds)
    found = (" " + gettext("or") + " ").join(
        gettext(KINDS[kind][1]) for kind in chosen if kind in KINDS
    )
    if OWN in chosen:
        return gettext("%(kinds)s, also by the author of the pull request") % {"kinds": found}
    return found
