"""The condition ``review_ratio``: the review to pull request ratio of the author, compared."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pycal_dashboard.conditions.condition.base import Condition
from pycal_dashboard.conditions.input.comparison import ComparisonInput
from pycal_dashboard.conditions.input.number import NumberInput
from pycal_dashboard.conditions.state.review_ratio import ReviewRatio

if TYPE_CHECKING:
    from pycal_dashboard.conditions.state.scope import Scope
    from pycal_dashboard.models import Issue


class ReviewRatioCompared(Condition):
    """The review to pull request ratio of the author of a pull request, compared with a number.

    Holds when the state ``review_ratio`` of the author, counted in all repositories of the
    project, compares with the input ``ratio`` as the input ``comparison`` says, such as below
    1: the author gave fewer reviews than they opened pull requests that others had to look
    at. 1 is as many reviews as pull requests, 0.5 half as many, 2 twice as many.
    """

    id = "review_ratio"
    title = "Review to pull request ratio"
    description = "The review to pull request ratio of the author compared with a number."
    inputs = (
        ComparisonInput(
            "comparison",
            "Comparison",
            "above, below, at_most, at_least or exactly; at most and at least include the number.",
            required=False,
            default="above",
        ),
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
        """Whether the ratio of the author compares with the input.

        Parameters:
            issue: The pull request.
            values: ``comparison`` and ``ratio``.
            scope: The repositories of the project.

        Returns:
            True if it holds; False for a pull request without an author.
        """
        comparison = values.get("comparison", "above")
        return bool(ReviewRatio.compare(issue, comparison, values["ratio"], scope))
