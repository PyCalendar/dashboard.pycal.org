"""The kinds of reviews that conditions and states count: approved, commented, ...

The same choice of kinds is an input of every condition and state that counts reviews
(:class:`~pycal_dashboard.conditions.input.review_kinds.ReviewKindsInput`), and of the page of a
person in a project. All kinds count by default.
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
ALL = tuple(KINDS)
# what a dismissed review is, for people
DISMISSED_HELP = gettext_noop(
    "Dismissed: an approval or a request for changes that a maintainer dismissed later, such as "
    "after new commits; the review stays on GitHub, but no longer counts there."
)


def checked(kinds: Iterable[str] | None) -> tuple[str, ...]:
    """The kinds in their order, each once; all of them for none.

    Parameters:
        kinds: Names of kinds, such as ``("commented", "approved")``; unknown ones are left out.

    Returns:
        The kinds, such as ``("approved", "commented")``.

    Examples:
        >>> checked(["commented", "approved", "commented"]), checked(None) == ALL
        (('approved', 'commented'), True)
    """
    chosen = set(kinds or ())
    return tuple(kind for kind in ALL if kind in chosen) or ALL


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
    return tuple(KINDS[kind][0] for kind in checked(kinds))


def text(kinds: Iterable[str]) -> str:
    """The kinds of reviews for a sentence, such as ``approved or commented``.

    Parameters:
        kinds: The kinds.

    Returns:
        Their texts, translated.
    """
    return (" " + gettext("or") + " ").join(gettext(KINDS[kind][1]) for kind in checked(kinds))
