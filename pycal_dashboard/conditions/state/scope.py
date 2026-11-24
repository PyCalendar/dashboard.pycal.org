"""Where the states of people are counted: the repositories of a project."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Count, F, Q

from pycal_dashboard.conditions.review_kinds import own as own_reviews
from pycal_dashboard.conditions.review_kinds import states as review_states
from pycal_dashboard.models import GitHubUser, Issue, PullRequestComment, Review, StepSkip

if TYPE_CHECKING:
    from pycal_dashboard.models import Project, Repository


class Scope:
    """The repositories in which the states of people are counted, such as those of a project.

    The numbers of all people are counted at once, with one query each, the first time one is
    asked for, so that a table of many pull requests asks the database a few times only.
    """

    def __init__(self, repositories: list[Repository], project: Project | None = None):
        """The repositories counted.

        Parameters:
            repositories: The repositories, such as those of a project that a person sees.
            project: The project, for the conditions on data of the dashboard, such as its PR
                Sync; None when not known.
        """
        self.repositories = list(repositories)
        self.project = project
        self._counts: dict[str, dict[int, int]] = {}
        self._synced: set[int] | None = None
        self._skips: tuple[set[int], set[str]] | None = None

    def synced(self) -> set[int] | None:
        """The pull requests with the PR Sync of the project on, read once.

        Returns:
            Their ids; None without a project.
        """
        if self.project is None:
            return None
        if self._synced is None:
            self._synced = set(
                PullRequestComment.objects.filter(project=self.project).values_list(
                    "issue", flat=True
                )
            )
        return self._synced

    def skips(self) -> tuple[set[int], set[str]] | None:
        """Who skips a step of the project: pull requests by a writer, and authors, read once.

        Returns:
            The ids of the pull requests that a writer skipped a step for, and the GitHub
            handles (lower case) of the authors whose pull requests skip a step; None without a
            project.
        """
        if self.project is None:
            return None
        if self._skips is None:
            issues = set(
                StepSkip.objects.filter(step__project=self.project).values_list("issue", flat=True)
            )
            authors = {
                str(login).lower()
                for logins in self.project.steps.values_list("skip_authors", flat=True)
                for login in logins or []
            }
            self._skips = (issues, authors)
        return self._skips

    @classmethod
    def of(cls, subject: Issue | GitHubUser | Project) -> Scope:
        """The scope of a pull request (its repository) or of a project (its repositories).

        Parameters:
            subject: A pull request, a project, or a person (no repositories).

        Returns:
            The scope.
        """
        if isinstance(subject, Issue):
            return cls([subject.repository])
        if isinstance(subject, GitHubUser):
            return cls([])
        return cls(list(subject.repositories.all()), subject)

    @staticmethod
    def person(subject: Issue | GitHubUser) -> GitHubUser | None:
        """The person observed: the author of a pull request, or the person itself.

        Parameters:
            subject: A pull request or a person.

        Returns:
            The person; None for a pull request whose author GitHub does not say.
        """
        return subject.author if isinstance(subject, Issue) else subject

    def counts(self, name: str, kinds: tuple[str, ...] | None = None) -> dict[int, int]:
        """A number of every person in the repositories, by the id of the person.

        Parameters:
            name: ``opened`` (pull requests opened), ``closed_own`` (of those, closed by the
                person without merging) or ``reviews`` (reviews given).
            kinds: For ``reviews``, the kinds of reviews that count; all of them for None.
                The reviews on their own pull requests count only with ``own``.

        Returns:
            The numbers by the id of the ``GitHubUser``; people without any are missing.
        """
        states = review_states(kinds)
        others = not own_reviews(kinds)
        key = f"{name}:{','.join(states)}:{others}" if name == "reviews" else name
        if key not in self._counts:
            pulls = Issue.objects.filter(repository__in=self.repositories, pull_request=True)
            if name == "opened":
                rows = pulls.values("author").annotate(number=Count("pk"))
            elif name == "closed_own":
                rows = (
                    pulls.filter(state=Issue.CLOSED, merged__isnull=True, closed_by=F("author"))
                    .values("author")
                    .annotate(number=Count("pk"))
                )
            else:
                reviews = Review.objects.filter(
                    Q(issue__repository__in=self.repositories), state__in=states
                )
                if others:  # not on their own pull requests
                    reviews = reviews.exclude(author=F("issue__author"))
                rows = reviews.values("author").annotate(number=Count("pk"))
            self._counts[key] = {row["author"]: row["number"] for row in rows if row["author"]}
        return self._counts[key]

    def count(self, name: str, person: GitHubUser, kinds: tuple[str, ...] | None = None) -> int:
        """A number of a person, see :meth:`counts`.

        Parameters:
            name: ``opened``, ``closed_own`` or ``reviews``.
            person: The person.
            kinds: For ``reviews``, the kinds of reviews that count; all of them for None.
                The reviews on their own pull requests count only with ``own``.

        Returns:
            The number.
        """
        return self.counts(name, kinds).get(person.pk, 0)
