"""The group of labels: a label is present on a pull request, or absent."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from pycal_dashboard.conditions.condition.label_exists import LabelExists
from pycal_dashboard.conditions.group.base import ConditionGroup
from pycal_dashboard.conditions.input.label import LabelInput
from pycal_dashboard.errors import ConditionInputMissing, ConditionInputUnknown

if TYPE_CHECKING:
    from django.http import QueryDict

    from pycal_dashboard.conditions.state.scope import Scope
    from pycal_dashboard.models import Issue

# the modes and the ids of their conditions: absent is the NOT of present
MODES = {"present": LabelExists.id, "absent": LabelExists.negate().id}


class LabelsGroup(ConditionGroup):
    """A label, present or absent: ``label_exists`` and ``label_absent``.

    The choices are the mode, ``present`` or ``absent``, and the name of the label, which may
    be one that no repository has yet.
    """

    id = "labels"
    title = _("Label")

    @classmethod
    def check(cls, choices: tuple[str, ...]) -> tuple[str, ...]:
        """Check the mode and the name.

        Parameters:
            choices: ``present`` or ``absent``, and the name.

        Returns:
            The choices.

        Raises:
            ConditionInputMissing: There is no name.
            ConditionInputUnknown: The mode is neither present nor absent.
        """
        if len(choices) != 2 or not choices[1].strip():
            raise ConditionInputMissing("labels: label")
        if choices[0] not in MODES:
            raise ConditionInputUnknown(f"labels: {choices[0]}")
        return choices[0], LabelInput("label", "").parse(choices[1])

    @classmethod
    def parse(cls, form: QueryDict) -> tuple[str, ...]:
        """The mode and the name of the label of a form.

        Parameters:
            form: ``mode`` and ``label``.

        Returns:
            The choices.
        """
        return cls.check((form.get("mode", "present"), form.get("label", "")))

    @classmethod
    def specs(cls, choices: tuple[str, ...]) -> list[dict]:
        """``label_exists`` of the label when present, ``label_absent``, its NOT, when absent.

        Parameters:
            choices: The mode and the name.

        Returns:
            The spec.
        """
        return [{"id": MODES[choices[0]], "label": choices[1]}]

    @classmethod
    def choices_of(cls, specs: list[dict]) -> tuple[str, ...] | None:
        """The mode and the name of ``label_exists`` or ``label_absent``.

        Parameters:
            specs: The specs of the conditions.

        Returns:
            The choices; None for other conditions.
        """
        modes = {id: mode for mode, id in MODES.items()}
        if len(specs) != 1 or specs[0].get("id") not in modes:
            return None
        return modes[specs[0]["id"]], specs[0]["label"]

    @classmethod
    def cell(cls, issue: Issue, choices: tuple[str, ...], scope: Scope | None = None) -> list[dict]:
        """Nothing: the label is in the header, the cell says whether it applies.

        Parameters:
            issue: The pull request.
            choices: The mode and the name.
            scope: Not used: the condition is of the pull request itself.

        Returns:
            No parts.
        """
        return []

    @classmethod
    def sentence(cls, choices: tuple[str, ...], negative: bool = False) -> str:
        """Such as ``it has the label bug`` or ``it does not have the label bug``.

        Parameters:
            choices: The mode and the name.
            negative: The pull requests that it does not apply to.

        Returns:
            The part of the sentence.
        """
        has = (choices[0] == "present") != negative
        if has:
            return gettext("it has the label %(name)s") % {"name": choices[1]}
        return gettext("it does not have the label %(name)s") % {"name": choices[1]}

    @classmethod
    def head(cls, choices: tuple[str, ...]) -> list[dict]:
        """The label with its border and color; struck through when it must be absent.

        Parameters:
            choices: The mode and the name.

        Returns:
            The label as one part.
        """
        return [{"text": choices[1], "kind": "label", "absent": choices[0] == "absent"}]

    @classmethod
    def summary(cls, choices: tuple[str, ...]) -> str:
        """Such as ``Label bug: present``.

        Parameters:
            choices: The mode and the name.

        Returns:
            The header.
        """
        mode = gettext("present") if choices[0] == "present" else gettext("absent")
        return gettext("Label %(name)s: %(mode)s") % {"name": choices[1], "mode": mode}
