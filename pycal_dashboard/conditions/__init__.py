"""The conditions and states of pull requests, with their inputs and the data they need.

A state (:class:`~.state.base.State`) has an id, the inputs that configure it
(:class:`~.input.base.InputSpec`), the data that the background reads for it
(:class:`~.spec.base.DataSpec`), and its page in the documentation. A condition
(:class:`~.condition.base.Condition`, ``docs/reference/conditions/<id>.rst``) is a state of a
pull request that is true or false; a state of a person (:class:`~.state.person.PersonState`,
``docs/reference/states/<id>.rst``) is a number counted in the repositories of a project
(:class:`~.state.scope.Scope`), such as the reviews the author gave.

``CONDITIONS`` and ``STATES`` have them by id; :func:`~pycal_dashboard.conditions.find` finds a
condition, and ``DATA_SPECS`` are the data that the update of a repository reads. The modules
are grouped: ``condition/`` the conditions, ``state/`` the states, ``input/`` the kinds of
inputs and ``spec/`` the data, each on its ``base.py``.
"""

from pycal_dashboard.conditions.condition.auto_merge_enabled import AutoMergeEnabled
from pycal_dashboard.conditions.condition.base import Condition
from pycal_dashboard.conditions.condition.branch_outdated import BranchOutdated
from pycal_dashboard.conditions.condition.branch_up_to_date import BranchUpToDate
from pycal_dashboard.conditions.condition.ci_fails import CiFails
from pycal_dashboard.conditions.condition.ci_passes import CiPasses
from pycal_dashboard.conditions.condition.ci_unknown import CiUnknown
from pycal_dashboard.conditions.condition.closed import Closed
from pycal_dashboard.conditions.condition.label_absent import LabelAbsent
from pycal_dashboard.conditions.condition.label_exists import LabelExists
from pycal_dashboard.conditions.condition.merge_conflict import MergeConflict
from pycal_dashboard.conditions.condition.merged import Merged
from pycal_dashboard.conditions.condition.open import Open
from pycal_dashboard.conditions.condition.review_ratio_above import ReviewRatioAbove
from pycal_dashboard.conditions.condition.reviews_at_least import ReviewsAtLeast
from pycal_dashboard.conditions.spec.checks import ChecksData
from pycal_dashboard.conditions.spec.issue import IssueData
from pycal_dashboard.conditions.spec.labels import LabelsData
from pycal_dashboard.conditions.spec.pull_request import PullRequestData
from pycal_dashboard.conditions.spec.reviews import ReviewsData
from pycal_dashboard.conditions.state.own_pull_requests_closed import OwnPullRequestsClosed
from pycal_dashboard.conditions.state.person import PersonState
from pycal_dashboard.conditions.state.pull_requests_opened import PullRequestsOpened
from pycal_dashboard.conditions.state.review_ratio import ReviewRatio
from pycal_dashboard.conditions.state.reviews_given import ReviewsGiven
from pycal_dashboard.errors import UnknownCondition

CONDITIONS: dict[str, type[Condition]] = {
    condition.id: condition
    for condition in (
        LabelExists,
        LabelAbsent,
        CiPasses,
        CiFails,
        CiUnknown,
        MergeConflict,
        BranchOutdated,
        BranchUpToDate,
        AutoMergeEnabled,
        Open,
        Merged,
        Closed,
        ReviewsAtLeast,
        ReviewRatioAbove,
    )
}
# the states of people, numbers counted in the repositories of a project
STATES: dict[str, type[PersonState]] = {
    state.id: state
    for state in (PullRequestsOpened, OwnPullRequestsClosed, ReviewsGiven, ReviewRatio)
}
# in the order the background reads them: the checks need the state of the pull request
DATA_SPECS = (IssueData(), LabelsData(), PullRequestData(), ChecksData(), ReviewsData())


def find(id: str) -> type[Condition]:
    """The condition with an id.

    Parameters:
        id: Such as ``label_exists``.

    Returns:
        The condition.

    Raises:
        UnknownCondition: There is no condition with this id.
    """
    try:
        return CONDITIONS[id]
    except KeyError:
        raise UnknownCondition(id) from None
