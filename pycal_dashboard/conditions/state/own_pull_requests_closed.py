"""The state ``own_pull_requests_closed``: the pull requests a person opened and closed."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils.translation import gettext_noop

from pycal_dashboard.conditions.spec.issue import IssueData
from pycal_dashboard.conditions.spec.reviews import ReviewsData
from pycal_dashboard.conditions.state.person import PersonState

if TYPE_CHECKING:
    from pycal_dashboard.conditions.state.scope import Scope
    from pycal_dashboard.models import GitHubUser


class OwnPullRequestsClosed(PersonState):
    """How many pull requests a person opened and closed themselves without merging them.

    Such as a pull request withdrawn, or opened by mistake. Who closed a pull request is read
    with the reviews (``reviews``): those closed by others, or merged, do not count.
    """

    id = "own_pull_requests_closed"
    title = gettext_noop("Own pull requests closed")
    description = gettext_noop(
        "How many pull requests a person opened and closed themselves in the project."
    )
    data = (IssueData(), ReviewsData())

    phrase = gettext_noop("PR author closed %(comparison)s %(number)s of their own pull requests")

    @classmethod
    def measure(cls, person: GitHubUser, scope: Scope, values: dict) -> int:
        """The pull requests the person opened and closed without merging.

        Parameters:
            person: The person.
            scope: The repositories of the project.
            values: Not used.

        Returns:
            How many.
        """
        return scope.count("closed_own", person)
