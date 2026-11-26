"""The method ``negate()`` of conditions: on their classes and on the conditions made of them."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pycal_dashboard.conditions.condition.negation import Not


class NegateMethod:
    """``negate()`` of a condition: its NOT, of a class or of a condition made of it.

    ``LabelExists.negate()`` is the NOT of the class, ``label_absent``, from which a condition is
    made as from a class; ``LabelExists({"label": "bug"}).negate()`` is the NOT of that condition,
    with the same values. The NOT of a NOT is the condition again (:meth:`Not.negate
    <pycal_dashboard.conditions.condition.negation.Not.negate>`).

    Examples:
        >>> from pycal_dashboard.conditions.condition.label_exists import LabelExists
        >>> LabelExists.negate().id, LabelExists.negate().negate() is LabelExists
        ('label_absent', True)
        >>> bug = LabelExists({"label": "bug"})
        >>> bug.negate() == LabelExists.negate()({"label": "bug"}), bug.negate().negate() == bug
        (True, True)
    """

    def __get__(self, instance: object, owner: type) -> Callable[[], Not]:
        """The method, bound to the condition or to its class.

        Parameters:
            instance: The condition; None on the class.
            owner: The class of the condition.

        Returns:
            ``negate()``, which gives the NOT.
        """
        wrapped: Any = owner if instance is None else instance

        def negate() -> Not:
            """The NOT of the condition: it holds exactly when the condition does not.

            Returns:
                The condition wrapped in its NOT.
            """
            return Not(wrapped)

        return negate
