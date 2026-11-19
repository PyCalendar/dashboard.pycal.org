"""The condition ``merged``: a pull request was merged."""

from pycal_dashboard.conditions.condition.base import Condition
from pycal_dashboard.conditions.spec.issue import IssueData
from pycal_dashboard.models import Issue


class Merged(Condition):
    """A pull request was merged.

    Holds when the pull request was merged into its base branch.
    """

    id = "merged"
    title = "Merged"
    description = "A pull request was merged."
    data = (IssueData(),)

    @classmethod
    def assess(cls, issue: Issue, values: dict) -> bool:
        """Whether the pull request was merged.

        Parameters:
            issue: The pull request.
            values: Nothing: the condition has no inputs.

        Returns:
            True if it was merged.
        """
        return issue.merged is not None
