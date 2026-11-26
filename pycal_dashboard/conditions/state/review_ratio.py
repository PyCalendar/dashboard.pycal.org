"""The state ``review_ratio``: the reviews a person gave for each of their pull requests."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from django.utils.translation import gettext_noop

from pycal_dashboard.conditions.spec.issue import IssueData
from pycal_dashboard.conditions.spec.reviews import ReviewsData
from pycal_dashboard.conditions.state.own_pull_requests_closed import OwnPullRequestsClosed
from pycal_dashboard.conditions.state.person import PersonState
from pycal_dashboard.conditions.state.pull_requests_opened import PullRequestsOpened
from pycal_dashboard.conditions.state.reviews_given import ReviewsGiven

if TYPE_CHECKING:
    from pycal_dashboard.conditions.state.scope import Scope
    from pycal_dashboard.models import GitHubUser


class ReviewRatio(PersonState):
    """The reviews a person gave for each pull request of theirs that others had to look at.

    It is ``reviews_given / (pull_requests_opened - own_pull_requests_closed)``, made of those
    states (``parts``), whose inputs it has: ``kinds``, the kinds of reviews that count. Without
    such pull requests, it is infinite with reviews, and 0 without.
    """

    id = "review_ratio"
    title = gettext_noop("Review to pull request ratio")
    description = gettext_noop(
        "The reviews a person gave in the project for each pull request they opened and did not "
        "close themselves."
    )
    data = (IssueData(), ReviewsData())
    parts = (ReviewsGiven, PullRequestsOpened, OwnPullRequestsClosed)
    inputs = PersonState.inputs_of(*parts)  # its parts choose, too, such as the kinds of reviews

    phrase = gettext_noop("PR author has a review to pull request ratio %(comparison)s %(number)s")
    counted = False

    @classmethod
    def measure(cls, person: GitHubUser, scope: Scope, values: dict) -> float:
        """Reviews given / (pull requests opened - own pull requests closed).

        Parameters:
            person: The person.
            scope: The repositories of the project.
            values: The inputs of its parts, such as ``kinds``.

        Returns:
            The ratio; ``inf`` with reviews but no such pull requests.
        """
        reviews = ReviewsGiven.measure(person, scope, values)
        pulls = PullRequestsOpened.measure(person, scope, values) - OwnPullRequestsClosed.measure(
            person, scope, values
        )
        if pulls <= 0:
            return math.inf if reviews else 0.0
        return reviews / pulls
