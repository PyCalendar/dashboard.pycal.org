"""An input of a condition that is a text."""

from dataclasses import dataclass
from typing import Any

from pycal_dashboard.conditions.input.base import InputSpec
from pycal_dashboard.errors import ConditionInputNotText


@dataclass(frozen=True)
class TextInput(InputSpec):
    """A text, without spaces around it (type ``string``).

    Attributes:
        max_length: The most characters it may have.
    """

    max_length: int = 200
    type: str = "string"

    def parse(self, value: Any, context: dict | None = None) -> str:
        """The text, stripped.

        Parameters:
            value: The value.
            context: Not used.

        Returns:
            The text.

        Raises:
            ConditionInputNotText: It is not a text, it is empty or too long.

        Examples:
            >>> TextInput("word", "Word").parse("  hello ")
            'hello'
        """
        if not isinstance(value, str) or not value.strip() or len(value) > self.max_length:
            raise ConditionInputNotText(f"{self.name}: {value!r}")
        return value.strip()

    def widget(self, context: dict | None = None) -> dict:
        """A field of text.

        Parameters:
            context: Not used.

        Returns:
            The kind and attributes of the field.
        """
        return {"kind": "text", "attributes": {"maxlength": self.max_length}}
