"""The condition ``step_skipped``: a pull request skips a step of the project."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.utils.translation import gettext

from pycal_dashboard.conditions.condition.dashboard_condition import DashboardCondition
from pycal_dashboard.conditions.evidence import Evidence

if TYPE_CHECKING:
    from pycal_dashboard.conditions.state.scope import Scope
    from pycal_dashboard.models import Issue, Project


class StepSkipped(DashboardCondition):
    """A pull request skips a step of the project.

    Holds when a writer of the project skipped one of its steps for the pull request
    (``StepSkip``), or when a step skips itself for its author (``PullRequestStep.skip_authors``).
    It is data of the dashboard: it is known for the pull requests of a project.
    """

    id = "step_skipped"
    title = "A step skipped"
    description = (
        "A pull request skips a step of the project, skipped by a person or for its author."
    )

    @classmethod
    def assess(cls, issue: Issue, values: dict, scope: Scope | None = None) -> bool:
        """Whether the pull request skips a step.

        Parameters:
            issue: The pull request.
            values: Nothing: the condition has no inputs.
            scope: The repositories and the project.

        Returns:
            True if it skips one.
        """
        issues, authors = scope.skips() or (set(), set())
        login = issue.author.login.lower() if issue.author_id and issue.author else ""
        return issue.pk in issues or bool(login and login in authors)

    @classmethod
    def evidence(
        cls,
        issue: Issue,
        values: dict,
        scope: Scope | None = None,
        project: Project | None = None,
    ) -> list[Evidence]:
        """The steps of the pull request on the dashboard, which say which one it skips.

        Parameters:
            issue: The pull request.
            values: Not used.
            scope: Not used.
            project: The project.

        Returns:
            The link; none without a project.
        """
        if project is None:
            return []
        path = project.path(f"pull/{issue.number}/")
        text = gettext("Its steps on %(site)s") % {"site": settings.SITE_NAME}
        return [Evidence(text, path)]
