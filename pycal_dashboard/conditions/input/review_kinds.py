"""The input of the kinds of reviews that count: approved, changes requested, ..."""

from dataclasses import dataclass, field
from typing import Any

from pycal_dashboard.conditions.input.base import InputSpec
from pycal_dashboard.conditions.review_kinds import ALL, CHOICES, OWN, checked
from pycal_dashboard.errors import ConditionInputMissing, ConditionInputUnknown


@dataclass(frozen=True)
class ReviewKindsInput(InputSpec):
    """The kinds of reviews that count; all of them by default (type ``review-kinds``).

    Of ``approved``, ``changes_requested``, ``commented`` and ``dismissed``, and ``own``: the
    reviews of the author of a pull request on it, which do not count by default. Every
    condition and state that counts reviews has it, with the same name, ``kinds``.
    """

    name: str = "kinds"
    label: str = "Kinds of reviews"
    help: str = (
        "Which reviews count: approved, changes_requested, commented and dismissed; all of them "
        "by default. Dismissed are approvals or requests for changes that were dismissed later. "
        "own: also the reviews of the author of the pull request, which do not count by default."
    )
    required: bool = False
    default: Any = field(default=ALL)
    type: str = "review-kinds"

    def parse(self, value: Any, context: dict | None = None) -> tuple[str, ...]:  # noqa: ANN401
        """The kinds, in their order.

        Parameters:
            value: A list of names, or their text separated by commas, such as
                ``"approved, commented"``.
            context: Not used.

        Returns:
            The kinds.

        Raises:
            ConditionInputUnknown: A name is not a kind of review.
            ConditionInputMissing: No kind is chosen.

        Examples:
            >>> ReviewKindsInput().parse("commented, approved")
            ('approved', 'commented')
        """
        names = value.split(",") if isinstance(value, str) else list(value or ())
        names = [str(name).strip() for name in names if str(name).strip()]
        unknown = [name for name in names if name not in CHOICES]
        if unknown:
            raise ConditionInputUnknown(f"{self.name}: {', '.join(unknown)}")
        if not names:
            raise ConditionInputMissing(f"{self.name}: {', '.join(ALL)}")
        return checked(names)

    def widget(self, context: dict | None = None) -> dict:
        """A switch for each kind.

        Parameters:
            context: Not used.

        Returns:
            The kind ``switches`` and the kinds with their texts.
        """
        return {
            "kind": "switches",
            "choices": [(kind, text) for kind, (_s, text) in CHOICES.items()],
        }

    def describe(self) -> dict:
        """The input with its kinds.

        Returns:
            As ``InputSpec.describe``, with ``choices``.
        """
        return {**super().describe(), "default": list(ALL), "choices": [*ALL, OWN]}
