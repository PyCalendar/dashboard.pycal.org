"""The condition ``pr_sync``: the PR Sync of the project is on for a pull request."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils.translation import gettext

from pycal_dashboard.conditions.condition.dashboard_condition import DashboardCondition
from pycal_dashboard.conditions.evidence import Evidence
from pycal_dashboard.models import PullRequestComment

if TYPE_CHECKING:
    from pycal_dashboard.conditions.state.scope import Scope
    from pycal_dashboard.models import Issue, Project


class PrSyncOn(DashboardCondition):
    """The PR Sync of the project is on for a pull request.

    Holds when the GitHub App wrote the Status Message of the project as a comment on the pull
    request, because it is in the scope of the message (``PullRequestComment``). It is data of
    the dashboard: it is known for the pull requests of a project.
    """

    id = "pr_sync"
    title = "PR Sync on"
    description = "The PR Sync of the project is on for a pull request: it has its Status Message."

    def assess(self, issue: Issue, scope: Scope | None = None) -> bool:
        """Whether the pull request has the Status Message of the project.

        Parameters:
            issue: The pull request.
            scope: The repositories and the project.

        Returns:
            True if it has.
        """
        return issue.pk in (scope.synced() or set())

    def evidence(
        self, issue: Issue, scope: Scope | None = None, project: Project | None = None
    ) -> list[Evidence]:
        """The Status Message on GitHub, else the tab PR Sync of the project.

        Parameters:
            issue: The pull request.
            scope: Not used.
            project: The project.

        Returns:
            The link; none without a project.
        """
        if project is None:
            return []
        comment = PullRequestComment.objects.filter(project=project, issue=issue).first()
        if comment is not None:
            url = f"{issue.url}#issuecomment-{comment.github_id}"
            return [Evidence(gettext("PR Status Message on GitHub"), url)]
        return [Evidence(gettext("The PR Sync of the project"), project.path("message/"))]
