"""A state of a pull request or of its author, configured by inputs, observed from data.

A condition (:class:`~pycal_dashboard.conditions.condition.base.Condition`) is a state of a pull
request that is true or false; a state of a person
(:class:`~pycal_dashboard.conditions.state.person.PersonState`) is a number, such as how many
reviews a person gave. They share their id, inputs, data, configuration, page of documentation
and description.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar

from django.conf import settings

from pycal_dashboard.conditions.input.base import InputSpec
from pycal_dashboard.conditions.spec.base import DataSpec
from pycal_dashboard.errors import ConditionInputMissing, ConditionInputUnknown

if TYPE_CHECKING:
    from pycal_dashboard.conditions.state.scope import Scope
    from pycal_dashboard.models import GitHubUser, Issue


class State(ABC):
    """Something observed on a pull request, configured by its inputs, assessed from its data.

    A subclass has an ``id``, the ``inputs`` that configure it, the ``data`` that the
    background reads for it, and :meth:`observe`. Each has its page in the documentation,
    ``reference/<section>/<id>.html``, with its API reference at the bottom.

    Attributes:
        id: The name in configurations, such as ``reviews_given``.
        title: What it observes, in a few words.
        description: What it observes, in a sentence.
        inputs: What configures it.
        data: What it needs of the pull requests.
        section: The folder of its page in the reference of the documentation.
    """

    id: ClassVar[str] = ""
    title: ClassVar[str] = ""
    description: ClassVar[str] = ""
    inputs: ClassVar[tuple[InputSpec, ...]] = ()
    data: ClassVar[tuple[DataSpec, ...]] = ()
    section: ClassVar[str] = "states"
    # the states that it is made of, such as reviews_given for review_ratio: their inputs are
    # its inputs, too (see inputs_of), so that a choice travels to all that use it
    parts: ClassVar[tuple[type[State], ...]] = ()

    @staticmethod
    def inputs_of(*states: type[State]) -> tuple[InputSpec, ...]:
        """The inputs of states and of their parts, each name once, in their order.

        A state made of others, or a condition that compares a state, has their inputs, so that
        a choice of them, such as the kinds of reviews, is the same wherever it is used.

        Parameters:
            *states: The states.

        Returns:
            The inputs.
        """
        found: dict[str, InputSpec] = {}
        for state in states:
            for spec in (*State.inputs_of(*state.parts), *state.inputs):
                found.setdefault(spec.name, spec)
        return tuple(found.values())

    @classmethod
    def configure(cls, config: dict | None = None, context: dict | None = None) -> dict:
        """Check a configuration and return its values.

        Parameters:
            config: The inputs by name, such as ``{"label": "bug"}``.
            context: What the inputs may need, such as the ``repository``.

        Returns:
            The value of every input; the default for one that is not required and not given.

        Raises:
            ConditionInputMissing: A required input is not given.
            ConditionInputUnknown: The configuration has an input that it does not know.
            ConditionError: An input is wrong: a subclass of it says how.
        """
        config = dict(config or {})
        names = {spec.name for spec in cls.inputs}
        unknown = sorted(set(config) - names)
        if unknown:
            raise ConditionInputUnknown(f"{cls.id}: {', '.join(unknown)}")
        values = {}
        for spec in cls.inputs:
            if spec.name in config:
                values[spec.name] = spec.parse(config[spec.name], context)
            elif spec.required:
                raise ConditionInputMissing(f"{cls.id}: {spec.name}")
            else:
                values[spec.name] = spec.default
        return values

    @classmethod
    @abstractmethod
    def observe(
        cls, subject: Issue | GitHubUser, scope: Scope | None = None, values: dict | None = None
    ) -> bool | float | None:
        """The state of a pull request or of a person.

        Parameters:
            subject: A pull request, or a person (``GitHubUser``).
            scope: The repositories counted, such as those of a project; for a pull request,
                its repository by default.
            values: The configuration, from :meth:`configure`.

        Returns:
            True or False for a condition, a number for a state of a person; None while it is
            not known.
        """

    @classmethod
    def docs_url(cls) -> str:
        """The page in the documentation."""
        return f"{settings.DOCS_URL.rstrip('/')}/reference/{cls.section}/{cls.id}.html"

    @classmethod
    def describe(cls) -> dict:
        """The state for the JSON and the documentation.

        Returns:
            Its id, title, description, inputs, data and page.
        """
        return {
            "id": cls.id,
            "title": str(cls.title),
            "description": str(cls.description),
            "inputs": [spec.describe() for spec in cls.inputs],
            "data": [spec.describe() for spec in cls.data],
            "documentation": cls.docs_url(),
        }
