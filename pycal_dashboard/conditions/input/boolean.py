"""The input of a switch: on or off."""

from dataclasses import dataclass
from typing import Any

from pycal_dashboard.conditions.input.base import InputSpec
from pycal_dashboard.errors import ConditionInputNotBoolean

ON = ("true", "on", "1", "yes")
OFF = ("false", "off", "0", "no", "")


@dataclass(frozen=True)
class BooleanInput(InputSpec):
    """On or off, such as whether reviews of comments only count (type ``bool``)."""

    type: str = "bool"

    def parse(self, value: Any, context: dict | None = None) -> bool:
        """Whether it is on.

        Parameters:
            value: True or False, or its text: ``true``, ``on``, ``1`` or ``yes``; ``false``,
                ``off``, ``0``, ``no`` or "" for off.
            context: Not used.

        Returns:
            True if it is on.

        Raises:
            ConditionInputNotBoolean: It is neither on nor off.

        Examples:
            >>> BooleanInput("comments", "Comments").parse("on")
            True
        """
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        if isinstance(value, str | int) and text in ON:
            return True
        if isinstance(value, str | int) and text in OFF:
            return False
        raise ConditionInputNotBoolean(f"{self.name}: {value!r}")

    def widget(self, context: dict | None = None) -> dict:
        """A switch.

        Parameters:
            context: Not used.

        Returns:
            The kind ``switch``.
        """
        return {"kind": "switch", "attributes": {}}
