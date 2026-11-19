"""The condition ``ci_passes``: the checks of a pull request passed."""

from pycal_dashboard.conditions.condition.base import Condition
from pycal_dashboard.conditions.spec.checks import ChecksData
from pycal_dashboard.conditions.spec.pull_request import PullRequestData
from pycal_dashboard.models import PullRequestState


class CiPasses(Condition):
    """The continuous integration of a pull request passes.

    Holds when every check run and commit status of its last commit succeeded, or was skipped
    or neutral. A pull request whose checks still run is neither passing nor failing.
    """

    id = "ci_passes"
    title = "CI passes"
    description = "The checks of the last commit of a pull request passed."
    data = (PullRequestData(), ChecksData())

    @classmethod
    def assess(cls, issue, values: dict) -> bool:
        """Whether the checks passed.

        Args:
            issue: The pull request.
            values: Nothing: the condition has no inputs.

        Returns:
            True if they passed.
        """
        return issue.pull_state.checks == PullRequestState.SUCCESS
