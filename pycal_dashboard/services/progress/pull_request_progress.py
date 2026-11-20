"""How far a pull request is: the steps of its project, each with its tasks done or to do."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils.text import capfirst

from pycal_dashboard.conditions.group.column import Column
from pycal_dashboard.step_template import expand, values_of

from .step_progress import StepProgress
from .task import Task

if TYPE_CHECKING:
    from pycal_dashboard.models import Issue, Project


class PullRequestProgress:
    """The steps of a project for one pull request, as its page shows them.

    A task is a condition in force of the filter of a step. It is to do while the filter shows
    the pull request by it, as
    :class:`~pycal_dashboard.services.step_assignment.StepAssignment` decides: the pull request
    is in the left-most step with a task to do. A step without a task to do is complete.
    """

    def __init__(self, issue: Issue, project: Project):
        """Find the tasks of every step of the project for a pull request.

        Parameters:
            issue: The pull request.
            project: The project whose steps it goes through.
        """
        self.issue = issue
        self.steps: list[StepProgress] = []
        for number, step in enumerate(project.steps.select_related("filter"), 1):
            values = values_of(issue, project, step)
            progress = StepProgress(step, number)
            for value in step.filter.columns:
                column = Column.decode(value)
                if column.filter == "all":  # off: no part of the filter
                    continue
                result = column.applies(issue)
                notes = (step.conditions or {}).get(value, {})
                progress.tasks.append(
                    Task(
                        value,
                        column,
                        result,
                        column.shows(result),
                        expand(notes.get("summary", ""), values),
                        expand(notes.get("description", ""), values),
                    )
                )
            progress.tasks.sort(key=lambda task: not task.todo)  # stable: to do first
            self.steps.append(progress)
        self.current = next((step for step in self.steps if not step.complete), None)
        if self.current:
            self.current.current = True

    def chosen(self, number: int | str | None) -> StepProgress | None:
        """The step to show below the bar.

        Parameters:
            number: The id of a step that was clicked, or None.

        Returns:
            That step; else the step the pull request is in; else the last one; None without
            steps.
        """
        for step in self.steps:
            if str(step.step.pk) == str(number):
                return step
        return self.current or (self.steps[-1] if self.steps else None)

    def data(self) -> dict:
        """The progress for the JSON of the page.

        Returns:
            ``step``, the id of the step the pull request is in (None when it is in none), and
            ``steps``, each with its ``id``, ``name``, ``number``, ``complete``, ``done``,
            ``total`` and ``tasks``: their ``condition``, ``sentence``, ``state`` and
            ``summary``.
        """
        return {
            "step": self.current.step.pk if self.current else None,
            "steps": [
                {
                    "id": step.step.pk,
                    "name": step.step.name,
                    "number": step.number,
                    "complete": step.complete,
                    "done": step.done,
                    "total": len(step.tasks),
                    "tasks": [
                        {
                            "condition": task.value,
                            "sentence": capfirst(str(task.column.sentence)),
                            "state": task.state,
                            "summary": task.summary,
                        }
                        for task in step.tasks
                    ],
                }
                for step in self.steps
            ],
        }
