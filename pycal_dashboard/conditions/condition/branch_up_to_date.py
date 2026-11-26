"""The condition ``branch_up_to_date``: a pull request is up to date with its base."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pycal_dashboard.conditions.condition.base import Condition
from pycal_dashboard.conditions.spec.issue import IssueData
from pycal_dashboard.conditions.spec.pull_request import PullRequestData

if TYPE_CHECKING:
    from pycal_dashboard.models import Issue

# what GitHub says of a branch that has neither a conflict nor is behind its base
NOT_UP_TO_DATE = {"behind", "dirty"}


class BranchUpToDate(Condition):
    """The branch of a pull request is up to date with its base branch.

    Holds when the pull request is neither behind its base branch nor has a conflict with it.

    Special case: a merged pull request is always up to date. Its branch is in the base branch,
    so it cannot be behind it or in conflict with it, and GitHub no longer tells the state of
    its branch; the condition holds without that data. ``branch_outdated`` and
    ``merge_conflict`` do not hold for it, accordingly.
    """

    id = "branch_up_to_date"
    title = "Branch up to date"
    description = "The branch of a pull request is up to date with its base branch."
    data = (IssueData(), PullRequestData())
    shown = (PullRequestData(),)

    @classmethod
    def complete(cls, issue: Issue) -> bool:
        """A merged pull request needs no state of its branch.

        Parameters:
            issue: The pull request.

        Returns:
            True if it was merged, or its state is complete.
        """
        return issue.merged is not None or super().complete(issue)

    def assess(self, issue: Issue) -> bool:
        """Whether the branch is up to date.

        Parameters:
            issue: The pull request.

        Returns:
            True if it was merged, or is neither behind nor in conflict.
        """
        if issue.merged is not None:
            return True
        return issue.pull_state.mergeable_state not in NOT_UP_TO_DATE
