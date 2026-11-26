"""The condition ``author_state``: a state of the author of a pull request, compared."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pycal_dashboard.conditions.condition.base import Condition
from pycal_dashboard.conditions.input.choice import ChoiceInput
from pycal_dashboard.conditions.input.comparison import ComparisonInput
from pycal_dashboard.conditions.input.number import NumberInput
from pycal_dashboard.conditions.input.review_kinds import ReviewKindsInput
from pycal_dashboard.conditions.spec.issue import IssueData
from pycal_dashboard.conditions.spec.reviews import ReviewsData
from pycal_dashboard.conditions.state.own_pull_requests_closed import OwnPullRequestsClosed
from pycal_dashboard.conditions.state.pull_requests_opened import PullRequestsOpened
from pycal_dashboard.conditions.state.review_ratio import ReviewRatio
from pycal_dashboard.conditions.state.reviews_given import ReviewsGiven

if TYPE_CHECKING:
    from pycal_dashboard.conditions.evidence import Evidence
    from pycal_dashboard.conditions.state.person import PersonState
    from pycal_dashboard.conditions.state.scope import Scope
    from pycal_dashboard.models import Issue, Project

# the states of the author that it compares, in the order of the menu of a column
STATES: dict[str, type[PersonState]] = {
    state.id: state
    for state in (ReviewRatio, ReviewsGiven, PullRequestsOpened, OwnPullRequestsClosed)
}


def has_kinds(state: type[PersonState]) -> bool:
    """Whether a state counts reviews and so has the input of their kinds.

    Parameters:
        state: The state.

    Returns:
        True for such as ``reviews_given`` and ``review_ratio``.
    """
    return any(spec.name == "kinds" for spec in state.inputs)


class AuthorState(Condition):
    """A state of the author of a pull request, compared with a number.

    Holds when the state of the input ``state`` of the author, such as the reviews they gave
    (``reviews_given``), counted in all repositories of the project, compares with the input
    ``number`` as the input ``comparison`` says, such as below 2. The input ``kinds`` says
    which reviews count, for a state that counts reviews. The column *Author* of the table of
    pull requests checks it.
    """

    id = "author_state"
    title = "A state of the author"
    description = "A state of the author of a pull request compared with a number."
    inputs = (
        ChoiceInput(
            "state",
            "State",
            "review_ratio, reviews_given, pull_requests_opened or own_pull_requests_closed.",
            choices={id: state.title for id, state in STATES.items()},
        ),
        ComparisonInput(
            "comparison",
            "Comparison",
            "above, below, at_most, at_least or exactly; at most and at least include the number.",
            required=False,
            default="below",
        ),
        NumberInput("number", "Number", "The number to compare the state with.", minimum=0),
        ReviewKindsInput(),
    )
    data = (IssueData(), ReviewsData())
    scoped = True

    @property
    def state(self) -> type[PersonState]:
        """The state that it compares."""
        return STATES[self.values["state"]]

    @property
    def state_values(self) -> dict:
        """The inputs of the state: ``kinds`` for a state that counts reviews, else nothing."""
        return {"kinds": self.values["kinds"]} if has_kinds(self.state) else {}

    def check(self, issue: Issue, scope: Scope | None = None) -> bool | None:
        """Whether the state of the author compares with the number, if it is known.

        Parameters:
            issue: The pull request.
            scope: The repositories of the project.

        Returns:
            True or False; None for an issue, without an author, or while the data of a
            repository that the state needs is not complete.
        """
        if not issue.pull_request:
            return None
        values = self.values
        return self.state.compare(
            issue, values["comparison"], values["number"], scope, self.state_values
        )

    def assess(self, issue: Issue, scope: Scope | None = None) -> bool:
        """Whether the state of the author compares with the number, see :meth:`check`.

        Parameters:
            issue: The pull request.
            scope: The repositories of the project.

        Returns:
            True if it holds; False while it is not known.
        """
        return bool(self.check(issue, scope))

    def evidence(
        self, issue: Issue, scope: Scope | None = None, project: Project | None = None
    ) -> list[Evidence]:
        """The page of the author in the project, where the states are counted.

        Parameters:
            issue: The pull request.
            scope: Not used.
            project: The project.

        Returns:
            The link; none without an author or a project.
        """
        return self.state.evidence(issue, project)
