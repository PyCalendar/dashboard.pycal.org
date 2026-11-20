"""A step of a project with the tasks of one pull request in it."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .task import Task

if TYPE_CHECKING:
    from pycal_dashboard.models import PullRequestStep


@dataclass
class StepProgress:
    """A step of the project with the tasks of one pull request in it.

    Attributes:
        step: The step.
        number: Its place in the bar, counted from 1.
        tasks: Its tasks, those to do first, in the order of the filter.
        current: Whether the pull request is in this step: the left-most one with a task to do.
    """

    step: PullRequestStep
    number: int
    tasks: list[Task] = field(default_factory=list)
    current: bool = False
    # past (complete, left of the current step), current, future (right of it), or outside
    # (the pull request is in no step: every step is gray)
    stage: str = "future"

    @property
    def done(self) -> int:
        """How many tasks are not to do: done, or not known."""
        return sum(not task.todo for task in self.tasks)

    @property
    def complete(self) -> bool:
        """Whether no task of the step is to do."""
        return self.done == len(self.tasks)

    @property
    def squares(self) -> list[str]:
        """The states of the tasks for the bar: done first, then not known, then to do."""
        order = {"done": 0, "unknown": 1, "todo": 2}
        return sorted((task.state for task in self.tasks), key=order.__getitem__)
