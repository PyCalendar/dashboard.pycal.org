"""The condition ``ci_fails``: a check of a pull request failed."""

from pycal_dashboard.conditions.condition.ci_passes import CiPasses
from pycal_dashboard.models import PullRequestState


class CiFails(CiPasses):
    """The continuous integration of a pull request fails.

    Holds when a check run or commit status of its last commit failed, timed out, was
    cancelled or needs an action. A pull request whose checks still run is neither passing nor
    failing.
    """

    id = "ci_fails"
    title = "CI fails"
    description = "A check of the last commit of a pull request failed."

    @classmethod
    def assess(cls, issue, values: dict) -> bool:
        """Whether a check failed.

        Args:
            issue: The pull request.
            values: Nothing: the condition has no inputs.

        Returns:
            True if one failed.
        """
        return issue.pull_state.checks == PullRequestState.FAILURE
