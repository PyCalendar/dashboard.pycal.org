"""The state ``reviews_given``: how many reviews a person gave in a project."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils.translation import gettext_noop

from pycal_dashboard.conditions.spec.reviews import ReviewsData
from pycal_dashboard.conditions.state.person import PersonState

if TYPE_CHECKING:
    from pycal_dashboard.conditions.state.scope import Scope
    from pycal_dashboard.models import GitHubUser


class ReviewsGiven(PersonState):
    """How many reviews a person gave on the pull requests of all repositories of a project.

    A review counts when it approved, requested changes, or was dismissed later; a review with
    comments only does not count.
    """

    id = "reviews_given"
    title = gettext_noop("Reviews given")
    description = gettext_noop(
        "How many reviews a person gave in the project, without those of comments only."
    )
    data = (ReviewsData(),)

    phrase = gettext_noop("its author gave %(comparison)s %(number)s reviews")

    @classmethod
    def measure(cls, person: GitHubUser, scope: Scope, values: dict) -> int:
        """The reviews the person gave.

        Parameters:
            person: The person.
            scope: The repositories of the project.
            values: Not used.

        Returns:
            How many.
        """
        return scope.count("reviews", person)
