"""The condition ``open``: a pull request is open."""

from pycal_dashboard.conditions.condition.base import Condition
from pycal_dashboard.conditions.spec.issue import IssueData
from pycal_dashboard.models import Issue


class Open(Condition):
    """A pull request is open.

    Holds while the pull request is neither merged nor closed; a draft is open too.
    """

    id = "open"
    title = "Open"
    description = "A pull request is open."
    data = (IssueData(),)

    @classmethod
    def assess(cls, issue: Issue, values: dict) -> bool:
        """Whether the pull request is open.

        Parameters:
            issue: The pull request.
            values: Nothing: the condition has no inputs.

        Returns:
            True if it is open.
        """
        return issue.state == Issue.OPEN
