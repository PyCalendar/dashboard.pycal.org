"""The group of the type of the author: owner, member, collaborator, contributor, first-timer."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils.translation import gettext_noop

from pycal_dashboard.conditions.author_types import HELP, TYPES
from pycal_dashboard.conditions.condition.author_type import AuthorType
from pycal_dashboard.conditions.evidence import Evidence
from pycal_dashboard.conditions.group.switches import SwitchesGroup

if TYPE_CHECKING:
    from pycal_dashboard.conditions.state.scope import Scope
    from pycal_dashboard.models import Issue, Project


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
    def results(cls, issue: Issue, scope: Scope | None = None) -> dict[str, bool | None]:
        """Whether the author is of each type.

        Parameters:
            issue: The pull request.
            scope: Not used: the type is of the pull request itself.

        Returns:
            The result of each type by its name; None while the type is not known.
        """
        return {name: AuthorType.check(issue, {"types": (name,)}) for name in TYPES}

    @classmethod
    def evidence(
        cls,
        issue: Issue,
        choices: tuple[str, ...],
        scope: Scope | None = None,
        project: Project | None = None,
    ) -> list[Evidence]:
        """The pull request on GitHub, which shows its author.

        Parameters:
            issue: The pull request.
            choices: The types that are on.
            scope: Not used.
            project: Not used.

        Returns:
            The link.
        """
        return AuthorType.evidence(issue, {"types": choices}, scope, project)
