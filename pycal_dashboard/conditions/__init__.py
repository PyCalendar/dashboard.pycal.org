"""The conditions that are checked on pull requests, with their inputs and the data they need.

Each condition (:class:`~.condition.base.Condition`) has an id, the inputs that configure it
(:class:`~.input.base.InputSpec`), the data that the background reads for it
(:class:`~.spec.base.DataSpec`), and its page in the documentation,
``docs/reference/conditions/<id>.rst``. They are not shown on the pages yet.

``CONDITIONS`` has them by id; :func:`~pycal_dashboard.conditions.find` finds one, and
``DATA_SPECS`` are the data that the update of a repository reads. The modules are grouped:
``condition/`` the conditions, ``input/`` the kinds of inputs and ``spec/`` the data, each on
its ``base.py``.
"""

from pycal_dashboard.conditions.condition.auto_merge_enabled import AutoMergeEnabled
from pycal_dashboard.conditions.condition.base import Condition
from pycal_dashboard.conditions.condition.branch_outdated import BranchOutdated
from pycal_dashboard.conditions.condition.ci_fails import CiFails
from pycal_dashboard.conditions.condition.ci_passes import CiPasses
from pycal_dashboard.conditions.condition.closed import Closed
from pycal_dashboard.conditions.condition.label_absent import LabelAbsent
from pycal_dashboard.conditions.condition.label_exists import LabelExists
from pycal_dashboard.conditions.condition.merge_conflict import MergeConflict
from pycal_dashboard.conditions.condition.merged import Merged
from pycal_dashboard.conditions.condition.open import Open
from pycal_dashboard.conditions.spec.checks import ChecksData
from pycal_dashboard.conditions.spec.issue import IssueData
from pycal_dashboard.conditions.spec.labels import LabelsData
from pycal_dashboard.conditions.spec.pull_request import PullRequestData
from pycal_dashboard.errors import UnknownCondition

CONDITIONS: dict[str, type[Condition]] = {
    condition.id: condition
    for condition in (
        LabelExists,
        LabelAbsent,
        CiPasses,
        CiFails,
        MergeConflict,
        BranchOutdated,
        AutoMergeEnabled,
        Open,
        Merged,
        Closed,
    )
}
# in the order the background reads them: the checks need the state of the pull request
DATA_SPECS = (IssueData(), LabelsData(), PullRequestData(), ChecksData())


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
