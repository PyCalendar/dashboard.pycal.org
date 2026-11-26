"""The condition ``ci_fails``: a check of a pull request failed."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pycal_dashboard.conditions.condition.ci_passes import CiPasses
from pycal_dashboard.models import PullRequestState

if TYPE_CHECKING:
    from pycal_dashboard.models import Issue


class CiFails(CiPasses):
    """The continuous integration of a pull request fails.

    Holds when a check run or commit status of its last commit failed, timed out, was
    cancelled or needs an action. While checks run, the last complete result counts.
    """

    id = "ci_fails"
    title = "CI fails"
    description = "A check of the last commit of a pull request failed."

    def assess(self, issue: Issue) -> bool:
        """Whether a check failed.

        Parameters:
            issue: The pull request.

        Returns:
            True if one failed.
        """
        return issue.pull_state.checks_complete == PullRequestState.FAILURE
