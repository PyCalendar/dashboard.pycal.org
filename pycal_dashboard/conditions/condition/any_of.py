"""Any of some conditions: it holds when one of them holds, such as open or merged."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from pycal_dashboard.conditions.condition.negation import Not
from pycal_dashboard.conditions.evidence import Evidence

if TYPE_CHECKING:
    from collections.abc import Iterable

    from pycal_dashboard.conditions.state.scope import Scope
    from pycal_dashboard.models import Issue, Project


class AnyOf:
    """Conditions joined by OR: it holds when one of them holds.

    The switches of a column that are on, such as *open* and *merged* of the status, are such
    an OR. It is made of the conditions, and yields them again (:meth:`spec`); its NOT is a
    :class:`~.negation.Not` as that of every condition.

    Attributes:
        conditions: The conditions, in their order.
    """

    id: ClassVar[str] = "any_of"
    title: ClassVar[str] = "Any of"
    description: ClassVar[str] = "One of some conditions holds for a pull request."
    negation: ClassVar[tuple[str, str, str]] = ("", "", "")

    def __init__(self, conditions: Iterable[Any]):
        """Join conditions by OR.

        Parameters:
            conditions: The conditions, such as ``Open()`` and ``Merged()``.
        """
        self.conditions = tuple(conditions)

    def spec(self) -> dict:
        """The spec of the OR, which makes it again: its conditions.

        Returns:
            ``conditions``.
        """
        return {"conditions": self.conditions}

    def __eq__(self, other: object) -> bool:
        return isinstance(other, AnyOf) and other.conditions == self.conditions

    def __hash__(self) -> int:
        return hash((AnyOf, self.conditions))

    def __repr__(self) -> str:
        return f"AnyOf({list(self.conditions)!r})"

    def negate(self) -> Not:
        """The NOT of the OR: none of the conditions holds.

        Returns:
            The OR wrapped in its NOT.
        """
        return Not(self)

    def results(self, issue: Issue, scope: Scope | None = None) -> list[bool | None]:
        """Whether each condition holds for a pull request.

        Parameters:
            issue: The pull request.
            scope: The repositories and the project.

        Returns:
            True, False, or None while not known, of each condition in its order.
        """
        return [condition.check(issue, scope) for condition in self.conditions]

    def check(self, issue: Issue, scope: Scope | None = None) -> bool | None:
        """Whether one of the conditions holds for a pull request.

        Parameters:
            issue: The pull request.
            scope: The repositories and the project.

        Returns:
            True if one holds; None if none holds and one cannot be assessed; else False.
        """
        results = self.results(issue, scope)
        if any(results):
            return True
        return None if None in results else False

    def evidence(
        self, issue: Issue, scope: Scope | None = None, project: Project | None = None
    ) -> list[Evidence]:
        """The evidence of the conditions that hold, or of all of them when none holds.

        Parameters:
            issue: The pull request.
            scope: The repositories and the project.
            project: The project, for its pages.

        Returns:
            The links of the conditions, each once.
        """
        results = self.results(issue, scope)
        holding = [c for c, result in zip(self.conditions, results, strict=True) if result]
        return Evidence.unique(
            [
                found
                for c in holding or self.conditions
                for found in c.evidence(issue, scope, project)
            ]
        )
