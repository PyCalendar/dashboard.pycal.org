"""An input of a condition that is a range of whole numbers."""

from dataclasses import dataclass
from typing import Any

from pycal_dashboard.conditions.input.integer import IntegerInput
from pycal_dashboard.errors import ConditionInputNotInteger, ConditionRangeInvalid


@dataclass(frozen=True)
class RangeInput(IntegerInput):
    """Two whole numbers, ``[low, high]``, low not above high (type ``range``).

    The limits ``minimum`` and ``maximum`` apply to both.
    """

    type: str = "range"

    def parse(self, value: Any, context: dict | None = None) -> tuple[int, int]:
        """The range.

        Parameters:
            value: Two numbers, such as ``[1, 5]`` or, from a form, ``"1-5"``.
            context: Not used.

        Returns:
            The low and the high number.

        Raises:
            ConditionRangeInvalid: It is not two numbers, or the first is above the second.
            ConditionInputOutOfRange: A number is outside the limits.

        Examples:
            >>> RangeInput("size", "Size", minimum=0).parse("1-5")
            (1, 5)
        """
        if isinstance(value, str):
            value = value.split("-", 1) if value.count("-") == 1 else [value]
        if not isinstance(value, list | tuple) or len(value) != 2:
            raise ConditionRangeInvalid(f"{self.name}: {value!r}")
        try:
            low, high = (IntegerInput.parse(self, number) for number in value)
        except ConditionInputNotInteger:
            raise ConditionRangeInvalid(f"{self.name}: {value!r}") from None
        if low > high:
            raise ConditionRangeInvalid(f"{self.name}: {low} > {high}")
        return low, high

    def widget(self, context: dict | None = None) -> dict:
        """Two fields of numbers with the limits.

        Parameters:
            context: Not used.

        Returns:
            The kind and attributes of each field.
        """
        return {**super().widget(context), "kind": "range"}
