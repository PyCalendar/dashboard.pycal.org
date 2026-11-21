"""The group of texts: the title or the description of a pull request matches."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from pycal_dashboard.conditions.condition.text_matches import TextMatches
from pycal_dashboard.conditions.group.base import ConditionGroup
from pycal_dashboard.conditions.text_match import FIELDS, MODES, check
from pycal_dashboard.errors import ConditionInputMissing, ConditionInputUnknown

if TYPE_CHECKING:
    from django.http import QueryDict

    from pycal_dashboard.conditions.state.scope import Scope
    from pycal_dashboard.models import Issue

CASE = "case"  # the choice of matching the case of letters; else it does not matter


def values(choices: tuple[str, ...]) -> dict:
    """The configuration of the condition ``text_matches`` of the choices of a column.

    Parameters:
        choices: The field, the mode, the text and maybe ``case``.

    Returns:
        ``field``, ``mode``, ``text`` and ``case_sensitive``.

    Examples:
        >>> values(("title", "starts", "fix", "case"))["case_sensitive"]
        True
    """
    return {
        "field": choices[0],
        "mode": choices[1],
        "text": choices[2],
        "case_sensitive": CASE in choices[3:],
    }


class TextGroup(ConditionGroup):
    """A text of a pull request matches: the condition ``text_matches``.

    The choices are the field (``title`` or ``description``), the mode (``starts``,
    ``ends``, ``contains`` or ``regex``), the text, and ``case`` when the case of letters
    matters.
    """

    id = "text"
    title = _("Text")
    fields = FIELDS  # for the menu of the column
    modes = MODES

    @classmethod
    def check(cls, choices: tuple[str, ...]) -> tuple[str, ...]:
        """Check the field, the mode, the text and the case.

        Parameters:
            choices: The field, the mode, the text and maybe ``case``.

        Returns:
            The choices.

        Raises:
            ConditionInputMissing: There is no text.
            ConditionInputUnknown: The field, the mode or the last choice is not known.
            TextPatternInvalid: The text is too long, or the regex is wrong or may be slow.
        """
        if len(choices) < 3 or not choices[2].strip():
            raise ConditionInputMissing("text: text")
        if choices[0] not in FIELDS or choices[1] not in MODES:
            raise ConditionInputUnknown(f"text: {choices[0]}, {choices[1]}")
        if choices[3:] not in ((), (CASE,)):
            raise ConditionInputUnknown(f"text: {choices[3]}")
        return choices[0], choices[1], check(choices[1], choices[2].strip()), *choices[3:]

    @classmethod
    def parse(cls, form: QueryDict) -> tuple[str, ...]:
        """The choices of a form.

        Parameters:
            form: ``text_field``, ``text_mode``, ``text_value`` and ``text_case`` (``on``).

        Returns:
            The choices.
        """
        case = (CASE,) if form.get("text_case") == "on" else ()
        return cls.check(
            (
                form.get("text_field", "title"),
                form.get("text_mode", "contains"),
                form.get("text_value", ""),
                *case,
            )
        )

    @classmethod
    def applies(
        cls, issue: Issue, choices: tuple[str, ...], scope: Scope | None = None
    ) -> bool | None:
        """Whether the text of the pull request matches.

        Parameters:
            issue: The pull request.
            choices: The field, the mode, the text and maybe ``case``.
            scope: Not used: the condition is of the pull request itself.

        Returns:
            True or False; None for an issue.
        """
        return TextMatches.check(issue, values(choices))

    @classmethod
    def cell(cls, issue: Issue, choices: tuple[str, ...], scope: Scope | None = None) -> list[dict]:
        """Nothing besides whether it matches: the title is in the row already.

        Parameters:
            issue: The pull request.
            choices: The field, the mode, the text and maybe ``case``.
            scope: Not used.

        Returns:
            No texts.
        """
        return []

    @classmethod
    def sentence(cls, choices: tuple[str, ...], negative: bool = False) -> str:
        """Such as ``its title starts with “fix”``.

        Parameters:
            choices: The field, the mode, the text and maybe ``case``.
            negative: The pull requests that it does not apply to.

        Returns:
            The part of the sentence.
        """
        found = {
            "field": gettext(FIELDS[choices[0]]),
            "mode": gettext(MODES[choices[1]]),
            "text": choices[2],
        }
        text = (
            gettext("its %(field)s does not match: %(mode)s “%(text)s”")
            if negative
            else gettext("its %(field)s %(mode)s “%(text)s”")
        ) % found
        if CASE in choices[3:]:
            text += gettext(", case sensitive")
        return text

    @classmethod
    def head(cls, choices: tuple[str, ...]) -> list[dict]:
        """Such as ``title starts with “fix”``.

        Parameters:
            choices: The field, the mode, the text and maybe ``case``.

        Returns:
            One part.
        """
        field, mode = gettext(FIELDS[choices[0]]), gettext(MODES[choices[1]])
        return [{"text": f"{field} {mode} “{choices[2]}”", "kind": "text"}]

    @classmethod
    def summary(cls, choices: tuple[str, ...]) -> str:
        """Such as ``Text: title starts with “fix”``.

        Parameters:
            choices: The field, the mode, the text and maybe ``case``.

        Returns:
            The header.
        """
        return gettext("Text: %(head)s") % {"head": cls.head(choices)[0]["text"]}
