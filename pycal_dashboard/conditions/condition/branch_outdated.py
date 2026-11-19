"""The condition ``branch_outdated``: the branch of a pull request is behind its base."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pycal_dashboard.conditions.condition.base import Condition
from pycal_dashboard.conditions.spec.pull_request import PullRequestData

if TYPE_CHECKING:
    from pycal_dashboard.models import Issue


class BranchOutdated(Condition):
    """The branch of a pull request is out of date.

    Holds when its base branch has commits that the branch of the pull request does not have,
    and the repository requires branches to be up to date before merging (``mergeable_state``
    is ``behind``). A merged pull request is not out of date.
    """

    id = "branch_outdated"
    title = "Branch out of date"
    description = "The branch of a pull request is behind its base branch."
    data = (PullRequestData(),)

    @classmethod
    def complete(cls, issue: Issue) -> bool:
        """A merged pull request needs no state of its branch.

        Parameters:
            issue: The pull request.

        Returns:
            True if it was merged, or its state is complete.
        """
        return issue.merged is not None or super().complete(issue)

    @classmethod
    def assess(cls, issue: Issue, values: dict) -> bool:
        """Whether the branch is behind its base.

        Parameters:
            issue: The pull request.
            values: Nothing: the condition has no inputs.

        Returns:
            True if it is behind.
        """
        if issue.merged is not None:
            return False
        return issue.pull_state.mergeable_state == "behind"
