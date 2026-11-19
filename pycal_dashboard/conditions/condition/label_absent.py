"""The condition ``label_absent``: a pull request does not have a label."""

from pycal_dashboard.conditions.condition.label_exists import LabelExists


class LabelAbsent(LabelExists):
    """A label is absent from a pull request.

    Holds when the pull request does not have the label of the input ``label``: the opposite of
    ``label_exists``.
    """

    id = "label_absent"
    title = "A label is absent"
    description = "A label is absent from a pull request."

    @classmethod
    def assess(cls, issue, values: dict) -> bool:
        """Whether the pull request does not have the label.

        Args:
            issue: The pull request.
            values: ``label``.

        Returns:
            True if it does not have the label.
        """
        return not super().assess(issue, values)
