"""A condition that is checked on a pull request, such as whether it has a label."""

from abc import ABC, abstractmethod
from typing import ClassVar

from django.conf import settings

from pycal_dashboard.conditions.input.base import InputSpec
from pycal_dashboard.conditions.spec.base import DataSpec
from pycal_dashboard.errors import ConditionInputMissing, ConditionInputUnknown


class Condition(ABC):
    """A condition of a pull request, configured by its inputs, assessed from its data.

    A subclass has an ``id``, the ``inputs`` that configure it, the ``data`` that the
    background reads for it, and :meth:`assess`. Each has its page in the documentation,
    ``reference/conditions/<id>.html``, with its API reference at the bottom.

    Attributes:
        id: The name of the condition in configurations, such as ``label_exists``.
        title: What it checks, in a few words.
        description: What it checks, in a sentence.
        inputs: What configures it.
        data: What it needs of the pull request.
    """

    id: ClassVar[str] = ""
    title: ClassVar[str] = ""
    description: ClassVar[str] = ""
    inputs: ClassVar[tuple[InputSpec, ...]] = ()
    data: ClassVar[tuple[DataSpec, ...]] = ()

    @classmethod
    def configure(cls, config: dict | None = None, context: dict | None = None) -> dict:
        """Check a configuration of the condition and return its values.

        Args:
            config: The inputs by name, such as ``{"label": "bug"}``.
            context: What the inputs may need, such as the ``repository``.

        Returns:
            The value of every input; the default for one that is not required and not given.

        Raises:
            ConditionInputMissing: A required input is not given.
            ConditionInputUnknown: The configuration has an input that the condition does not
                know.
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
    def complete(cls, issue) -> bool:
        """Whether the data of a pull request is complete, so that the condition can be assessed.

        Args:
            issue: The pull request.

        Returns:
            True if every data spec of the condition is complete for it.
        """
        return all(spec.complete(issue) for spec in cls.data)

    @classmethod
    def check(cls, issue, values: dict) -> bool | None:
        """Assess the condition on a pull request, if its data allows it.

        Args:
            issue: The pull request (``Issue``); conditions are checked on pull requests only.
            values: The configuration, from :meth:`configure`.

        Returns:
            True or False; None if it is not a pull request or its data is not complete yet.
        """
        if not issue.pull_request or not cls.complete(issue):
            return None
        return cls.assess(issue, values)

    @classmethod
    @abstractmethod
    def assess(cls, issue, values: dict) -> bool:
        """Whether the condition holds for a pull request whose data is complete.

        Args:
            issue: The pull request.
            values: The configuration.

        Returns:
            True if it holds.
        """

    @classmethod
    def docs_url(cls) -> str:
        """The page of the condition in the documentation."""
        return f"{settings.DOCS_URL.rstrip('/')}/reference/conditions/{cls.id}.html"

    @classmethod
    def describe(cls) -> dict:
        """The condition for the JSON and the documentation.

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
