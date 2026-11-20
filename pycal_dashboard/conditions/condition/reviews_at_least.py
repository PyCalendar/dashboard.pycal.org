"""The condition ``reviews_at_least``: a pull request has a number of reviews."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pycal_dashboard.conditions.condition.base import Condition
from pycal_dashboard.conditions.input.positive_integer import PositiveIntegerInput
from pycal_dashboard.conditions.spec.reviews import COUNTED, ReviewsData

if TYPE_CHECKING:
    from pycal_dashboard.models import Issue


class ReviewsAtLeast(Condition):
    """A pull request has at least a number of reviews.

    Holds when the pull request has at least as many reviews as the input ``reviews``. A review
    counts when it approved, requested changes, or was dismissed later; a review with comments
    only does not count.
    """

    id = "reviews_at_least"
    title = "At least a number of reviews"
    description = "A pull request has at least a number of reviews, without those of comments."
    inputs = (PositiveIntegerInput("reviews", "Reviews", "The fewest reviews it has."),)
    data = (ReviewsData(),)

    @classmethod
    def assess(cls, issue: Issue, values: dict) -> bool:
        """Whether the pull request has enough reviews.

        Parameters:
            issue: The pull request.
            values: ``reviews``.

        Returns:
            True if it has at least that many.
        """
        # the reviews prefetched with the pull request, if so
        counted = sum(review.state in COUNTED for review in issue.reviews.all())
        return counted >= values["reviews"]
