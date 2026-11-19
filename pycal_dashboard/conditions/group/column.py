"""A column of conditions in the table of pull requests: a group, its choices and a filter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import quote, unquote

from pycal_dashboard.conditions.group.branch import BranchGroup
from pycal_dashboard.conditions.group.ci import CiGroup
from pycal_dashboard.conditions.group.labels import LabelsGroup
from pycal_dashboard.conditions.group.status import StatusGroup
from pycal_dashboard.errors import ConditionInputUnknown, UnknownCondition

if TYPE_CHECKING:
    from django.http import QueryDict

    from pycal_dashboard.conditions.group.base import ConditionGroup
    from pycal_dashboard.models import Issue

# the groups in the order of the menu
GROUPS: dict[str, type[ConditionGroup]] = {
    group.id: group for group in (LabelsGroup, BranchGroup, CiGroup, StatusGroup)
}
# which pull requests the column shows: all, those it applies to, those it does not apply to
FILTERS = ("all", "applies", "not")


@dataclass(frozen=True)
class Column:
    """A column of conditions, kept in the address of the table as ``col``.

    The value is ``<group>~<filter>~<choice>~...``, each part quoted, such as
    ``branch~all~outdated~conflict`` or ``labels~applies~present~needs%20review``.

    Attributes:
        group: The group of conditions.
        choices: Its choices.
        filter: ``all``, ``applies`` or ``not``.
    """

    group: type[ConditionGroup]
    choices: tuple[str, ...]
    filter: str = "all"

    @classmethod
    def decode(cls, value: str) -> Column:
        """The column of a value of the address.

        Parameters:
            value: Such as ``branch~all~outdated``.

        Returns:
            The column.

        Raises:
            UnknownCondition: The group is not known.
            ConditionInputUnknown: The filter is not known.
            ConditionError: A choice is wrong.
        """
        parts = [unquote(part) for part in value.split("~")]
        group = GROUPS.get(parts[0])
        if group is None:
            raise UnknownCondition(parts[0])
        filter = parts[1] if len(parts) > 1 else "all"
        if filter not in FILTERS:
            raise ConditionInputUnknown(f"filter: {filter}")
        return cls(group, group.check(tuple(parts[2:])), filter)

    @classmethod
    def of_form(cls, form: QueryDict) -> Column:
        """The column that the menu of a column describes.

        Parameters:
            form: ``group``, ``filter`` and the fields of the group.

        Returns:
            The column.

        Raises:
            UnknownCondition: The group is not known.
            ConditionInputUnknown: The filter is not known.
            ConditionError: A choice is wrong.
        """
        group = GROUPS.get(form.get("group", ""))
        if group is None:
            raise UnknownCondition(form.get("group", ""))
        filter = form.get("filter", "all")
        if filter not in FILTERS:
            raise ConditionInputUnknown(f"filter: {filter}")
        return cls(group, group.parse(form), filter)

    def encode(self) -> str:
        """The value of the column in the address.

        Returns:
            Such as ``branch~all~outdated``.
        """
        parts = (self.group.id, self.filter, *self.choices)
        return "~".join(quote(part, safe="").replace("~", "%7E") for part in parts)

    def applies(self, issue: Issue) -> bool | None:
        """Whether the condition of the column applies to a pull request.

        Parameters:
            issue: The pull request.

        Returns:
            True or False; None while its data is not complete.
        """
        return self.group.applies(issue, self.choices)

    def shows(self, result: bool | None) -> bool:
        """Whether the filter of the column shows a pull request with this result.

        Parameters:
            result: Whether the condition applies to it.

        Returns:
            True if the pull request is shown.
        """
        if self.filter == "applies":
            return result is True
        if self.filter == "not":
            return result is False
        return True

    @property
    def summary(self) -> str:
        """The header of the column."""
        return self.group.summary(self.choices)
