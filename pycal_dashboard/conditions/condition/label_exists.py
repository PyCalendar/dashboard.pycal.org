"""The condition ``label_exists``: a pull request has a label."""

from pycal_dashboard.conditions.condition.base import Condition
from pycal_dashboard.conditions.input.label import LabelInput
from pycal_dashboard.conditions.spec.labels import LabelsData


class LabelExists(Condition):
    """A label exists on a pull request.

    Holds when the pull request has the label of the input ``label``, such as ``needs review``;
    its case does not matter.
    """

    id = "label_exists"
    title = "A label exists"
    description = "A label exists on a pull request."
    inputs = (LabelInput("label", "Label", "The name of a label of the repository."),)
    data = (LabelsData(),)

    @classmethod
    def assess(cls, issue, values: dict) -> bool:
        """Whether the pull request has the label.

        Args:
            issue: The pull request.
            values: ``label``.

        Returns:
            True if it has the label.
        """
        return issue.labels.filter(name__iexact=values["label"]).exists()
