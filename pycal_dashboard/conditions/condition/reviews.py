"""The condition ``reviews``: how many reviews a pull request has, compared with a number."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils.translation import gettext

from pycal_dashboard.conditions.condition.base import Condition
from pycal_dashboard.conditions.evidence import Evidence
from pycal_dashboard.conditions.input.comparison import ComparisonInput, compare
from pycal_dashboard.conditions.input.integer import IntegerInput
from pycal_dashboard.conditions.input.review_kinds import ReviewKindsInput
from pycal_dashboard.conditions.spec.reviews import ReviewsData

if TYPE_CHECKING:
    from pycal_dashboard.conditions.state.scope import Scope
    from pycal_dashboard.models import Issue, Project


class Reviews(Condition):
    """A pull request has a number of reviews: at least, at most, more, fewer, or exactly.

    Holds when the number of reviews of the pull request compares with the input ``reviews``
    as the input ``comparison`` says, such as at least 2; at least and at most include the
    number. The input ``kinds`` says which reviews count: approved, changes requested,
    commented and dismissed (an approval or a request for changes dismissed later); all of them
    by default, but not those of the author of the pull request, unless ``own`` is chosen.
    """

    id = "reviews"
    title = "Reviews"
    description = (
        "A pull request has a number of reviews, of the kinds that count: all by default, but not "
        "those of its author."
    )
    inputs = (
        ComparisonInput(
            "comparison",
            "Comparison",
            "above, below, at_most, at_least or exactly; at most and at least include the number.",
            required=False,
            default="at_least",
        ),
        IntegerInput("reviews", "Reviews", "The number of reviews to compare with.", minimum=0),
        ReviewKindsInput(),
    )
    data = (ReviewsData(),)

    def assess(self, issue: Issue) -> bool:
        """Whether the number of reviews compares with the input.

        Parameters:
            issue: The pull request.

        Returns:
            True if it holds.
        """
        # the reviews prefetched with the pull request, if so
        values = self.values
        counted = len(ReviewsData.counted(issue, values.get("kinds")))
        return compare(counted, values.get("comparison", "at_least"), values["reviews"])

    @staticmethod
    def deciding(count: int, comparison: str, number: int) -> int:
        """How many reviews decide the condition: the least that show it holds, or not.

        Parameters:
            count: The reviews of the pull request that count.
            comparison: Such as ``at_least``.
            number: The number to compare with.

        Returns:
            How many to show, at most ``count``.

        Examples:
            >>> Reviews.deciding(3, "at_least", 4), Reviews.deciding(5, "at_least", 2)
            (3, 2)
            >>> Reviews.deciding(5, "at_most", 2), Reviews.deciding(1, "at_most", 2)
            (3, 1)
            >>> Reviews.deciding(4, "above", 1), Reviews.deciding(4, "below", 2)
            (2, 2)
            >>> Reviews.deciding(4, "exactly", 2), Reviews.deciding(1, "exactly", 2)
            (3, 1)
        """
        holds = compare(count, comparison, number)
        enough = {  # the reviews that decide it, if not all of them
            "at_least": number if holds else count,
            "above": number + 1 if holds else count,
            "at_most": count if holds else number + 1,
            "below": count if holds else number,
            "exactly": count if holds or count < number else number + 1,
        }
        return min(count, enough.get(comparison, count))

    def evidence(
        self, issue: Issue, scope: Scope | None = None, project: Project | None = None
    ) -> list[Evidence]:
        """As many reviews as decide the condition, the oldest first.

        Such as 3 of at least 4 when there are 3, and 3 of at most 2 when there are more.

        Parameters:
            issue: The pull request.
            scope: Not used.
            project: Not used.

        Returns:
            A link to each review; to the pull request without one to show.
        """
        values = self.values
        found = ReviewsData().evidence(issue, values.get("kinds"))
        shown = self.deciding(len(found), values.get("comparison", "at_least"), values["reviews"])
        if not shown:
            return [Evidence(gettext("Its reviews on GitHub"), issue.url)]
        return found[:shown]
