"""The group of the type of the author: owner, member, collaborator, contributor, first-timer."""

from __future__ import annotations

from django.utils.translation import gettext_noop

from pycal_dashboard.conditions.author_types import HELP, TYPES
from pycal_dashboard.conditions.condition.author_type import AuthorType
from pycal_dashboard.conditions.group.switches import SwitchesGroup


class AuthorTypeGroup(SwitchesGroup):
    """The type of the author of a pull request: the condition ``author_type``.

    A switch for each type; they are exclusive, as an author has exactly one type for a pull
    request, so the opposite of some types is the others.
    """

    id = "author_type"
    title = gettext_noop("Type of author")
    switches = tuple((name, AuthorType, text) for name, (_a, text) in TYPES.items())
    exclusive = tuple(TYPES)
    phrase = (
        gettext_noop("its author is %(states)s"),
        gettext_noop("its author is not %(states)s"),
    )
    words = {
        "owner": gettext_noop("an owner"),
        "member": gettext_noop("a member"),
        "collaborator": gettext_noop("a collaborator"),
        "contributor": gettext_noop("a contributor"),
        "first_timer": gettext_noop("a first-timer"),
    }
    help = HELP
    docs = "reference/conditions/author_type.html"

    @classmethod
    def spec_of(cls, name: str) -> dict:
        """The condition ``author_type`` of one type.

        Parameters:
            name: The type, such as ``contributor``.

        Returns:
            Its spec.
        """
        return {"id": AuthorType.id, "types": (name,)}

    @classmethod
    def specs(cls, choices: tuple[str, ...]) -> list[dict]:
        """The condition ``author_type`` of the types that are on.

        Parameters:
            choices: The types.

        Returns:
            Its spec.
        """
        return [{"id": AuthorType.id, "types": tuple(choices)}]

    @classmethod
    def choices_of(cls, specs: list[dict]) -> tuple[str, ...] | None:
        """The types of the condition ``author_type``.

        Parameters:
            specs: The specs of the conditions.

        Returns:
            The types, in the order of the switches; None for other conditions.
        """
        if len(specs) != 1 or specs[0].get("id") != AuthorType.id:
            return None
        return tuple(name for name in cls.names() if name in specs[0]["types"]) or None
