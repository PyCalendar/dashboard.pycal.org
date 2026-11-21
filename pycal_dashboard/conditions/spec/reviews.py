"""The reviews of the pull requests of a repository, and who closed each of them."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.translation import gettext, gettext_noop

from pycal_dashboard.conditions.evidence import Evidence
from pycal_dashboard.conditions.review_kinds import states as review_states
from pycal_dashboard.conditions.spec.base import DataSpec
from pycal_dashboard.github.data_version import DATA_VERSION
from pycal_dashboard.github.queries import REVIEWS
from pycal_dashboard.models import GitHubUser, Issue, Review

if TYPE_CHECKING:
    from pycal_dashboard.github.client import GitHubClient
    from pycal_dashboard.models import Repository

# a page of pull requests with their reviews; down to the least when GitHub gives up
PER_PAGE = 20
LEAST_PER_PAGE = 5
# the reviews that count: not those with only comments
COUNTED = ("APPROVED", "CHANGES_REQUESTED", "DISMISSED")
# a review of comments only, which counts where a condition says so
COMMENTED = "COMMENTED"
# the states of reviews that count, for people
STATES = {
    "APPROVED": gettext_noop("approved"),
    "CHANGES_REQUESTED": gettext_noop("changes requested"),
    "DISMISSED": gettext_noop("dismissed"),
    "COMMENTED": gettext_noop("commented"),
}


class ReviewsData(DataSpec):
    """The reviews of all pull requests of a repository, open and closed, and who closed them.

    :meth:`fetch` reads the pull requests that GitHub changed last first, with one query of
    GraphQL for a page, and stops at those it read before: a new review or closing changes a
    pull request. The first 100 reviews of a pull request are read. Reading needs the GitHub
    App, as all of GraphQL; the states of people need it in every repository of the project.
    Reviews that are only comments are kept, but not counted (``COUNTED``).
    """

    id = "reviews"
    title = "The reviews of the pull requests and who closed them"
    permissions = {"pull_requests": "read"}
    events = ("pull_request_review", "pull_request")

    def fetch(self, client: GitHubClient, repository: Repository) -> int:
        """Read the pull requests changed since the last time with their reviews and closers.

        Parameters:
            client: The client of the installation.
            repository: The repository, after its issues and pull requests were read.

        Returns:
            How many pull requests were read.
        """
        if not repository.app_installed:
            return 0
        since = None if repository.data_version < DATA_VERSION else repository.reviews_changed
        issues = {
            issue.number: issue
            for issue in Issue.objects.filter(repository=repository, pull_request=True)
        }
        owner, name = repository.full_name.split("/", 1)
        people: dict[int, GitHubUser | None] = {}
        read, newest = 0, since
        for nodes in client.graphql_pages(
            REVIEWS,
            ("repository", "pullRequests"),
            PER_PAGE,
            LEAST_PER_PAGE,
            owner=owner,
            name=name,
        ):
            done = False
            for node in nodes:
                changed = parse_datetime(node["updatedAt"])
                if since and changed and changed <= since:  # read before, and all after it
                    done = True
                    break
                if changed and (newest is None or changed > newest):
                    newest = changed
                issue = issues.get(node["number"])
                if issue is not None:  # else opened after the issues were read: the next update
                    self.keep(issue, node, people)
                    read += 1
            if done:
                break
        repository.reviews_changed = newest or timezone.now()
        repository.save(update_fields=["reviews_changed"])
        return read

    @staticmethod
    def person(data: dict | None, people: dict[int, GitHubUser | None]) -> GitHubUser | None:
        """A person of GraphQL as the site keeps them, recorded once in a reading.

        Parameters:
            data: The actor of GraphQL: ``__typename``, ``login``, ``avatarUrl`` and
                ``databaseId``; None for a deleted account.
            people: The people recorded in this reading, by their id.

        Returns:
            The GitHub user; None without an id, such as for a deleted account.
        """
        github_id = (data or {}).get("databaseId")
        if not github_id:
            return None
        if github_id not in people:
            people[github_id] = GitHubUser.record(
                {
                    "id": github_id,
                    "login": data.get("login"),
                    "avatar_url": data.get("avatarUrl"),
                    "type": data.get("__typename"),
                }
            )
        return people[github_id]

    def keep(self, issue: Issue, node: dict, people: dict[int, GitHubUser | None]) -> None:
        """Keep the reviews of a pull request and who closed it.

        Parameters:
            issue: The pull request.
            node: The pull request of GraphQL with ``reviews`` and ``timelineItems``.
            people: The people recorded in this reading, by their id.
        """
        seen = []
        with transaction.atomic():
            for review in node["reviews"]["nodes"]:
                if not review.get("databaseId"):
                    continue
                submitted = review.get("submittedAt")
                Review.objects.update_or_create(
                    github_id=review["databaseId"],
                    defaults={
                        "issue": issue,
                        "author": self.person(review.get("author"), people),
                        "state": str(review.get("state") or "")[:20],
                        "submitted": parse_datetime(submitted) if submitted else None,
                    },
                )
                seen.append(review["databaseId"])
            if len(seen) < 100:  # all of them: those GitHub no longer has are deleted
                issue.reviews.exclude(github_id__in=seen).delete()
            closings = node["timelineItems"]["nodes"]
            closer = closings[-1].get("actor") if closings and issue.state == Issue.CLOSED else None
            issue.closed_by = self.person(closer, people)
            issue.save(update_fields=["closed_by"])

    def evidence(self, issue: Issue, kinds: tuple[str, ...] | None = None) -> list[Evidence]:
        """The reviews of the pull request that count, each on GitHub, the oldest first.

        Parameters:
            issue: The pull request.
            kinds: The kinds of reviews that count, see
                :mod:`~pycal_dashboard.conditions.review_kinds`; all for None.

        Returns:
            A link to each review.
        """
        return [self.review_evidence(issue, review) for review in self.counted(issue, kinds)]

    @staticmethod
    def counted(issue: Issue, kinds: tuple[str, ...] | None = None) -> list[Review]:
        """The reviews of a pull request of kinds, the oldest first.

        Parameters:
            issue: The pull request.
            kinds: The kinds of reviews that count; all of them for None.

        Returns:
            The reviews of these kinds.
        """
        states = review_states(kinds)
        found = [review for review in issue.reviews.all() if review.state in states]
        return sorted(found, key=lambda review: (review.submitted is None, review.submitted))

    @staticmethod
    def review_evidence(issue: Issue, review: Review) -> Evidence:
        """A review on GitHub, by its author.

        Parameters:
            issue: The pull request.
            review: One of its reviews.

        Returns:
            The link to it, such as ``Review by stevepiercy: approved``.
        """
        state = STATES.get(review.state, review.state.lower())
        text = gettext("Review by %(handle)s: %(state)s") % {
            "handle": review.author.login if review.author else gettext("a deleted account"),
            "state": gettext(state),
        }
        return Evidence(text, f"{issue.url}#pullrequestreview-{review.github_id}")

    def complete(self, issue: Issue) -> bool:
        """The reviews of the repository of the pull request were read.

        Parameters:
            issue: The pull request.

        Returns:
            True if its repository was read with its reviews.
        """
        return issue.repository.reviews_changed is not None

    def complete_in(self, repositories: list[Repository]) -> bool:
        """The reviews of every repository were read.

        Parameters:
            repositories: The repositories.

        Returns:
            True if each was read with its reviews.
        """
        return all(repository.reviews_changed is not None for repository in repositories)
