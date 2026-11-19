"""The checks of the last commit of a pull request: its continuous integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils import timezone

from pycal_dashboard.conditions.spec.base import DataSpec
from pycal_dashboard.models import Issue, PullRequestState

if TYPE_CHECKING:
    from pycal_dashboard.github.client import GitHubClient
    from pycal_dashboard.models import Issue, Repository


class ChecksData(DataSpec):
    """The check runs and commit statuses of the last commit of an open pull request.

    Together they are ``success``, ``failure`` or ``pending`` (``PullRequestState.checks``).
    """

    id = "checks"
    title = "The checks and statuses of the last commit of the pull request"
    permissions = {"checks": "read", "statuses": "read"}
    events = ("check_run", "check_suite", "status")

    def fetch(self, client: GitHubClient, repository: Repository) -> int:
        """Read the checks of the last commit of every open pull request.

        Parameters:
            client: The client.
            repository: The repository; without the GitHub App, nothing is read.

        Returns:
            How many pull requests were read.
        """
        if not repository.app_installed:
            return 0
        states = PullRequestState.objects.filter(
            issue__repository=repository, issue__state=Issue.OPEN
        ).exclude(head_sha="")
        for state in states:
            base = f"/repos/{repository.full_name}/commits/{state.head_sha}"
            runs = client.request("GET", f"{base}/check-runs", params={"per_page": 100}).json()
            status = client.request("GET", f"{base}/status").json()
            state.checks = self.summary(runs.get("check_runs") or [], status)
            state.checks_updated = timezone.now()
            state.save(update_fields=["checks", "checks_updated"])
        return len(states)

    @staticmethod
    def summary(runs: list[dict], status: dict) -> str:
        """One state of the check runs and the combined status of a commit.

        Parameters:
            runs: The check runs, with ``status`` and ``conclusion``.
            status: The combined status, with ``state`` and ``total_count``.

        Returns:
            ``failure`` if one failed, else ``pending`` if one runs, else ``success``.

        Examples:
            >>> ChecksData.summary([{"status": "completed", "conclusion": "success"}], {})
            'success'
            >>> ChecksData.summary([], {"state": "failure", "total_count": 1})
            'failure'
        """
        failed = {"failure", "timed_out", "cancelled", "action_required", "startup_failure"}
        states = [
            "pending" if run.get("status") != "completed" else run.get("conclusion") or ""
            for run in runs
        ]
        if status.get("total_count"):
            states.append(status.get("state") or "pending")
        if any(state in failed or state == "error" for state in states):
            return PullRequestState.FAILURE
        if any(state == "pending" for state in states):
            return PullRequestState.PENDING
        return PullRequestState.SUCCESS

    def complete(self, issue: Issue) -> bool:
        """Read after the last reading of the pull request, for its last commit.

        Parameters:
            issue: The pull request.

        Returns:
            True if the checks are known and current.
        """
        state = getattr(issue, "pull_state", None)
        if state is None or not state.checks or state.checks_updated is None:
            return False
        return state.updated is None or state.checks_updated >= state.updated
