"""A condition that is checked on a pull request, such as whether it has a label."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, ClassVar

from pycal_dashboard.conditions.evidence import Evidence
from pycal_dashboard.conditions.state.base import State
from pycal_dashboard.conditions.state.scope import Scope

if TYPE_CHECKING:
    from pycal_dashboard.conditions.spec.base import DataSpec
    from pycal_dashboard.models import Issue, Project


class Condition(State):
    """A condition of a pull request: a state that is true or false.

    A subclass has an ``id``, the ``inputs`` that configure it, the ``data`` that the
    background reads for it, and :meth:`assess`. Each has its page in the documentation,
    ``reference/conditions/<id>.html``, with its API reference at the bottom. The id, inputs,
    data, configuration and description are those of every state (:class:`~.state.base.State`).

    Attributes:
        id: The name of the condition in configurations, such as ``label_exists``.
        title: What it checks, in a few words.
        description: What it checks, in a sentence.
        inputs: What configures it.
        data: What it needs of the pull request.
    """

    section: ClassVar[str] = "conditions"

    @classmethod
    def complete(cls, issue: Issue) -> bool:
        """Whether the data of a pull request is complete, so that the condition can be assessed.

        Parameters:
            issue: The pull request.

        Returns:
            True if every data spec of the condition is complete for it.
        """
        return all(spec.complete(issue) for spec in cls.data)

    @classmethod
    def check(cls, issue: Issue, values: dict, scope: Scope | None = None) -> bool | None:
        """Assess the condition on a pull request, if its data allows it.

        Parameters:
            issue: The pull request (``Issue``); conditions are checked on pull requests only.
            values: The configuration, from
                :meth:`~pycal_dashboard.conditions.state.base.State.configure`.
            scope: The repositories of the project, for the states of its author.

        Returns:
            True or False; None if it is not a pull request or its data is not complete yet.
        """
        if not issue.pull_request or not cls.complete(issue):
            return None
        if not cls.scoped:
            return cls.assess(issue, values)
        scope = scope or Scope.of(issue)
        if not all(spec.complete_in(scope.repositories) for spec in cls.data):
            return None
        return cls.assess(issue, values, scope)

    # the data whose evidence shows the condition, see evidence(); None for all of data
    shown: ClassVar[tuple[DataSpec, ...] | None] = None

    # whether it checks states of the author, counted in the repositories of the project: then
    # assess() takes the scope, and the data of all of them must be complete
    scoped: ClassVar[bool] = False

    @classmethod
    def observe(
        cls, subject: Issue, scope: Scope | None = None, values: dict | None = None
    ) -> bool | None:
        """The condition as a state of a pull request, see :meth:`check`.

        Parameters:
            subject: The pull request.
            scope: The repositories of the project.
            values: The configuration.

        Returns:
            True or False; None while it is not known.
        """
        return cls.check(subject, values or {}, scope)

    @classmethod
    @abstractmethod
    def assess(cls, issue: Issue, values: dict) -> bool:
        """Whether the condition holds for a pull request whose data is complete.

        Parameters:
            issue: The pull request.
            values: The configuration.

        Returns:
            True if it holds.
        """

    @classmethod
    def evidence(
        cls,
        issue: Issue,
        values: dict,
        scope: Scope | None = None,
        project: Project | None = None,
    ) -> list[Evidence]:
        """The least that shows why the condition holds for a pull request, or why not.

        By default, the evidence of its data (:meth:`DataSpec.evidence
        <pycal_dashboard.conditions.spec.base.DataSpec.evidence>`), or of the data in
        ``shown``, each link once.

        Parameters:
            issue: The pull request.
            values: The configuration.
            scope: The repositories of the project, for the states of its author.
            project: The project, for its pages, such as that of the author.

        Returns:
            The links.
        """
        specs = cls.data if cls.shown is None else cls.shown
        return Evidence.unique([found for spec in specs for found in spec.evidence(issue)])
