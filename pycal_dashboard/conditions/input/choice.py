"""The input of one of a few choices, such as the field of a pull request to match."""

from dataclasses import dataclass, field
from typing import Any

from pycal_dashboard.conditions.input.base import InputSpec
from pycal_dashboard.errors import ConditionInputUnknown


@dataclass(frozen=True)
class ChoiceInput(InputSpec):
    """One of the names of ``choices``, with their texts for people (type ``choice``).

    Attributes:
        choices: The names and their texts, in the order of the form.
    """

    choices: dict[str, str] = field(default_factory=dict)
    type: str = "choice"

    def parse(self, value: Any, context: dict | None = None) -> str:  # noqa: ANN401
        """The name of the choice.

        Parameters:
            value: The name.
            context: Not used.

        Returns:
            The name.

        Raises:
            ConditionInputUnknown: It is none of the choices.

        Examples:
            >>> ChoiceInput("field", "Field", choices={"title": "title"}).parse("title")
            'title'
        """
        if value not in self.choices:
            raise ConditionInputUnknown(f"{self.name}: {value!r}")
        return str(value)

    def widget(self, context: dict | None = None) -> dict:
        """A choice of the names.

        Parameters:
            context: Not used.

        Returns:
            The kind and the choices.
        """
        choices = [{"value": name, "description": text} for name, text in self.choices.items()]
        return {"kind": "choice", "attributes": {}, "choices": choices}

    def describe(self) -> dict:
        """The input with its choices.

        Returns:
            As ``InputSpec.describe``, with ``choices``.
        """
        return {**super().describe(), "choices": list(self.choices)}
