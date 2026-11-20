"""The condition ``reviews``: how many reviews a pull request has, compared with a number."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pycal_dashboard.conditions.condition.base import Condition
from pycal_dashboard.conditions.input.comparison import ComparisonInput, compare
from pycal_dashboard.conditions.input.integer import IntegerInput
from pycal_dashboard.conditions.spec.reviews import COUNTED, ReviewsData

if TYPE_CHECKING:
    from pycal_dashboard.models import Issue


class Reviews(Condition):
    """A pull request has a number of reviews: at least, at most, more, fewer, or exactly.

    Holds when the number of reviews of the pull request compares with the input ``reviews``
    as the input ``comparison`` says, such as at least 2; at least and at most include the
    number. A review counts when it approved, requested changes, or was dismissed later; a
    review with comments only does not count.
    """

    id = "reviews"
    title = "Reviews"
    description = "A pull request has a number of reviews, without those of comments only."
    inputs = (
        ComparisonInput(
            "comparison",
            "Comparison",
            "above, below, at_most, at_least or exactly; at most and at least include the number.",
            required=False,
            default="at_least",
        ),
        IntegerInput("reviews", "Reviews", "The number of reviews to compare with.", minimum=0),
    )
    data = (ReviewsData(),)

    @classmethod
    def assess(cls, issue: Issue, values: dict) -> bool:
        """Whether the number of reviews compares with the input.

        Parameters:
            issue: The pull request.
            values: ``comparison`` and ``reviews``.

        Returns:
            True if it holds.
        """
        # the reviews prefetched with the pull request, if so
        counted = sum(review.state in COUNTED for review in issue.reviews.all())
        return compare(counted, values.get("comparison", "at_least"), values["reviews"])
