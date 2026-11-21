"""A state of a person, a number counted in the repositories of a project."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, ClassVar
from urllib.parse import quote

from django.utils.translation import gettext

from pycal_dashboard.conditions.evidence import Evidence
from pycal_dashboard.conditions.input.comparison import compare
from pycal_dashboard.conditions.state.base import State
from pycal_dashboard.conditions.state.scope import Scope

if TYPE_CHECKING:
    from pycal_dashboard.models import GitHubUser, Issue, Project


class PersonState(State):
    """A number of a person in a project, such as the reviews they gave.

    It is observed on a person in a project (:class:`~.scope.Scope`, all its repositories): the
    author of a pull request, or a person of GitHub. A subclass has :meth:`measure`.

    Attributes:
        phrase: The state compared with a number, with ``%(comparison)s`` and ``%(number)s``,
            for the columns of the table, such as ``its author gave %(comparison)s
            %(number)s reviews``.
        counted: Whether it is a count, such as reviews, whose comparisons read *more than*
            and *fewer than*; else a value, such as a ratio: *above* and *below*.
    """

    phrase: ClassVar[str] = ""
    counted: ClassVar[bool] = True

    @classmethod
    def observe(
        cls, subject: Issue | GitHubUser, scope: Scope | None = None, values: dict | None = None
    ) -> float | None:
        """The number of a person: the author of a pull request, or a person of GitHub.

        Parameters:
            subject: A pull request, whose author is observed, or a person (``GitHubUser``).
            scope: The repositories counted, such as those of a project; for a pull request,
                its repository by default.
            values: The configuration, from
                :meth:`~pycal_dashboard.conditions.state.base.State.configure`.

        Returns:
            The number; None without a person or while the data is not complete.
        """
        scope = scope or Scope.of(subject)
        person = scope.person(subject)
        if person is None or not all(spec.complete_in(scope.repositories) for spec in cls.data):
            return None
        return cls.measure(person, scope, values or {})

    @classmethod
    def evidence(cls, issue: Issue, project: Project | None) -> list[Evidence]:
        """The page of the author of a pull request in the project, where they are counted.

        Parameters:
            issue: The pull request.
            project: The project; None for no page.

        Returns:
            The link to the page of the author; none without an author or a project.
        """
        person = Scope.person(issue)
        if person is None or project is None:
            return []
        text = gettext("%(handle)s in the project") % {"handle": person.login}
        return [Evidence(text, project.path(f"contributors/{quote(person.login)}/"))]

    @classmethod
    def compare(
        cls,
        subject: Issue | GitHubUser,
        comparison: str,
        number: float,
        scope: Scope | None = None,
    ) -> bool | None:
        """Whether the state compares with a number: what the conditions of states check.

        Parameters:
            subject: A pull request or a person, see :meth:`observe`.
            comparison: Such as ``below`` or ``at_least``, see ``COMPARISONS`` of
                :mod:`pycal_dashboard.conditions.input.comparison`.
            number: The number.
            scope: The repositories counted.

        Returns:
            True if it holds; None while the state is not known.
        """
        value = cls.observe(subject, scope)
        return None if value is None else compare(value, comparison, number)

    @classmethod
    @abstractmethod
    def measure(cls, person: GitHubUser, scope: Scope, values: dict) -> float:
        """The state of a person whose data is complete.

        Parameters:
            person: The person.
            scope: The repositories counted.
            values: The configuration.

        Returns:
            The number.
        """
