"""How far a pull request is: the steps of its project, each with its tasks done or to do."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils.text import capfirst
from django.utils.translation import gettext

from pycal_dashboard.conditions.group.conjunction import Conjunction
from pycal_dashboard.conditions.state.scope import Scope
from pycal_dashboard.models import StepSkip
from pycal_dashboard.services.skip_link import SkipLink
from pycal_dashboard.services.step_overrides import StepOverrides
from pycal_dashboard.step_template import expand, values_of

from .step_progress import StepProgress
from .task import Task

if TYPE_CHECKING:
    from pycal_dashboard.models import Issue, Project
    from pycal_dashboard.services.column_results import ColumnResults


class PullRequestProgress:
    """The steps of a project for one pull request, as its page shows them.

    A task is a condition in force of the filter of a step. It is to do while the filter shows
    the pull request by it, as
    :class:`~pycal_dashboard.services.step_assignment.StepAssignment` decides: the pull request
    is in the left-most step with a task to do. A task that a person skipped is not to do. A
    step without a task to do is complete.
    """

    def __init__(
        self,
        issue: Issue,
        project: Project,
        scope: Scope | None = None,
        results: ColumnResults | None = None,
        overrides: StepOverrides | None = None,
        badge_alt: str | None = None,
    ):
        """Find the tasks of every step of the project for a pull request.

        Parameters:
            issue: The pull request.
            project: The project whose steps it goes through.
            scope: The repositories of the project that the person sees, in which the states
                of the author are counted; all of the project when None.
            results: The results of the columns of the repositories, used where the cache
                has them; else each condition is evaluated for the pull request.
            overrides: The skips of the steps, read once for many pull requests; those of this
                pull request when None.
            badge_alt: The alternative text of the badge in the texts of the steps
                (``{pr_badge}``); None for the text of the badge, such as ``Triage 3/4``, where
                the texts are made again when the badge changes, as on the pages.
        """
        scope = scope or Scope.of(project)
        overrides = overrides or StepOverrides(project, [issue])
        self.issue = issue
        self.project = project
        self.scope = scope
        self.steps: list[StepProgress] = []
        self._values: dict[str, str] | None = None  # see values(), once the step is known
        self.badge_alt = badge_alt
        for number, step in enumerate(project.steps.select_related("filter"), 1):
            progress = StepProgress(step, number, skip=overrides.skip(issue, step))
            for column in Conjunction.of_values(step.filter.columns):
                value = column.encode()  # of a column, or of columns joined by AND
                if not column.active:  # off: no part of the filter
                    continue
                cached = results.cached(column) if results else None
                if cached is not None and issue.pk in cached:
                    result = cached[issue.pk]
                else:
                    result = column.applies(issue, scope)
                if column.skips:  # a condition of Skip if: it applies, the step is skipped
                    if result is True and progress.skip is None:
                        progress.skip = StepSkip(
                            step=step, issue=issue, reason=capfirst(str(column.sentence))
                        )
                    continue
                notes = (step.conditions or {}).get(value, {})
                skipped = overrides.check_skip(issue.pk, step, value)
                progress.tasks.append(
                    Task(
                        value,
                        column,
                        result,
                        column.shows(result) and skipped is None,
                        notes.get("summary", ""),  # expanded below, with the badge
                        notes.get("description", ""),
                        skip=skipped,
                    )
                )
            progress.tasks.sort(key=lambda task: not task.todo)  # stable: to do first
            self.steps.append(progress)
        # the pull request is in the step a person chose with its label, else in the left-most
        # step with a task to do that it does not skip
        chosen = overrides.chosen(issue.pk)
        self.current = next((step for step in self.steps if step.step == chosen), None) or next(
            (step for step in self.steps if not step.complete and step.skip is None), None
        )
        if self.current:
            self.current.current = True
        for step in self.steps:  # the badge is known now: the texts of the tasks with it
            values = self.values(step)
            links = SkipLink(project, issue, step.step)
            for task in step.tasks:
                own = links.values(task.value)
                task.skip_urls = {
                    "writers": own["quality_check_skip_url"],
                    "author": own["quality_check_skip_url_author"],
                }
                task.summary = expand(task.summary, values | own)
                task.description = expand(task.description, values | own)
        # it went through all steps when it skipped those with tasks to do
        self.skipped_open = any(not step.complete and step.skip for step in self.steps)
        stage = "past" if self.current or self.skipped_open else "outside"
        for step in self.steps:
            if step.current:
                stage = "current"
            step.stage = stage
            if stage == "current":
                stage = "future"

    def badge_text(self) -> tuple[str, str]:
        """What the badge of the pull request shows.

        Returns:
            Such as ``("Triage", "3/4")``: the step it is in, with its tasks done and all of
            them; ``("Steps", "outside")`` when no task of any step is to do, outside of the
            usual steps; ``("Steps", "none")`` without steps.
        """
        if self.current:
            return self.current.step.name, f"{self.current.done}/{len(self.current.tasks)}"
        if self.steps:
            return gettext("Steps"), gettext("outside")
        return gettext("Steps"), gettext("none")

    def values(self, step: StepProgress | None = None) -> dict[str, str]:
        """The values of the variables of the texts of a step for the pull request.

        Parameters:
            step: The step; None for the texts of no step.

        Returns:
            The values, with the alternative text of ``pr_badge``: ``badge_alt``, else the
            text of the badge; with a step, its links to skip it.
        """
        if self._values is None:
            alt = " ".join(self.badge_text()) if self.badge_alt is None else self.badge_alt
            self._values = values_of(self.issue, self.project, alt=alt)
        if step is None:
            return self._values
        return (
            self._values
            | {
                "step_name": step.step.name,
                "step_number": str(step.number),
                "step_id": str(step.step.pk),
            }
            | SkipLink(self.project, self.issue, step.step).values()
        )

    @property
    def visible(self) -> list[StepProgress]:
        """The steps of the bar: those not hidden, and the one the pull request is in."""
        return [step for step in self.steps if not step.step.hidden or step.current]

    @property
    def outside(self) -> bool:
        """Whether the pull request is outside of the usual steps: no task of any step is to do.

        Such as a merged pull request, or one that none of the filters of the steps shows.
        """
        return bool(self.steps) and self.current is None and not self.skipped_open

    def chosen(self, number: int | str | None) -> StepProgress | None:
        """The step to show below the bar.

        Parameters:
            number: The id of a step that was clicked, or None.

        Returns:
            That step, also a hidden one; else the step the pull request is in; else the last
            step of the bar; None without steps.
        """
        for step in self.steps:
            if str(step.step.pk) == str(number):
                return step
        visible = self.visible
        return self.current or (visible[-1] if visible else None)

    def find_evidence(self, steps: list[StepProgress]) -> None:
        """Find the evidence of the tasks of steps, which only the page of the pull request shows.

        Parameters:
            steps: The steps, such as the one shown below the bar.
        """
        for step in steps:
            for task in step.tasks:
                task.evidence = task.column.evidence(self.issue, self.scope, self.project)

    def data(self) -> dict:
        """The progress for the JSON of the page.

        Returns:
            ``step``, the id of the step the pull request is in (None when it is in none),
            ``outside``, whether it is outside of the usual steps, and ``steps``, each with its
            ``id``, ``name``, ``number``, ``hidden``, ``skipped`` (not why), ``complete``,
            ``done``, ``total`` and
            ``tasks``: their ``condition``, ``sentence``, ``state`` (``todo``, ``done``,
            ``skipped`` or ``unknown``), ``skipped`` (not why), ``summary`` and
            ``evidence`` (each with ``text`` and ``url``; empty until it is found).
        """
        return {
            "step": self.current.step.pk if self.current else None,
            "outside": self.outside,
            "steps": [
                {
                    "id": step.step.pk,
                    "name": step.step.name,
                    "number": step.number,
                    "hidden": step.step.hidden,
                    "skipped": step.skip is not None,
                    "complete": step.complete,
                    "done": step.done,
                    "total": len(step.tasks),
                    "tasks": [
                        {
                            "condition": task.value,
                            "sentence": capfirst(str(task.column.sentence)),
                            "state": task.state,
                            "skipped": task.skip is not None,
                            "summary": task.summary,
                            "evidence": [found.data() for found in task.evidence],
                        }
                        for task in step.tasks
                    ],
                }
                for step in self.steps
            ],
        }
