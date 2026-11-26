"""A label renamed on GitHub keeps the saved filters that name it working."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from pycal_dashboard.conditions.group.column import Column
from pycal_dashboard.conditions.group.labels import LabelsGroup
from pycal_dashboard.models import PullRequestFilter, PullRequestStep
from pycal_dashboard.step_actions import normalized, renamed

if TYPE_CHECKING:
    from pycal_dashboard.models import Repository


class LabelRename:
    """Rename a label in the saved filters of the projects of its repository.

    GitHub keeps the id of a label when it is renamed: the update of the repository finds the
    label by its id under its new name (``LabelsData.label``). The filters keep the names of
    labels, so a filter that names the old one would no longer find it; this renames it there.
    Labels are matched by their name in every repository of a project, in any case.
    """

    def __init__(self, repository: Repository, old: str, new: str):
        """A rename of a label.

        Parameters:
            repository: The repository of the label.
            old: Its name before.
            new: Its name now.
        """
        self.repository = repository
        self.old = old
        self.new = new

    def column(self, value: str) -> str:
        """A column of a filter, with the new name if it names the old one.

        Parameters:
            value: The column as the filter keeps it.

        Returns:
            The column, renamed or as it was.
        """
        try:
            column = Column.decode(value)
        except Exception:  # a column the filter kept from before: left as it is
            return value
        if column.group is not LabelsGroup or column.choices[1].lower() != self.old.lower():
            return value
        # its AND stays
        return replace(column, choices=(column.choices[0], self.new)).encode()

    def apply(self) -> int:
        """Rename the label in the filters and in the actions of the steps of the projects.

        Returns:
            How many filters and steps changed.
        """
        changed = 0
        steps = PullRequestStep.objects.filter(project__repositories=self.repository)
        for step in steps.distinct():
            actions = renamed(step.actions, self.old, self.new)
            if actions != normalized(step.actions):
                step.actions = actions
                step.save(update_fields=["actions", "updated"])
                changed += 1
        filters = PullRequestFilter.objects.filter(project__repositories=self.repository)
        for saved in filters.distinct():
            columns = [self.column(value) for value in saved.columns]
            if columns != saved.columns:
                saved.columns = columns
                saved.save(update_fields=["columns", "updated"])
                changed += 1
        return changed
