"""The step of a pull request: the left-most step whose filter shows it."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pycal_dashboard.conditions.group.column import Column
from pycal_dashboard.conditions.state.scope import Scope
from pycal_dashboard.models import Issue
from pycal_dashboard.services.step_overrides import StepOverrides

if TYPE_CHECKING:
    from pycal_dashboard.models import Project, PullRequestStep
    from pycal_dashboard.services.column_results import ColumnResults


class StepAssignment:
    """Which step of a project each pull request is in.

    A pull request is in a step when one of the conditions in force of its filter applies to
    it, as the column shows it: the conditions are failures that keep it from being merged.
    Steps more to the left come first; a pull request is in the left-most step that shows it,
    and in none when none does. A step whose filter has no condition in force shows none.
    A pull request is not in a step that it skips (``StepOverrides``).
    """

    def __init__(self, project: Project, scope: Scope | None = None):
        """The steps of a project, in their order, with the columns of their filters.

        Parameters:
            project: The project.
            scope: The repositories in which the states of the authors are counted; all of
                the project when None.
        """
        self.scope = scope or Scope.of(project)
        self.overrides = StepOverrides(project)
        self.steps: list[tuple[PullRequestStep, list[Column]]] = []
        for step in project.steps.select_related("filter"):
            columns = [Column.decode(value) for value in step.filter.columns]
            self.steps.append((step, [c for c in columns if c.filter != "all"]))

    def step_of_all(self, results: ColumnResults) -> dict[int, PullRequestStep | None]:
        """The step of every pull request at once, from the cached results of the columns.

        Parameters:
            results: The results of the columns for the pull requests of the repositories.

        Returns:
            The step by the id of the pull request; None for those in no step.
        """
        found: dict[int, PullRequestStep | None] = dict.fromkeys(results.ids())
        logins = dict(Issue.objects.filter(pk__in=list(found)).values_list("pk", "author__login"))
        for step, columns in reversed(self.steps):  # the left-most step comes last and wins
            shown = [(column, results.of(column)) for column in columns]
            for pk in found:
                if self.overrides.skips_step(pk, logins.get(pk) or "", step):
                    continue
                if any(column.shows(cells.get(pk)) for column, cells in shown):
                    found[pk] = step
        return found

    def step_of(self, issue: Issue) -> PullRequestStep | None:
        """The step of a pull request.

        Parameters:
            issue: The pull request, with its labels and state.

        Returns:
            The left-most step whose filter shows it and that it does not skip; None if none
            does.
        """
        for step, columns in self.steps:
            if self.overrides.skip(issue, step) is not None:
                continue
            if any(column.shows(column.applies(issue, self.scope)) for column in columns):
                return step
        return None
