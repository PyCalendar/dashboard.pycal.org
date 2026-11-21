"""The types of the author of a pull request: owner, member, collaborator, contributor, ...

GitHub tells the association of the author with the repository with each issue and pull
request (``author_association``); the types group them, as the insights platform does, but
without its classification of bots. They are exclusive: an author has exactly one type for a
pull request.
"""

from __future__ import annotations

from django.utils.translation import gettext_noop

# the types, the most privileged first, with the associations of GitHub and their texts
TYPES = {
    "owner": (("OWNER",), gettext_noop("owner")),
    "member": (("MEMBER",), gettext_noop("member")),
    "collaborator": (("COLLABORATOR",), gettext_noop("collaborator")),
    "contributor": (("CONTRIBUTOR", "MANNEQUIN"), gettext_noop("contributor")),
    "first_timer": (
        ("FIRST_TIMER", "FIRST_TIME_CONTRIBUTOR", "NONE"),
        gettext_noop("first-timer"),
    ),
}
ALL = tuple(TYPES)
# what the types are, for people
HELP = gettext_noop(
    "The type of the author comes from GitHub, with each pull request: owner of the repository, "
    "member of its organization, collaborator, contributor with earlier contributions, or "
    "first-timer, whose first contribution it is. They are exclusive: an author has exactly one "
    "type for a pull request, the most privileged."
)


def type_of(association: str) -> str:
    """The type of an author by the association of GitHub.

    Parameters:
        association: Such as ``MEMBER`` or ``FIRST_TIME_CONTRIBUTOR``; "" when not known.

    Returns:
        The type, such as ``member``; "" when not known.

    Examples:
        >>> type_of("FIRST_TIME_CONTRIBUTOR"), type_of("member"), type_of("")
        ('first_timer', 'member', '')
    """
    found = association.upper()
    return next((name for name, (associations, _t) in TYPES.items() if found in associations), "")
