"""The condition ``auto_merge_enabled``: a pull request merges itself when it may."""

from pycal_dashboard.conditions.condition.base import Condition
from pycal_dashboard.conditions.spec.pull_request import PullRequestData


class AutoMergeEnabled(Condition):
    """Auto-merge is enabled on a pull request.

    Holds when someone enabled auto-merge: GitHub merges the pull request as soon as its
    requirements, such as reviews and checks, are met.
    """

    id = "auto_merge_enabled"
    title = "Auto-merge enabled"
    description = "Auto-merge is enabled on a pull request."
    data = (PullRequestData(),)

    @classmethod
    def assess(cls, issue, values: dict) -> bool:
        """Whether auto-merge is enabled.

        Args:
            issue: The pull request.
            values: Nothing: the condition has no inputs.

        Returns:
            True if it is enabled.
        """
        return issue.pull_state.auto_merge
