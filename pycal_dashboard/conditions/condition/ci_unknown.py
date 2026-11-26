"""The condition ``ci_unknown``: the result of the checks of a pull request is not known."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils.translation import gettext

from pycal_dashboard.conditions.condition.base import Condition
from pycal_dashboard.conditions.condition.ci_passes import CiPasses
from pycal_dashboard.conditions.evidence import Evidence
from pycal_dashboard.conditions.spec.checks import ChecksData
from pycal_dashboard.conditions.spec.issue import IssueData

if TYPE_CHECKING:
    from pycal_dashboard.conditions.state.scope import Scope
    from pycal_dashboard.models import Issue, Project


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

    def assess(self, issue: Issue) -> bool:
        """Whether the result of the checks is not known.

        Parameters:
            issue: The pull request.

        Returns:
            True if ``ci_passes`` cannot be assessed.
        """
        return CiPasses().check(issue) is None

    def evidence(
        self, issue: Issue, scope: Scope | None = None, project: Project | None = None
    ) -> list[Evidence]:
        """Why the result is not known: the pull request is closed or merged; else its checks.

        Parameters:
            issue: The pull request.
            scope: Not used.
            project: Not used.

        Returns:
            The reason with the link to the pull request, or the link to its checks.
        """
        if issue.merged is not None:
            reason = gettext("Merged: the checks are read for open pull requests only")
            return [Evidence(reason, issue.url)]
        if issue.state != issue.OPEN:
            reason = gettext("Closed: the checks are read for open pull requests only")
            return [Evidence(reason, issue.url)]
        return ChecksData().evidence(issue)
