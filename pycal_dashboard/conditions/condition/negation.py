"""The NOT of a condition: it holds when the condition does not, such as ``label_absent``."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pycal_dashboard.conditions.state.base import State

if TYPE_CHECKING:
    from pycal_dashboard.conditions.condition.base import Condition
    from pycal_dashboard.conditions.evidence import Evidence
    from pycal_dashboard.conditions.state.scope import Scope
    from pycal_dashboard.models import Issue, Project


class Not:
    """The NOT of a condition, wrapped around it: it holds exactly when the condition does not.

    Every condition can be inverted: :meth:`Condition.negate
    <pycal_dashboard.conditions.condition.base.Condition.negate>` wraps it, and :meth:`negate`
    of the NOT gives the condition back. The NOT has its own ``id``, ``title`` and
    ``description``, such as ``label_absent`` of ``label_exists``; the rest of the condition is
    seen through it: its inputs, the data it needs, when the data is complete and its evidence,
    which shows why it holds or not. Its result is the opposite of that of the condition, and
    not known while that is not known.

    Attributes:
        condition: The condition that it inverts.
        id: The name in configurations, such as ``label_absent``.
        title: What it checks, in a few words.
        description: What it checks, in a sentence.
    """

    def __init__(
        self, condition: type[Condition], id: str = "", title: str = "", description: str = ""
    ):
        """Wrap a condition.

        Parameters:
            condition: The condition, such as ``LabelExists``.
            id: The name of the NOT; ``not_`` and the id of the condition by default.
            title: Its title; ``Not:`` and the title of the condition by default.
            description: Its description; ``Not:`` and that of the condition by default.
        """
        self.condition = condition
        self.id = id or f"not_{condition.id}"
        self.title = title or f"Not: {condition.title}"
        self.description = description or f"Not: {condition.description}"

    def __getattr__(self, name: str) -> Any:  # noqa: ANN401 - whatever the condition has
        """The attributes of the condition that the NOT does not change, such as ``inputs``.

        Parameters:
            name: The name of the attribute.

        Returns:
            That of the condition.
        """
        if name.startswith("__"):  # such as for copying: not those of the condition
            raise AttributeError(name)
        return getattr(self.condition, name)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Not) and (other.condition, other.id) == (self.condition, self.id)

    def __hash__(self) -> int:
        return hash((Not, self.condition, self.id))

    def __repr__(self) -> str:
        return f"Not({self.condition.__name__}, {self.id!r})"

    def negate(self) -> type[Condition]:
        """The condition that the NOT inverts: the NOT of a NOT is the condition.

        Returns:
            The condition.
        """
        return self.condition

    @staticmethod
    def result(value: bool | None) -> bool | None:
        """The opposite of a result, which stays not known while it is not known.

        Parameters:
            value: True, False, or None while it is not known.

        Returns:
            The opposite; None for None.

        Examples:
            >>> Not.result(True), Not.result(None)
            (False, None)
        """
        return None if value is None else not value

    def assess(self, issue: Issue, values: dict, *scope: Scope) -> bool:
        """Whether the condition does not hold for a pull request whose data is complete.

        Parameters:
            issue: The pull request.
            values: The configuration.
            *scope: The repositories of the project, for a condition of the author.

        Returns:
            True if the condition does not hold.
        """
        return not self.condition.assess(issue, values, *scope)

    def check(self, issue: Issue, values: dict, scope: Scope | None = None) -> bool | None:
        """Whether the condition does not hold for a pull request, if its data allows it.

        Parameters:
            issue: The pull request.
            values: The configuration.
            scope: The repositories of the project, for the states of its author.

        Returns:
            True or False; None while the condition cannot be assessed.
        """
        return self.result(self.condition.check(issue, values, scope))

    def observe(
        self, subject: Issue, scope: Scope | None = None, values: dict | None = None
    ) -> bool | None:
        """The NOT as a state of a pull request, see :meth:`check`.

        Parameters:
            subject: The pull request.
            scope: The repositories of the project.
            values: The configuration.

        Returns:
            True or False; None while it is not known.
        """
        return self.result(self.condition.observe(subject, scope, values))

    def evidence(
        self,
        issue: Issue,
        values: dict,
        scope: Scope | None = None,
        project: Project | None = None,
    ) -> list[Evidence]:
        """The evidence of the condition: it shows why it holds, and so why the NOT does not.

        Parameters:
            issue: The pull request.
            values: The configuration.
            scope: The repositories of the project.
            project: The project, for its pages.

        Returns:
            The links.
        """
        return self.condition.evidence(issue, values, scope, project)

    def docs_url(self) -> str:
        """The page of the NOT in the documentation, by its own id."""
        return State.docs_url.__func__(self)

    def describe(self) -> dict:
        """The NOT for the JSON and the documentation, by its own id, title and description.

        See :meth:`State.describe <pycal_dashboard.conditions.state.base.State.describe>`.

        Returns:
            Its id, title, description, and the inputs, data and page of the condition.
        """
        return State.describe.__func__(self)
