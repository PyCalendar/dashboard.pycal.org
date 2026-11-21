"""What the dashboard keeps of a pull request itself: its PR Sync and the skips of its steps."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pycal_dashboard.conditions.spec.base import DataSpec

if TYPE_CHECKING:
    from pycal_dashboard.models import Issue


class DashboardData(DataSpec):
    """Data of the dashboard about a pull request in a project, not of GitHub.

    Whether the PR Sync of the project is on for the pull request (``PullRequestComment``) and
    which of its steps it skips (``StepSkip``, ``PullRequestStep.skip_authors``). Nothing is
    read from GitHub for it, so it is always complete; the project comes with the scope
    (``project`` of :class:`~pycal_dashboard.conditions.state.scope.Scope`).
    """

    id = "dashboard"
    title = "What the dashboard keeps of a pull request: its PR Sync and the skips of its steps"

    def complete(self, issue: Issue) -> bool:
        """The data of the dashboard is always there.

        Parameters:
            issue: The pull request.

        Returns:
            True.
        """
        return True
