"""The condition ``draft``: a pull request is a draft."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pycal_dashboard.conditions.condition.base import Condition
from pycal_dashboard.conditions.spec.issue import IssueData

if TYPE_CHECKING:
    from pycal_dashboard.models import Issue

# the data version (DATA_VERSION) since which the site keeps whether it is a draft
SINCE = 5


class Draft(Condition):
    """A pull request is a draft: its author marked it as not ready for review yet.

    Holds while the pull request is a draft, as GitHub tells with each pull request
    (``draft``); a draft is open, too. Its author makes it ready for review on GitHub.
    """

    id = "draft"
    title = "Draft"
    description = "A pull request is a draft: not ready for review yet."
    data = (IssueData(),)

    @classmethod
    def complete(cls, issue: Issue) -> bool:
        """Whether a draft is kept since data version 5.

        Parameters:
            issue: The pull request.

        Returns:
            True if its repository was read with it.
        """
        return issue.repository.data_version >= SINCE and super().complete(issue)

    @classmethod
    def assess(cls, issue: Issue, values: dict) -> bool:
        """Whether the pull request is a draft.

        Parameters:
            issue: The pull request.
            values: Nothing: the condition has no inputs.

        Returns:
            True if it is a draft.
        """
        return issue.draft
