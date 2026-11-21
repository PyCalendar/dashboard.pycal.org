"""A task of a step for one pull request: a condition in force of the filter of the step."""

from __future__ import annotations

from dataclasses import dataclass, field

from pycal_dashboard.conditions.evidence import Evidence
from pycal_dashboard.conditions.group.column import Column


@dataclass
class Task:
    """A task of a step: a condition in force of its filter, for one pull request.

    Attributes:
        value: The column of the condition, as the filter keeps it.
        column: The column of the condition.
        result: Whether the condition applies to the pull request; None while not known.
        todo: Whether the task keeps the pull request in the step: the filter shows it.
        summary: The summary of the task, expanded with the values of the pull request.
        description: The description of the task, expanded with the same values.
        evidence: The least that shows why its condition holds or not, once it is found
            (:meth:`PullRequestProgress.find_evidence
            <pycal_dashboard.services.progress.pull_request_progress.PullRequestProgress.find_evidence>`).
    """

    value: str
    column: Column
    result: bool | None
    todo: bool
    summary: str = ""
    description: str = ""
    evidence: list[Evidence] = field(default_factory=list)

    @property
    def state(self) -> str:
        """``todo``, ``done``, or ``unknown`` while the data of the condition is not complete."""
        if self.todo:
            return "todo"
        return "unknown" if self.result is None else "done"
