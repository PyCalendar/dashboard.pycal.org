"""A condition that is checked on a pull request, such as whether it has a label."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, ClassVar

from pycal_dashboard.conditions.condition.negate_method import NegateMethod
from pycal_dashboard.conditions.evidence import Evidence
from pycal_dashboard.conditions.state.base import State
from pycal_dashboard.conditions.state.scope import Scope

if TYPE_CHECKING:
    from pycal_dashboard.conditions.spec.base import DataSpec
    from pycal_dashboard.models import Issue, Project


class Condition(State):
    """A condition of a pull request: a state that is true or false.

    A subclass has an ``id``, the ``inputs`` that configure it, the ``data`` that the
    background reads for it, and :meth:`assess`. A condition is made of its class and a
    creation spec, the inputs by name (``LabelExists({"label": "bug"})``), and yields the same
    spec again (:meth:`spec`); how the conditions are written down, such as in the address of
    the table of pull requests, is not their business, but that of the
    :class:`~pycal_dashboard.conditions.factory.ConditionFactory`. Every condition can be
    inverted: :meth:`negate` wraps it, or its class, in its NOT (:class:`~.negation.Not`),
    named by ``negation``. Each has its page in the documentation,
    ``reference/conditions/<id>.html``, with its API reference at the bottom. The id, inputs,
    data, configuration and description are those of every state
    (:class:`~.state.base.State`).

    Attributes:
        id: The name of the condition in configurations, such as ``label_exists``.
        title: What it checks, in a few words.
        description: What it checks, in a sentence.
        inputs: What configures it.
        data: What it needs of the pull request.
        values: The value of every input, checked, of a condition made of the class.
    """

    section: ClassVar[str] = "conditions"
    # the id, title and description of its NOT (negate()), such as label_absent of label_exists;
    # empty for those that the NOT makes of its own
    negation: ClassVar[tuple[str, str, str]] = ("", "", "")
    negate = NegateMethod()

    def __init__(self, spec: dict | None = None, context: dict | None = None):
        """Make the condition of a creation spec.

        Parameters:
            spec: The inputs by name, such as ``{"label": "bug"}``; as :meth:`spec` yields them.
            context: What the inputs may need, such as the ``repository``.

        Raises:
            ConditionInputMissing: A required input is not given.
            ConditionInputUnknown: The spec has an input that the condition does not know.
            ConditionError: An input is wrong: a subclass of it says how.
        """
        self.values = self.configure(spec, context)

    def spec(self) -> dict:
        """The spec of the condition, which makes it again: the value of every input.

        Returns:
            The inputs by name, such as ``{"label": "bug"}``.

        Examples:
            >>> from pycal_dashboard.conditions.condition.label_exists import LabelExists
            >>> LabelExists({"label": "bug"}).spec()
            {'label': 'bug'}
        """
        return dict(self.values)

    def __eq__(self, other: object) -> bool:
        return type(other) is type(self) and other.values == self.values

    def __hash__(self) -> int:
        return hash((type(self), repr(sorted(self.values.items()))))

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.values!r})"

    @classmethod
    def complete(cls, issue: Issue) -> bool:
        """Whether the data of a pull request is complete, so that the condition can be assessed.

        Parameters:
            issue: The pull request.

        Returns:
            True if every data spec of the condition is complete for it.
        """
        return all(spec.complete(issue) for spec in cls.data)

    def check(self, issue: Issue, scope: Scope | None = None) -> bool | None:
        """Assess the condition on a pull request, if its data allows it.

        Parameters:
            issue: The pull request (``Issue``); conditions are checked on pull requests only.
            scope: The repositories of the project, for the states of its author.

        Returns:
            True or False; None if it is not a pull request or its data is not complete yet.
        """
        if not issue.pull_request or not self.complete(issue):
            return None
        if not self.scoped:
            return self.assess(issue)
        scope = scope or Scope.of(issue)
        if not all(spec.complete_in(scope.repositories) for spec in self.data):
            return None
        return self.assess(issue, scope)

    # the data whose evidence shows the condition, see evidence(); None for all of data
    shown: ClassVar[tuple[DataSpec, ...] | None] = None

    # whether it checks states of the author, counted in the repositories of the project: then
    # assess() takes the scope, and the data of all of them must be complete
    scoped: ClassVar[bool] = False

    def observe(self, subject: Issue, scope: Scope | None = None) -> bool | None:
        """The condition as a state of a pull request, see :meth:`check`.

        Parameters:
            subject: The pull request.
            scope: The repositories of the project.

        Returns:
            True or False; None while it is not known.
        """
        return self.check(subject, scope)

    @abstractmethod
    def assess(self, issue: Issue) -> bool:
        """Whether the condition holds for a pull request whose data is complete.

        Parameters:
            issue: The pull request.

        Returns:
            True if it holds.
        """

    def evidence(
        self, issue: Issue, scope: Scope | None = None, project: Project | None = None
    ) -> list[Evidence]:
        """The least that shows why the condition holds for a pull request, or why not.

        By default, the evidence of its data (:meth:`DataSpec.evidence
        <pycal_dashboard.conditions.spec.base.DataSpec.evidence>`), or of the data in
        ``shown``, each link once.

        Parameters:
            issue: The pull request.
            scope: The repositories of the project, for the states of its author.
            project: The project, for its pages, such as that of the author.

        Returns:
            The links.
        """
        specs = self.data if self.shown is None else self.shown
        return Evidence.unique([found for spec in specs for found in spec.evidence(issue)])
