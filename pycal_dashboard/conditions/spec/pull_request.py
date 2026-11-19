"""The state of an open pull request: whether it can be merged, its branches, auto-merge."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils import timezone

from pycal_dashboard.conditions.spec.base import DataSpec
from pycal_dashboard.models import PullRequestState

if TYPE_CHECKING:
    from pycal_dashboard.models import Issue

# mergeable of GraphQL as the site keeps it: None while GitHub computes it
MERGEABLE = {"MERGEABLE": True, "CONFLICTING": False, "UNKNOWN": None}


class PullRequestData(DataSpec):
    """Whether an open pull request has a conflict, is behind its base, and merges itself.

    Read for every open pull request at every update, with one query of GraphQL for the
    repository: a change of the base branch changes it without an event of the pull request.
    GraphQL needs a token, so only repositories with the GitHub App are read.
    """

    id = "pull_request"
    title = "Whether the pull request can be merged, is behind its base, and merges itself"
    permissions = {"pull_requests": "read", "contents": "read"}
    events = ("pull_request", "push")
    graphql = (
        "headRefName headRefOid baseRefName mergeable mergeStateStatus "
        "autoMergeRequest { enabledAt }"
    )

    def keep_pull_request(self, issue: Issue, node: dict) -> None:
        """Keep the state of a pull request as GraphQL describes it.

        Parameters:
            issue: The pull request.
            node: The pull request of GraphQL.
        """
        PullRequestState.objects.update_or_create(
            issue=issue,
            defaults={
                "head_sha": str(node.get("headRefOid") or ""),
                "head_ref": str(node.get("headRefName") or "")[:255],
                "base_ref": str(node.get("baseRefName") or "")[:255],
                "mergeable": MERGEABLE.get(str(node.get("mergeable"))),
                "mergeable_state": str(node.get("mergeStateStatus") or "").lower()[:20],
                "auto_merge": bool(node.get("autoMergeRequest")),
                "updated": timezone.now(),
            },
        )

    def complete(self, issue: Issue) -> bool:
        """Read since the last change of the pull request, and GitHub knows if it merges.

        Parameters:
            issue: The pull request.

        Returns:
            True if the state is current and ``mergeable`` is known.
        """
        state = getattr(issue, "pull_state", None)
        if state is None or state.updated is None or state.mergeable is None:
            return False
        return issue.changed is None or state.updated >= issue.changed
