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
    A pull request is not in a step that it skips, and it is in the step that a person chose
    with its status label (``StepOverrides``).
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
        # the conditions of Skip if of each step: one that applies skips the step
        self.skipping: dict[int, list[Column]] = {}
        for step in project.steps.select_related("filter"):
            columns = [Column.decode(value) for value in step.filter.columns]
            self.steps.append((step, [c for c in columns if c.checks]))
            self.skipping[step.pk] = [c for c in columns if c.skips]

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
            skipped = [results.of(column) for column in self.skipping.get(step.pk, [])]
            for pk in found:
                if any(cells.get(pk) is True for cells in skipped):
                    continue
                if self.overrides.chosen(pk) is not None:
                    continue
                if self.overrides.skips_step(pk, logins.get(pk) or "", step):
                    continue
                if any(column.shows(cells.get(pk)) for column, cells in shown):
                    found[pk] = step
        for pk in found:
            found[pk] = self.overrides.chosen(pk) or found[pk]
        return found

    def step_of(self, issue: Issue, chosen: bool = True) -> PullRequestStep | None:
        """The step of a pull request.

        Parameters:
            issue: The pull request, with its labels and state.
            chosen: Whether the step that a person chose with its label counts; False for the
                step of its conditions and skips alone.

        Returns:
            The left-most step whose filter shows it and that it does not skip; None if none
            does; the step that a person chose, if any.
        """
        if chosen and self.overrides.chosen(issue.pk) is not None:
            return self.overrides.chosen(issue.pk)
        for step, columns in self.steps:
            if self.overrides.skip(issue, step) is not None:
                continue
            if any(c.applies(issue, self.scope) is True for c in self.skipping.get(step.pk, [])):
                continue
            if any(column.shows(column.applies(issue, self.scope)) for column in columns):
                return step
        return None
