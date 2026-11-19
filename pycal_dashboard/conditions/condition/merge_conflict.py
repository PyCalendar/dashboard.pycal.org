"""The condition ``merge_conflict``: a pull request cannot be merged because of a conflict."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pycal_dashboard.conditions.condition.base import Condition
from pycal_dashboard.conditions.spec.pull_request import PullRequestData

if TYPE_CHECKING:
    from pycal_dashboard.models import Issue


class MergeConflict(Condition):
    """A pull request has a merge conflict.

    Holds when GitHub says that the pull request cannot be merged into its base branch
    because they changed the same lines (``mergeable_state`` is ``dirty``).
    """

    id = "merge_conflict"
    title = "Merge conflict"
    description = "A pull request has a merge conflict with its base branch."
    data = (PullRequestData(),)

    @classmethod
    def assess(cls, issue: Issue, values: dict) -> bool:
        """Whether the pull request has a conflict.

        Parameters:
            issue: The pull request.
            values: Nothing: the condition has no inputs.

        Returns:
            True if it has a conflict.
        """
        state = issue.pull_state
        return state.mergeable is False and state.mergeable_state == "dirty"
