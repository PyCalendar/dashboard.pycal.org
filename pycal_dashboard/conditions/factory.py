"""The factory of the conditions: it makes them, and writes them down and reads them again."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pycal_dashboard.conditions import CONDITIONS
from pycal_dashboard.conditions.condition.any_of import AnyOf
from pycal_dashboard.conditions.condition.negation import Not
from pycal_dashboard.errors import ConditionNotInGroup, UnknownCondition

if TYPE_CHECKING:
    from collections.abc import Iterable

    from pycal_dashboard.conditions.group.base import ConditionGroup


class ConditionFactory:
    """Makes the conditions of their classes, and serializes and deserializes them.

    A condition is made of its class, or of its id, and a creation spec, the inputs by name
    (:meth:`create`); it yields the same spec again (``spec()``). All that writes conditions
    down and reads them again is here, outside of the conditions: as a spec with an id
    (:meth:`dump`, :meth:`load`), and as the choices of a group, such as those of a column of
    the table of pull requests (:meth:`decode`, :meth:`encode`). A group says which specs its
    choices mean (``ConditionGroup.specs``) and which choices write specs
    (``ConditionGroup.choices_of``); the factory does the rest, the same for every group.

    So the NOT of a condition and a condition that is its NOT are the same in the factory:
    ``label_absent`` is the NOT of ``label_exists``, and the choices ``absent`` and the NOT of
    ``present`` of a column of labels read as the same condition, which is written as
    ``absent``. A NOT that its group has no choices for is written as the NOT of the
    condition.

    The factory is cheap to make: it is made where it is needed.

    Attributes:
        conditions: The classes of the conditions, and their NOTs, by id.

    Examples:
        >>> from pycal_dashboard.conditions.condition.label_exists import LabelExists
        >>> factory = ConditionFactory()
        >>> bug = factory.create(LabelExists, {"label": "bug"})
        >>> factory.create("label_absent", {"label": "bug"}) == bug.negate()
        True
        >>> factory.dump(bug.negate())
        {'id': 'label_absent', 'label': 'bug'}
        >>> factory.load({"id": "label_absent", "label": "bug"}) == bug.negate()
        True
    """

    def __init__(self, conditions: dict[str, Any] | None = None):
        """Make the factory.

        Parameters:
            conditions: The classes of the conditions, and their NOTs, by id;
                ``CONDITIONS`` by default.
        """
        self.conditions = dict(CONDITIONS if conditions is None else conditions)

    def find(self, id: str) -> Any:  # noqa: ANN401 - a class of conditions or its NOT
        """The class of the conditions with an id, or its NOT.

        Parameters:
            id: Such as ``label_exists``, or ``label_absent``, its NOT.

        Returns:
            The class, or the NOT of a class, which makes conditions as a class does.

        Raises:
            UnknownCondition: There is no condition with this id.
        """
        try:
            return self.conditions[id]
        except KeyError:
            raise UnknownCondition(id) from None

    def create(
        self,
        kind: Any,  # noqa: ANN401 - a class of conditions, its NOT or its id
        spec: dict | None = None,
        context: dict | None = None,
    ) -> Any:  # noqa: ANN401 - a condition or its NOT
        """The condition of a class, or of its id, and a creation spec.

        Parameters:
            kind: The class, such as ``LabelExists``; its NOT, such as
                ``LabelExists.negate()``; or the id of either, such as ``label_absent``.
            spec: The inputs by name, such as ``{"label": "bug"}``.
            context: What the inputs may need, such as the ``repository``.

        Returns:
            The condition.

        Raises:
            UnknownCondition: There is no condition with the id.
            ConditionError: The spec is wrong: a subclass of it says how.
        """
        kind = self.find(kind) if isinstance(kind, str) else kind
        return kind(spec, context)

    def load(self, spec: dict, context: dict | None = None) -> Any:  # noqa: ANN401
        """The condition of a spec with its id, as :meth:`dump` writes it.

        Parameters:
            spec: ``id`` and the inputs, such as ``{"id": "label_absent", "label": "bug"}``.
            context: What the inputs may need, such as the ``repository``.

        Returns:
            The condition.

        Raises:
            UnknownCondition: The id is missing or not known.
            ConditionError: An input is wrong: a subclass of it says how.
        """
        inputs = dict(spec)
        return self.create(str(inputs.pop("id", "")), inputs, context)

    @staticmethod
    def dump(condition: Any) -> dict:  # noqa: ANN401 - a condition or its NOT
        """The spec of a condition with its id, which :meth:`load` makes again.

        Parameters:
            condition: The condition, such as ``LabelExists({"label": "bug"}).negate()``.

        Returns:
            ``id`` and the inputs, such as ``{"id": "label_absent", "label": "bug"}``.
        """
        return {"id": condition.id, **condition.spec()}

    @staticmethod
    def any_of(conditions: Iterable[Any]) -> Any:  # noqa: ANN401 - a condition or an OR
        """Conditions joined by OR; one condition alone is itself.

        Parameters:
            conditions: The conditions.

        Returns:
            The condition, or the OR of them (:class:`~.condition.any_of.AnyOf`).
        """
        conditions = tuple(conditions)
        return conditions[0] if len(conditions) == 1 else AnyOf(conditions)

    @staticmethod
    def parts(condition: Any) -> tuple:  # noqa: ANN401 - a condition or an OR
        """The conditions joined by OR in a condition; the condition alone else.

        Parameters:
            condition: The condition.

        Returns:
            The conditions.
        """
        return condition.conditions if isinstance(condition, AnyOf) else (condition,)

    def decode(
        self, group: type[ConditionGroup], choices: tuple[str, ...], negated: bool = False
    ) -> Any:  # noqa: ANN401 - a condition
        """The condition of the choices of a group, such as those of a column of the table.

        Parameters:
            group: The group, such as that of labels.
            choices: Its choices, checked (``ConditionGroup.check``), such as
                ``("present", "bug")``.
            negated: Whether it is the NOT of the condition of the choices.

        Returns:
            The condition of the spec of the choices, or the OR of the specs; its NOT when
            negated.

        Examples:
            >>> from pycal_dashboard.conditions.group.labels import LabelsGroup
            >>> factory = ConditionFactory()
            >>> absent = factory.decode(LabelsGroup, ("absent", "bug"))
            >>> absent == factory.decode(LabelsGroup, ("present", "bug"), negated=True)
            True
        """
        condition = self.any_of(self.load(spec) for spec in group.specs(choices))
        return condition.negate() if negated else condition

    def encode(self, group: type[ConditionGroup], condition: Any) -> tuple[tuple[str, ...], bool]:  # noqa: ANN401
        """The choices of a group that write a condition, and whether they are negated.

        A NOT that the group has no choices for is written as the choices of its condition,
        negated: ``not~`` in the address of the table.

        Parameters:
            group: The group.
            condition: The condition, such as ``LabelExists({"label": "bug"}).negate()``.

        Returns:
            The choices, such as ``("absent", "bug")``, and whether they are negated.

        Raises:
            ConditionNotInGroup: The group has no choices for the condition, nor for the
                condition of its NOT.

        Examples:
            >>> from pycal_dashboard.conditions.condition.open import Open
            >>> from pycal_dashboard.conditions.group.labels import LabelsGroup
            >>> from pycal_dashboard.conditions.group.status import StatusGroup
            >>> factory = ConditionFactory()
            >>> factory.encode(LabelsGroup, factory.decode(LabelsGroup, ("present", "bug"), True))
            (('absent', 'bug'), False)
            >>> factory.encode(StatusGroup, Open().negate())
            (('open',), True)
        """
        choices = group.choices_of([self.dump(part) for part in self.parts(condition)])
        if choices is not None:
            return choices, False
        if isinstance(condition, Not):
            choices = group.choices_of([self.dump(part) for part in self.parts(condition.negate())])
            if choices is not None:
                return choices, True
        raise ConditionNotInGroup(f"{group.id}: {condition.id}")
