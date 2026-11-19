"""An input of a condition that is a whole number."""

from dataclasses import dataclass
from typing import Any

from pycal_dashboard.conditions.input.base import InputSpec
from pycal_dashboard.errors import ConditionInputNotInteger, ConditionInputOutOfRange


@dataclass(frozen=True)
class IntegerInput(InputSpec):
    """A whole number, between ``minimum`` and ``maximum`` if they are set (type ``int``).

    Attributes:
        minimum: The smallest number it may be, None for no limit.
        maximum: The largest number it may be, None for no limit.
    """

    minimum: int | None = None
    maximum: int | None = None
    type: str = "int"

    def parse(self, value: Any, context: dict | None = None) -> int:
        """The number.

        Parameters:
            value: A number or its text, such as ``3`` or ``"3"`` from a form.
            context: Not used.

        Returns:
            The number.

        Raises:
            ConditionInputNotInteger: It is not a whole number.
            ConditionInputOutOfRange: It is below the minimum or above the maximum.

        Examples:
            >>> IntegerInput("days", "Days", minimum=0).parse("7")
            7
        """
        if isinstance(value, bool) or not isinstance(value, int | str):
            raise ConditionInputNotInteger(f"{self.name}: {value!r}")
        try:
            number = int(value)
        except ValueError:
            raise ConditionInputNotInteger(f"{self.name}: {value!r}") from None
        if (self.minimum is not None and number < self.minimum) or (
            self.maximum is not None and number > self.maximum
        ):
            raise ConditionInputOutOfRange(
                f"{self.name}: {number} not in [{self.minimum}, {self.maximum}]"
            )
        return number

    def widget(self, context: dict | None = None) -> dict:
        """A field of a number with its limits.

        Parameters:
            context: Not used.

        Returns:
            The kind and attributes of the field.
        """
        attributes: dict = {"step": 1}
        if self.minimum is not None:
            attributes["min"] = self.minimum
        if self.maximum is not None:
            attributes["max"] = self.maximum
        return {"kind": "number", "attributes": attributes}

    def describe(self) -> dict:
        """The input with its limits.

        Returns:
            As ``InputSpec.describe``, with ``minimum`` and ``maximum``.
        """
        return {**super().describe(), "minimum": self.minimum, "maximum": self.maximum}
