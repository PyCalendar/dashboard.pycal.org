"""The input of a condition: how it is configured, checked, and asked for in a form."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class InputSpec(ABC):
    """One input that configures a condition, such as the name of a label.

    A subclass checks a value (:meth:`parse`) and describes the field of a form that asks for it
    (:meth:`widget`), which the partial ``conditions/_input.html`` shows.

    Attributes:
        name: The key of the input in the configuration, such as ``label``.
        label: What the field is called in a form.
        help: A sentence that explains the input.
        required: Whether the configuration must have it.
        default: The value without it, when it is not required.
    """

    name: str
    label: str
    help: str = ""
    required: bool = True
    default: Any = None

    # the name of the type in the documentation and the JSON, such as "string-label"
    type: str = ""

    @abstractmethod
    def parse(self, value: Any, context: dict | None = None) -> Any:
        """Check a value of the input and return it as the condition uses it.

        Args:
            value: The value of the configuration, such as from JSON or a form.
            context: What the check may need, such as the ``repository`` for a label.

        Returns:
            The value.

        Raises:
            ConditionError: A subclass of it says what is wrong.
        """

    def widget(self, context: dict | None = None) -> dict:
        """The field of a form that asks for the input, for ``conditions/_input.html``.

        Args:
            context: What the field may need, such as the ``repository`` for its labels.

        Returns:
            ``kind`` (``text``, ``number``, ``range`` or ``choice``) and the attributes of the
            field.
        """
        return {"kind": "text", "attributes": {}}

    def describe(self) -> dict:
        """The input for the JSON and the documentation.

        Returns:
            Its name, type, label, help, whether it is required and its default.
        """
        return {
            "name": self.name,
            "type": self.type,
            "label": str(self.label),
            "help": str(self.help),
            "required": self.required,
            "default": self.default,
        }
