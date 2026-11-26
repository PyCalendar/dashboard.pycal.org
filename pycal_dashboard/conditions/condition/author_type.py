"""The condition ``author_type``: the author of a pull request is of one of some types."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pycal_dashboard.conditions.author_types import TYPES, type_of
from pycal_dashboard.conditions.condition.base import Condition
from pycal_dashboard.conditions.input.multiple_choice import MultipleChoiceInput
from pycal_dashboard.conditions.spec.issue import IssueData

if TYPE_CHECKING:
    from pycal_dashboard.models import Issue

# the data version (DATA_VERSION) since which the site keeps the association of the author
SINCE = 4


class AuthorType(Condition):
    """The author of a pull request is an owner, a member, a collaborator, ...

    Holds when the type of the author, of the association that GitHub tells with the pull
    request (``author_association``), is one of the input ``types``: ``owner``, ``member``,
    ``collaborator``, ``contributor`` (also an imported account, a mannequin) or
    ``first_timer`` (whose first contribution it is, also on GitHub, or without any yet). The
    types are exclusive: an author has exactly one for a pull request.
    """

    id = "author_type"
    title = "Type of author"
    description = "The author of a pull request is an owner, a member, a collaborator, ..."
    inputs = (
        MultipleChoiceInput(
            "types",
            "Types",
            "owner, member, collaborator, contributor and first_timer.",
            choices={name: text for name, (_a, text) in TYPES.items()},
        ),
    )
    data = (IssueData(),)

    @classmethod
    def complete(cls, issue: Issue) -> bool:
        """The association is kept since data version 4.

        Parameters:
            issue: The pull request.

        Returns:
            True if its repository was read with it.
        """
        return issue.repository.data_version >= SINCE and super().complete(issue)

    def assess(self, issue: Issue) -> bool:
        """Whether the type of the author is one of the types.

        Parameters:
            issue: The pull request.

        Returns:
            True if it is.
        """
        return type_of(issue.author_association) in self.values["types"]
