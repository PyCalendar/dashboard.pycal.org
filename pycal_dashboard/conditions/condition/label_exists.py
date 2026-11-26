"""The condition ``label_exists``: a pull request has a label."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pycal_dashboard.conditions.condition.base import Condition
from pycal_dashboard.conditions.input.label import LabelInput
from pycal_dashboard.conditions.spec.labels import LabelsData

if TYPE_CHECKING:
    from pycal_dashboard.models import Issue


class LabelExists(Condition):
    """A label exists on a pull request.

    Holds when the pull request has the label of the input ``label``, such as ``needs review``;
    its case does not matter. Its NOT is ``label_absent``: the label is absent.
    """

    id = "label_exists"
    title = "A label exists"
    description = "A label exists on a pull request."
    negation = ("label_absent", "A label is absent", "A label is absent from a pull request.")
    inputs = (LabelInput("label", "Label", "The name of a label of the repository."),)
    data = (LabelsData(),)

    def assess(self, issue: Issue) -> bool:
        """Whether the pull request has the label.

        Parameters:
            issue: The pull request.

        Returns:
            True if it has the label.
        """
        wanted = self.values["label"].lower()  # the labels prefetched with the pull request, if so
        return any(label.name.lower() == wanted for label in issue.labels.all())
