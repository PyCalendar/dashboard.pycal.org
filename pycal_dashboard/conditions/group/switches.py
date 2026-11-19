"""A group whose choices are switches, of which any one applies, such as the states of a branch."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from django.utils.translation import gettext

from pycal_dashboard.conditions.group.base import ConditionGroup
from pycal_dashboard.errors import ConditionInputMissing, ConditionInputUnknown

if TYPE_CHECKING:
    from django.http import QueryDict

    from pycal_dashboard.conditions.condition.base import Condition
    from pycal_dashboard.models import Issue


class SwitchesGroup(ConditionGroup):
    """Switches of conditions, on or off: the column applies when one switched on holds.

    Attributes:
        switches: Each switch: its name in the address, its condition and its text.
    """

    switches: ClassVar[tuple[tuple[str, type[Condition], str], ...]] = ()
    # the switches of which exactly one holds for a pull request whose data is known
    exclusive: ClassVar[tuple[str, ...]] = ()
    # the sentence of the group, with %(states)s: positive and negative
    phrase: ClassVar[tuple[str, str]] = ("", "")
    # the words of switches in the sentence where they differ from their texts
    words: ClassVar[dict[str, str]] = {}

    @classmethod
    def names(cls) -> list[str]:
        """The names of the switches, in their order."""
        return [name for name, _condition, _text in cls.switches]

    @classmethod
    def check(cls, choices: tuple[str, ...]) -> tuple[str, ...]:
        """Check the switches that are on.

        Parameters:
            choices: The names of the switches that are on.

        Returns:
            The choices, in the order of the switches.

        Raises:
            ConditionInputMissing: No switch is on.
            ConditionInputUnknown: A name is not one of the switches.
        """
        unknown = [name for name in choices if name not in cls.names()]
        if unknown:
            raise ConditionInputUnknown(f"{cls.id}: {', '.join(unknown)}")
        if not choices:
            raise ConditionInputMissing(f"{cls.id}: {', '.join(cls.names())}")
        return tuple(name for name in cls.names() if name in choices)

    @classmethod
    def parse(cls, form: QueryDict) -> tuple[str, ...]:
        """The switches that are on in a form: the checkboxes ``<group>``.

        Parameters:
            form: The form.

        Returns:
            The choices.
        """
        return cls.check(tuple(form.getlist(cls.id)))

    @classmethod
    def results(cls, issue: Issue) -> dict[str, bool | None]:
        """Whether the condition of each switch holds for a pull request.

        Parameters:
            issue: The pull request.

        Returns:
            The result of each switch by its name.
        """
        return {name: condition.check(issue, {}) for name, condition, _text in cls.switches}

    @classmethod
    def applies(cls, issue: Issue, choices: tuple[str, ...]) -> bool | None:
        """Whether one of the switches that are on holds.

        Parameters:
            issue: The pull request.
            choices: The switches that are on.

        Returns:
            True if one holds; None if none holds and one cannot be assessed.
        """
        results = cls.results(issue)
        chosen = [results[name] for name in choices]
        if any(chosen):
            return True
        return None if None in chosen else False

    @classmethod
    def cell(cls, issue: Issue, choices: tuple[str, ...]) -> list[dict]:
        """The texts of all switches that hold, such as ``outdated, conflict``.

        Parameters:
            issue: The pull request.
            choices: The switches that are on.

        Returns:
            Each text that holds, with its name as its kind.
        """
        results = cls.results(issue)
        return [
            {"text": gettext(text), "kind": name}
            for name, _condition, text in cls.switches
            if results[name]
        ]

    @classmethod
    def opposite(cls, choices: tuple[str, ...]) -> tuple[str, ...] | None:
        """The other switches of those of which exactly one holds.

        Such as closed and merged for open.

        Parameters:
            choices: The switches that are on.

        Returns:
            The other switches; None if a switch is not one of those, or all are on.
        """
        if not set(choices) <= set(cls.exclusive) or set(choices) == set(cls.exclusive):
            return None
        return tuple(name for name in cls.exclusive if name not in choices)

    @classmethod
    def sentence(cls, choices: tuple[str, ...], negative: bool = False) -> str:
        """Such as ``its branch is outdated or in conflict``.

        Parameters:
            choices: The switches that are on.
            negative: The pull requests that it does not apply to.

        Returns:
            The part of the sentence.
        """
        texts = {name: cls.words.get(name, text) for name, _condition, text in cls.switches}
        states = (" " + gettext("or") + " ").join(gettext(texts[name]) for name in choices)
        return gettext(cls.phrase[1 if negative else 0]) % {"states": states}

    @classmethod
    def head(cls, choices: tuple[str, ...]) -> list[dict]:
        """The switches that are on, such as ``conflict``, without the name of the group.

        Parameters:
            choices: The switches that are on.

        Returns:
            Each text, with its name as its kind for its color.
        """
        texts = {name: text for name, _condition, text in cls.switches}
        return [{"text": gettext(texts[name]), "kind": name} for name in choices]

    @classmethod
    def summary(cls, choices: tuple[str, ...]) -> str:
        """Such as ``Branch: outdated, conflict``.

        Parameters:
            choices: The switches that are on.

        Returns:
            The header.
        """
        texts = {name: text for name, _condition, text in cls.switches}
        names = ", ".join(gettext(texts[name]) for name in choices)
        return f"{gettext(cls.title)}: {names}"
