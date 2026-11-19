"""An input of a condition that is the name of a label of the repository."""

from dataclasses import dataclass
from typing import Any

from pycal_dashboard.conditions.input.text import TextInput
from pycal_dashboard.errors import ConditionLabelUnknown


@dataclass(frozen=True)
class LabelInput(TextInput):
    """The name of a label that the repository has (type ``string-label``).

    The name is restricted to the labels of the repository (``Label``), when the context has
    the ``repository``; its case does not matter, the name is returned as the repository has
    it.
    """

    max_length: int = 100
    type: str = "string-label"

    def parse(self, value: Any, context: dict | None = None) -> str:
        """The name of the label, as the repository writes it.

        Args:
            value: The name.
            context: ``repository``, whose labels the name must be one of; without it, any
                name is taken.

        Returns:
            The name.

        Raises:
            ConditionInputNotText: It is not a text.
            ConditionLabelUnknown: The repository has no label of this name.
        """
        name = super().parse(value, context)
        repository = (context or {}).get("repository")
        if repository is None:
            return name
        label = repository.labels.filter(name__iexact=name).first()
        if label is None:
            raise ConditionLabelUnknown(f"{repository.full_name}: {name}")
        return label.name

    def widget(self, context: dict | None = None) -> dict:
        """A choice of the labels of the repository, or a field of text without one.

        Args:
            context: ``repository``, whose labels are the choices.

        Returns:
            The kind, attributes and ``choices``: name, description and color of each label.
        """
        repository = (context or {}).get("repository")
        if repository is None:
            return super().widget(context)
        choices = [
            {"value": label.name, "description": label.description, "color": label.color}
            for label in repository.labels.all()
        ]
        return {"kind": "choice", "attributes": {}, "choices": choices}
