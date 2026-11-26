"""The base of the conditions on data of the dashboard, such as the PR Sync of a project."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from pycal_dashboard.conditions.condition.base import Condition
from pycal_dashboard.conditions.spec.dashboard import DashboardData

if TYPE_CHECKING:
    from pycal_dashboard.conditions.state.scope import Scope
    from pycal_dashboard.models import Issue


class DashboardCondition(Condition):
    """A condition on what the dashboard keeps of a pull request in a project.

    It needs the project, which comes with the scope (``Scope.project``): without one, the
    condition is not known. Its results change without an update from GitHub, so a column of it
    is not kept in the cache (``ConditionGroup.cached``).
    """

    data = (DashboardData(),)
    scoped: ClassVar[bool] = True

    def check(self, issue: Issue, scope: Scope | None = None) -> bool | None:
        """Assess the condition, if the project is known.

        Parameters:
            issue: The pull request.
            scope: The repositories and the project.

        Returns:
            True or False; None for an issue or without the project.
        """
        if not issue.pull_request or scope is None or scope.project is None:
            return None
        return self.assess(issue, scope)
