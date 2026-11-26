"""The condition ``auto_merge_enabled``: a pull request merges itself when it may."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pycal_dashboard.conditions.condition.base import Condition
from pycal_dashboard.conditions.spec.pull_request import PullRequestData

if TYPE_CHECKING:
    from pycal_dashboard.models import Issue


class AutoMergeEnabled(Condition):
    """Auto-merge is enabled on a pull request.

    Holds when someone enabled auto-merge: GitHub merges the pull request as soon as its
    requirements, such as reviews and checks, are met.
    """

    id = "auto_merge_enabled"
    title = "Auto-merge enabled"
    description = "Auto-merge is enabled on a pull request."
    data = (PullRequestData(),)

    def assess(self, issue: Issue) -> bool:
        """Whether auto-merge is enabled.

        Parameters:
            issue: The pull request.

        Returns:
            True if it is enabled.
        """
        return issue.pull_state.auto_merge
