"""The state of an open pull request: whether it can be merged, its branches, auto-merge."""

from django.utils import timezone

from pycal_dashboard.conditions.spec.base import DataSpec
from pycal_dashboard.models import Issue, PullRequestState


class PullRequestData(DataSpec):
    """Whether an open pull request has a conflict, is behind its base, and merges itself.

    GitHub tells it only for one pull request at a time, so :meth:`fetch` reads every open pull
    request of a repository with the GitHub App installed on it, at every update: a change of
    the base branch changes it without an event of the pull request.
    """

    id = "pull_request"
    title = "Whether the pull request can be merged, is behind its base, and merges itself"
    permissions = {"pull_requests": "read", "contents": "read"}
    events = ("pull_request", "push")

    def fetch(self, client, repository) -> int:
        """Read the state of every open pull request.

        Args:
            client: The client.
            repository: The repository; without the GitHub App, nothing is read, so that the
                site does not spend the few requests GitHub allows without a token.

        Returns:
            How many pull requests were read.
        """
        if not repository.app_installed:
            return 0
        pulls = Issue.objects.filter(repository=repository, pull_request=True, state=Issue.OPEN)
        for issue in pulls:
            data = client.request(
                "GET", f"/repos/{repository.full_name}/pulls/{issue.number}"
            ).json()
            self.keep(issue, data)
        return len(pulls)

    @staticmethod
    def keep(issue, data: dict) -> PullRequestState:
        """Keep the state of a pull request as GitHub describes it.

        Args:
            issue: The pull request.
            data: The pull request from GitHub.

        Returns:
            The state.
        """
        state, _created = PullRequestState.objects.update_or_create(
            issue=issue,
            defaults={
                "head_sha": str((data.get("head") or {}).get("sha") or ""),
                "head_ref": str((data.get("head") or {}).get("ref") or "")[:255],
                "base_ref": str((data.get("base") or {}).get("ref") or "")[:255],
                "mergeable": data.get("mergeable"),
                "mergeable_state": str(data.get("mergeable_state") or "")[:20],
                "auto_merge": bool(data.get("auto_merge")),
                "updated": timezone.now(),
            },
        )
        return state

    def complete(self, issue) -> bool:
        """Read since the last change of the pull request, and GitHub knows if it merges.

        Args:
            issue: The pull request.

        Returns:
            True if the state is current and ``mergeable`` is known.
        """
        state = getattr(issue, "pull_state", None)
        if state is None or state.updated is None or state.mergeable is None:
            return False
        return issue.changed is None or state.updated >= issue.changed
