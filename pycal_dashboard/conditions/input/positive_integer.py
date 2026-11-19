"""An input of a condition that is a positive whole number."""

from dataclasses import dataclass

from pycal_dashboard.conditions.input.integer import IntegerInput


@dataclass(frozen=True)
class PositiveIntegerInput(IntegerInput):
    """A whole number from 1 up (type ``positive-int``)."""

    minimum: int | None = 1
    type: str = "positive-int"
