"""The checks of the last commit of a pull request: its continuous integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils import timezone
from django.utils.translation import gettext

from pycal_dashboard.conditions.evidence import Evidence
from pycal_dashboard.conditions.spec.base import DataSpec
from pycal_dashboard.models import PullRequestState

if TYPE_CHECKING:
    from pycal_dashboard.models import Issue

# the state of the rollup of GraphQL as the site keeps it
ROLLUP = {
    "SUCCESS": PullRequestState.SUCCESS,
    "FAILURE": PullRequestState.FAILURE,
    "ERROR": PullRequestState.FAILURE,
    "PENDING": PullRequestState.PENDING,
    "EXPECTED": PullRequestState.PENDING,
}


class ChecksData(DataSpec):
    """The check runs and commit statuses of the last commit of an open pull request.

    GitHub sums them up in the rollup of the last commit: ``success``, ``failure`` or
    ``pending`` (``PullRequestState.checks``). A commit without checks is ``success``.
    """

    id = "checks"
    title = "The checks and statuses of the last commit of the pull request"
    permissions = {"checks": "read", "statuses": "read"}
    events = ("check_run", "check_suite", "status")
    graphql = "commits(last: 1) { nodes { commit { statusCheckRollup { state } } } }"

    @staticmethod
    def summary(node: dict) -> str:
        """The state of the checks of the last commit of a pull request of GraphQL.

        Parameters:
            node: The pull request, with ``commits``.

        Returns:
            ``success``, ``failure`` or ``pending``; ``success`` without checks.

        Examples:
            >>> rollup = {"statusCheckRollup": {"state": "ERROR"}}
            >>> ChecksData.summary({"commits": {"nodes": [{"commit": rollup}]}})
            'failure'
            >>> ChecksData.summary({"commits": {"nodes": [{"commit": {}}]}})
            'success'
        """
        commits = (node.get("commits") or {}).get("nodes") or [{}]
        rollup = (commits[-1].get("commit") or {}).get("statusCheckRollup") or {}
        return ROLLUP.get(str(rollup.get("state")), PullRequestState.SUCCESS)

    def keep_pull_request(self, issue: Issue, node: dict) -> None:
        """Keep the state of the checks of a pull request.

        Parameters:
            issue: The pull request.
            node: The pull request of GraphQL.
        """
        summary = self.summary(node)
        defaults = {"checks": summary, "checks_updated": timezone.now()}
        if summary != PullRequestState.PENDING:  # complete: the result while new checks run
            defaults["checks_complete"] = summary
        PullRequestState.objects.update_or_create(issue=issue, defaults=defaults)

    def evidence(self, issue: Issue) -> list[Evidence]:
        """The checks of the pull request on GitHub.

        Parameters:
            issue: The pull request.

        Returns:
            The link to them.
        """
        return [Evidence(gettext("PR checks on GitHub"), issue.url + "/checks")]

    def complete(self, issue: Issue) -> bool:
        """Read after the last reading of the pull request, for its last commit.

        Parameters:
            issue: The pull request.

        Returns:
            True if the checks are known and current, and one result was complete.
        """
        state = getattr(issue, "pull_state", None)
        if state is None or not state.checks_complete or state.checks_updated is None:
            return False
        return state.updated is None or state.checks_updated >= state.updated
