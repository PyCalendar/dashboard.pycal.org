"""The condition ``review_ratio_above``: the author of a pull request reviews enough."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pycal_dashboard.conditions.condition.base import Condition
from pycal_dashboard.conditions.input.number import NumberInput
from pycal_dashboard.conditions.state.review_ratio import ReviewRatio

if TYPE_CHECKING:
    from pycal_dashboard.conditions.state.scope import Scope
    from pycal_dashboard.models import Issue


class ReviewRatioAbove(Condition):
    """The review to pull request ratio of the author of a pull request is above a number.

    Holds when the state ``review_ratio`` of the author, counted in all repositories of the
    project, is above the input ``ratio``, such as ``1.5``: the author gave more than one and a
    half reviews for each pull request of theirs.
    """

    id = "review_ratio_above"
    title = "Review to pull request ratio above"
    description = "The review to pull request ratio of the author is above a number."
    inputs = (
        NumberInput(
            "ratio",
            "Ratio",
            "The reviews given for each pull request opened and not closed by the author.",
            minimum=0,
        ),
    )
    data = ReviewRatio.data
    scoped = True

    @classmethod
    def assess(cls, issue: Issue, values: dict, scope: Scope | None = None) -> bool:
        """Whether the ratio of the author is above the input.

        Parameters:
            issue: The pull request.
            values: ``ratio``.
            scope: The repositories of the project.

        Returns:
            True if it is above; False for a pull request without an author.
        """
        return bool(ReviewRatio.above(issue, values["ratio"], scope))
