"""The state ``pull_requests_opened``: how many pull requests a person opened in a project."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils.translation import gettext_noop

from pycal_dashboard.conditions.spec.issue import IssueData
from pycal_dashboard.conditions.state.person import PersonState

if TYPE_CHECKING:
    from pycal_dashboard.conditions.state.scope import Scope
    from pycal_dashboard.models import GitHubUser


class PullRequestsOpened(PersonState):
    """How many pull requests a person opened in the repositories of a project.

    All of them count: open, merged and closed. Observed on a pull request, its author is
    counted, with this pull request.
    """

    id = "pull_requests_opened"
    title = gettext_noop("Pull requests opened")
    description = gettext_noop("How many pull requests a person opened in the project.")
    data = (IssueData(),)

    phrase = gettext_noop("its author opened %(comparison)s %(number)s pull requests")

    @classmethod
    def measure(cls, person: GitHubUser, scope: Scope, values: dict) -> int:
        """The pull requests the person opened.

        Parameters:
            person: The person.
            scope: The repositories of the project.
            values: Not used.

        Returns:
            How many.
        """
        return scope.count("opened", person)
