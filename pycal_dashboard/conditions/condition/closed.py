"""The condition ``closed``: a pull request was closed without being merged."""

from pycal_dashboard.conditions.condition.base import Condition
from pycal_dashboard.conditions.spec.issue import IssueData
from pycal_dashboard.models import Issue


class Closed(Condition):
    """A pull request was closed without being merged.

    Holds when the pull request was closed and not merged, as GitHub shows it with the badge
    *Closed*; a merged pull request is ``merged``, not ``closed``.
    """

    id = "closed"
    title = "Closed"
    description = "A pull request was closed without being merged."
    data = (IssueData(),)

    @classmethod
    def assess(cls, issue: Issue, values: dict) -> bool:
        """Whether the pull request was closed without being merged.

        Parameters:
            issue: The pull request.
            values: Nothing: the condition has no inputs.

        Returns:
            True if it was closed and not merged.
        """
        return issue.state == Issue.CLOSED and issue.merged is None
