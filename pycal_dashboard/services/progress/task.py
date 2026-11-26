"""A task of a step for one pull request: a condition in force of the filter of the step."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from django.utils.html import strip_tags
from django.utils.text import capfirst

from pycal_dashboard.conditions.evidence import Evidence
from pycal_dashboard.conditions.group.column import Column
from pycal_dashboard.conditions.group.conjunction import Conjunction
from pycal_dashboard.markdown_text import render

if TYPE_CHECKING:
    from pycal_dashboard.models import CheckSkip


@dataclass
class Task:
    """A task of a step: a condition in force of its filter, for one pull request.

    Attributes:
        value: The column of the condition, as the filter keeps it; for columns joined by AND,
            their values joined with ``&`` (``Conjunction.encode``).
        column: The column of the condition, or the columns joined by AND.
        result: Whether the condition applies to the pull request (for an AND: whether all of
            its conditions hold); None while not known.
        todo: Whether the task keeps the pull request in the step: the filter shows it, and
            nobody skipped it.
        summary: The summary of the task, expanded with the values of the pull request.
        description: The description of the task, expanded with the same values.
        evidence: The least that shows why its condition holds or not, once it is found
            (:meth:`PullRequestProgress.find_evidence
            <pycal_dashboard.services.progress.pull_request_progress.PullRequestProgress.find_evidence>`).
        skip: Why the pull request skips the quality check (``CheckSkip``), None when it does
            not.
        skip_urls: The addresses that open the dialog to skip it: ``writers`` and ``author``
            (``{quality_check_skip_url}`` and ``{quality_check_skip_url_author}``).
    """

    value: str
    column: Column | Conjunction
    result: bool | None
    todo: bool
    summary: str = ""
    description: str = ""
    evidence: list[Evidence] = field(default_factory=list)
    skip: CheckSkip | None = None
    skip_urls: dict[str, str] = field(default_factory=dict)

    @property
    def state(self) -> str:
        """``todo``, ``done``, ``skipped``, or ``unknown`` while its data is not complete.

        A quality check that a person skipped is ``skipped`` unless its condition is met.
        """
        if self.todo:
            return "todo"
        if self.skip is not None and (self.result is None or self.column.shows(self.result)):
            return "skipped"
        return "unknown" if self.result is None else "done"

    @property
    def name(self) -> str:
        """The quality check as text: its summary without Markdown, else its condition."""
        text = strip_tags(render(self.summary)) if self.summary else ""
        return " ".join(text.split()) or capfirst(str(self.column.sentence))

    @property
    def skippable(self) -> bool:
        """Whether a person may skip it: it is to do or not known, and not skipped."""
        return self.state in ("todo", "unknown")
