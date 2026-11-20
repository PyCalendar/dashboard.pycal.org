"""A state of a person, a number counted in the repositories of a project."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, ClassVar

from pycal_dashboard.conditions.state.base import State
from pycal_dashboard.conditions.state.scope import Scope

if TYPE_CHECKING:
    from pycal_dashboard.models import GitHubUser, Issue


class PersonState(State):
    """A number of a person in a project, such as the reviews they gave.

    It is observed on a person in a project (:class:`~.scope.Scope`, all its repositories): the
    author of a pull request, or a person of GitHub. A subclass has :meth:`measure`.

    Attributes:
        phrase: The sentence of the state above a number, with ``%(number)s``: positive and
            negative, for the columns of the table.
    """

    phrase: ClassVar[tuple[str, str]] = ("", "")

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
    def above(
        cls, subject: Issue | GitHubUser, threshold: float, scope: Scope | None = None
    ) -> bool | None:
        """Whether the state is above a number: what the conditions of states check.

        Parameters:
            subject: A pull request or a person, see :meth:`observe`.
            threshold: The number.
            scope: The repositories counted.

        Returns:
            True if it is above; None while it is not known.
        """
        value = cls.observe(subject, scope)
        return None if value is None else value > threshold

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
