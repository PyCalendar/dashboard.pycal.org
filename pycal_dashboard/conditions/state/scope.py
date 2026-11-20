"""Where the states of people are counted: the repositories of a project."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Count, F, Q

from pycal_dashboard.conditions.spec.reviews import COUNTED
from pycal_dashboard.models import GitHubUser, Issue, Review

if TYPE_CHECKING:
    from pycal_dashboard.models import Project, Repository


class Scope:
    """The repositories in which the states of people are counted, such as those of a project.

    The numbers of all people are counted at once, with one query each, the first time one is
    asked for, so that a table of many pull requests asks the database a few times only.
    """

    def __init__(self, repositories: list[Repository]):
        """The repositories counted.

        Parameters:
            repositories: The repositories, such as those of a project that a person sees.
        """
        self.repositories = list(repositories)
        self._counts: dict[str, dict[int, int]] = {}

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
        return cls(list(subject.repositories.all()))

    @staticmethod
    def person(subject: Issue | GitHubUser) -> GitHubUser | None:
        """The person observed: the author of a pull request, or the person itself.

        Parameters:
            subject: A pull request or a person.

        Returns:
            The person; None for a pull request whose author GitHub does not say.
        """
        return subject.author if isinstance(subject, Issue) else subject

    def counts(self, name: str) -> dict[int, int]:
        """A number of every person in the repositories, by the id of the person.

        Parameters:
            name: ``opened`` (pull requests opened), ``closed_own`` (of those, closed by the
                person without merging) or ``reviews`` (reviews given, not only comments).

        Returns:
            The numbers by the id of the ``GitHubUser``; people without any are missing.
        """
        if name not in self._counts:
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
                rows = (
                    Review.objects.filter(
                        Q(issue__repository__in=self.repositories), state__in=COUNTED
                    )
                    .values("author")
                    .annotate(number=Count("pk"))
                )
            self._counts[name] = {row["author"]: row["number"] for row in rows if row["author"]}
        return self._counts[name]

    def count(self, name: str, person: GitHubUser) -> int:
        """A number of a person, see :meth:`counts`.

        Parameters:
            name: ``opened``, ``closed_own`` or ``reviews``.
            person: The person.

        Returns:
            The number.
        """
        return self.counts(name).get(person.pk, 0)
