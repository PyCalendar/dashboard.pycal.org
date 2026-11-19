"""The condition ``ci_unknown``: the result of the checks of a pull request is not known."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pycal_dashboard.conditions.condition.base import Condition
from pycal_dashboard.conditions.condition.ci_passes import CiPasses
from pycal_dashboard.conditions.spec.issue import IssueData

if TYPE_CHECKING:
    from pycal_dashboard.models import Issue


class CiUnknown(Condition):
    """The result of the continuous integration of a pull request is not known.

    Holds when neither ``ci_passes`` nor ``ci_fails`` can be assessed: the site has not read
    the checks of its last commit, such as for a closed pull request or while the GitHub App
    may not read checks and statuses, or its checks never completed. Exactly one of
    ``ci_passes``, ``ci_fails`` and ``ci_unknown`` holds for every pull request.
    """

    id = "ci_unknown"
    title = "CI unknown"
    description = "The result of the checks of a pull request is not known."
    data = (IssueData(),)

    @classmethod
    def assess(cls, issue: Issue, values: dict) -> bool:
        """Whether the result of the checks is not known.

        Parameters:
            issue: The pull request.
            values: Nothing: the condition has no inputs.

        Returns:
            True if ``ci_passes`` cannot be assessed.
        """
        return CiPasses.check(issue, {}) is None
