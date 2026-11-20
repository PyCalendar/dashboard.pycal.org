"""An input of a condition that is a number, also with a fraction."""

import math
from dataclasses import dataclass
from typing import Any

from pycal_dashboard.conditions.input.base import InputSpec
from pycal_dashboard.errors import ConditionInputNotNumber, ConditionInputOutOfRange


@dataclass(frozen=True)
class NumberInput(InputSpec):
    """A number such as ``1.5``, within ``minimum`` and ``maximum`` (type ``number``).

    Attributes:
        minimum: The smallest number it may be, None for no limit.
        maximum: The largest number it may be, None for no limit.
    """

    minimum: float | None = None
    maximum: float | None = None
    type: str = "number"

    def parse(self, value: Any, context: dict | None = None) -> float:
        """The number.

        Parameters:
            value: A number or its text, such as ``1.5`` or ``"1.5"`` from a form.
            context: Not used.

        Returns:
            The number.

        Raises:
            ConditionInputNotNumber: It is not a finite number.
            ConditionInputOutOfRange: It is below the minimum or above the maximum.

        Examples:
            >>> NumberInput("ratio", "Ratio", minimum=0).parse("1.5")
            1.5
        """
        if isinstance(value, bool) or not isinstance(value, int | float | str):
            raise ConditionInputNotNumber(f"{self.name}: {value!r}")
        try:
            number = float(value)
        except ValueError:
            raise ConditionInputNotNumber(f"{self.name}: {value!r}") from None
        if not math.isfinite(number):
            raise ConditionInputNotNumber(f"{self.name}: {value!r}")
        if (self.minimum is not None and number < self.minimum) or (
            self.maximum is not None and number > self.maximum
        ):
            raise ConditionInputOutOfRange(
                f"{self.name}: {number} not in [{self.minimum}, {self.maximum}]"
            )
        return number

    def widget(self, context: dict | None = None) -> dict:
        """A field of a number with fractions and its limits.

        Parameters:
            context: Not used.

        Returns:
            The kind and attributes of the field.
        """
        attributes: dict = {"step": "any"}
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
