"""An input of a condition that compares a number: above, below, at most, at least, exactly."""

import operator
from dataclasses import dataclass
from typing import Any

from django.utils.translation import gettext_noop

from pycal_dashboard.conditions.input.base import InputSpec
from pycal_dashboard.errors import ConditionInputUnknown

# each comparison: its sign, its words for a value (a ratio) and for a count (reviews)
COMPARISONS = {
    "above": (">", gettext_noop("above"), gettext_noop("more than")),
    "below": ("<", gettext_noop("below"), gettext_noop("fewer than")),
    "at_most": ("≤", gettext_noop("at most"), gettext_noop("at most")),
    "at_least": ("≥", gettext_noop("at least"), gettext_noop("at least")),
    "exactly": ("=", gettext_noop("exactly"), gettext_noop("exactly")),
}
# the words of a comparison that is not exactly a number, for the opposite of exactly
NOT_EXACTLY = gettext_noop("not exactly")
OPERATORS = {
    "above": operator.gt,
    "below": operator.lt,
    "at_most": operator.le,
    "at_least": operator.ge,
    "exactly": operator.eq,
}
# the comparison that holds exactly when the other does not; exactly has none
INVERSE = {"above": "at_most", "at_most": "above", "below": "at_least", "at_least": "below"}


def compare(value: float, comparison: str, number: float) -> bool:
    """Whether a value compares with a number as a comparison says; the limits count.

    Parameters:
        value: The value, such as how many reviews a pull request has.
        comparison: One of ``COMPARISONS``, such as ``at_least``.
        number: The number to compare with.

    Returns:
        True if it holds.

    Examples:
        >>> compare(2, "at_least", 2), compare(2, "above", 2), compare(float("inf"), "above", 9)
        (True, False, True)
    """
    return OPERATORS[comparison](value, number)


@dataclass(frozen=True)
class ComparisonInput(InputSpec):
    """How a number is compared: ``above``, ``below``, ``at_most``, ``at_least`` or ``exactly``.

    At most and at least include the number itself (type ``comparison``).
    """

    type: str = "comparison"

    def parse(self, value: Any, context: dict | None = None) -> str:
        """The comparison.

        Parameters:
            value: Its name, such as ``at_least``.
            context: Not used.

        Returns:
            The name.

        Raises:
            ConditionInputUnknown: It is none of ``COMPARISONS``.

        Examples:
            >>> ComparisonInput("comparison", "Comparison").parse("below")
            'below'
        """
        if value not in COMPARISONS:
            raise ConditionInputUnknown(f"{self.name}: {value!r}")
        return value

    def widget(self, context: dict | None = None) -> dict:
        """A choice of the comparisons, with their signs.

        Parameters:
            context: Not used.

        Returns:
            The kind and the choices.
        """
        choices = [
            {"value": name, "description": f"{words} {sign}"}
            for name, (sign, words, _count) in COMPARISONS.items()
        ]
        return {"kind": "choice", "attributes": {}, "choices": choices}
