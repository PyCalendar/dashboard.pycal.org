"""The group of the branch: up to date, outdated or in conflict."""

from django.utils.translation import gettext, gettext_noop

from pycal_dashboard.conditions.condition.branch_outdated import BranchOutdated
from pycal_dashboard.conditions.condition.branch_up_to_date import BranchUpToDate
from pycal_dashboard.conditions.condition.merge_conflict import MergeConflict
from pycal_dashboard.conditions.group.switches import SwitchesGroup
from pycal_dashboard.models import Issue


class BranchGroup(SwitchesGroup):
    """The branch of a pull request: up to date, outdated or in conflict.

    The conditions ``branch_up_to_date``, ``branch_outdated`` and ``merge_conflict``. A merged
    pull request is up to date. Its cell shows what applies, such as ``outdated, conflict``.
    """

    id = "branch"
    title = gettext_noop("Branch")
    switches = (
        ("up_to_date", BranchUpToDate, gettext_noop("up to date")),
        ("outdated", BranchOutdated, gettext_noop("outdated")),
        ("conflict", MergeConflict, gettext_noop("conflict")),
    )
    exclusive = ("up_to_date", "outdated", "conflict")
    phrase = (
        gettext_noop("PR branch is %(states)s"),
        gettext_noop("PR branch is not %(states)s"),
    )
    words = {"conflict": gettext_noop("in conflict")}

    @classmethod
    def unknown(cls, issue: Issue, choices: tuple[str, ...]) -> str:
        """Why the state of the branch is not known.

        Parameters:
            issue: The pull request.
            choices: The switches that are on.

        Returns:
            The reason, translated.
        """
        if issue.state != Issue.OPEN:
            return gettext("not known: GitHub tells the branch of open pull requests only")
        return gettext("not known yet: GitHub computes whether it can be merged")
