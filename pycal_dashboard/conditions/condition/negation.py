"""The NOT of a condition: it holds when the condition does not, such as ``label_absent``."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pycal_dashboard.conditions.state.base import State

if TYPE_CHECKING:
    from pycal_dashboard.conditions.evidence import Evidence
    from pycal_dashboard.conditions.state.scope import Scope
    from pycal_dashboard.models import Issue, Project

# the attributes of the NOT itself: never those of its condition
OWN = ("condition", "id", "title", "description")


class Not:
    """The NOT of a condition, wrapped around it: it holds exactly when the condition does not.

    Every condition can be inverted: :meth:`Condition.negate
    <pycal_dashboard.conditions.condition.base.Condition.negate>` wraps it, and :meth:`negate`
    of the NOT gives the condition back. The NOT of a class of conditions, such as
    ``label_absent`` of ``label_exists``, makes conditions as the class does when it is called
    with a spec: the NOT of the condition made of the class. The NOT has its own ``id``,
    ``title`` and ``description`` (``negation`` of the condition); the rest of the condition is
    seen through it: its inputs, its values and spec, the data it needs, when the data is
    complete and its evidence, which shows why it holds or not. Its result is the opposite of
    that of the condition, and not known while that is not known.

    Attributes:
        condition: The condition that it inverts, or its class.
        id: The name in configurations, such as ``label_absent``.
        title: What it checks, in a few words.
        description: What it checks, in a sentence.
    """

    def __init__(self, condition: Any, id: str = "", title: str = "", description: str = ""):  # noqa: ANN401 - a condition or its class
        """Wrap a condition, or its class.

        Parameters:
            condition: The condition, such as ``LabelExists({"label": "bug"})``, or its class.
            id: The name of the NOT; that of ``negation`` of the condition, else ``not_`` and
                its id.
            title: Its title; that of ``negation``, else ``Not:`` and the title of the
                condition.
            description: Its description; that of ``negation``, else ``Not:`` and that of the
                condition.
        """
        named = getattr(condition, "negation", ("", "", ""))
        self.condition = condition
        self.id = id or named[0] or f"not_{condition.id}"
        self.title = title or named[1] or f"Not: {condition.title}"
        self.description = description or named[2] or f"Not: {condition.description}"

    def __getattr__(self, name: str) -> Any:  # noqa: ANN401 - whatever the condition has
        """The attributes of the condition that the NOT does not change, such as ``inputs``.

        The first time, the attribute becomes a property of the class, which reads it of the
        condition: the next time, it is found without this method.

        Parameters:
            name: The name of the attribute.

        Returns:
            That of the condition.

        Raises:
            AttributeError: The condition does not have it, or it is one of the NOT itself.
        """
        if name.startswith("__") or name in OWN:  # such as for copying, or before __init__
            raise AttributeError(name)
        value = getattr(self.condition, name)
        setattr(type(self), name, property(lambda self: getattr(self.condition, name)))
        return value

    def __call__(self, spec: dict | None = None, context: dict | None = None) -> Not:
        """The NOT of the condition made of the class of the condition and a spec.

        Parameters:
            spec: The inputs by name, such as ``{"label": "bug"}``.
            context: What the inputs may need, such as the ``repository``.

        Returns:
            The NOT of the condition, with the id, title and description of this NOT.
        """
        return Not(self.condition(spec, context), self.id, self.title, self.description)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Not) and (other.condition, other.id) == (self.condition, self.id)

    def __hash__(self) -> int:
        return hash((Not, self.condition, self.id))

    def __repr__(self) -> str:
        name = getattr(self.condition, "__name__", None) or repr(self.condition)
        return f"Not({name}, {self.id!r})"

    def negate(self) -> Any:  # noqa: ANN401 - a condition or its class
        """The condition that the NOT inverts: the NOT of a NOT is the condition.

        Returns:
            The condition, or its class.
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

    def check(self, issue: Issue, scope: Scope | None = None) -> bool | None:
        """Whether the condition does not hold for a pull request, if its data allows it.

        Parameters:
            issue: The pull request.
            scope: The repositories of the project, for the states of its author.

        Returns:
            True or False; None while the condition cannot be assessed.
        """
        return self.result(self.condition.check(issue, scope))

    def observe(self, subject: Issue, scope: Scope | None = None) -> bool | None:
        """The NOT as a state of a pull request, see :meth:`check`.

        Parameters:
            subject: The pull request.
            scope: The repositories of the project.

        Returns:
            True or False; None while it is not known.
        """
        return self.check(subject, scope)

    def evidence(
        self, issue: Issue, scope: Scope | None = None, project: Project | None = None
    ) -> list[Evidence]:
        """The evidence of the condition: it shows why it holds, and so why the NOT does not.

        Parameters:
            issue: The pull request.
            scope: The repositories of the project.
            project: The project, for its pages.

        Returns:
            The links.
        """
        return self.condition.evidence(issue, scope, project)

    def docs_url(self) -> str:
        """The page of the NOT in the documentation, by its own id."""
        return State.page(self.section, self.id)

    def describe(self) -> dict:
        """The NOT for the JSON and the documentation, by its own id, title and description.

        See :meth:`State.described <pycal_dashboard.conditions.state.base.State.described>`.

        Returns:
            Its id, title, description, and the inputs, data and page of the condition.
        """
        return State.described(self)
