"""The input of several of a few choices, such as the types of the author."""

from dataclasses import dataclass, field
from typing import Any

from pycal_dashboard.conditions.input.base import InputSpec
from pycal_dashboard.errors import ConditionInputMissing, ConditionInputUnknown


@dataclass(frozen=True)
class MultipleChoiceInput(InputSpec):
    """Some of the names of ``choices``, in their order (type ``choices``).

    Attributes:
        choices: The names and their texts, in the order of the form.
    """

    choices: dict[str, str] = field(default_factory=dict)
    type: str = "choices"

    def parse(self, value: Any, context: dict | None = None) -> tuple[str, ...]:  # noqa: ANN401
        """The names, in the order of the choices.

        Parameters:
            value: A list of names, or their text separated by commas.
            context: Not used.

        Returns:
            The names.

        Raises:
            ConditionInputUnknown: A name is none of the choices.
            ConditionInputMissing: No name is chosen.

        Examples:
            >>> spec = MultipleChoiceInput("types", "Types", choices={"a": "A", "b": "B"})
            >>> spec.parse("b, a")
            ('a', 'b')
        """
        names = value.split(",") if isinstance(value, str) else list(value or ())
        names = [str(name).strip() for name in names if str(name).strip()]
        unknown = [name for name in names if name not in self.choices]
        if unknown:
            raise ConditionInputUnknown(f"{self.name}: {', '.join(unknown)}")
        if not names:
            raise ConditionInputMissing(f"{self.name}: {', '.join(self.choices)}")
        return tuple(name for name in self.choices if name in names)

    def widget(self, context: dict | None = None) -> dict:
        """A switch for each choice.

        Parameters:
            context: Not used.

        Returns:
            The kind ``switches`` and the choices with their texts.
        """
        return {"kind": "switches", "choices": list(self.choices.items())}

    def describe(self) -> dict:
        """The input with its choices.

        Returns:
            As ``InputSpec.describe``, with ``choices``.
        """
        return {**super().describe(), "choices": list(self.choices)}
