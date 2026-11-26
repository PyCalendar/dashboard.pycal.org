"""A column of conditions in the table of pull requests: a group, its choices and a filter."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from functools import cached_property
from typing import TYPE_CHECKING, Any
from urllib.parse import unquote

from django.utils.translation import gettext

from pycal_dashboard.conditions.factory import ConditionFactory
from pycal_dashboard.conditions.group.author import AuthorGroup
from pycal_dashboard.conditions.group.author_type import AuthorTypeGroup
from pycal_dashboard.conditions.group.branch import BranchGroup
from pycal_dashboard.conditions.group.ci import CiGroup
from pycal_dashboard.conditions.group.dashboard import DashboardGroup
from pycal_dashboard.conditions.group.labels import LabelsGroup
from pycal_dashboard.conditions.group.reviews import ReviewsGroup
from pycal_dashboard.conditions.group.status import StatusGroup
from pycal_dashboard.conditions.group.text import TextGroup
from pycal_dashboard.conditions.review_kinds import ALL, checked
from pycal_dashboard.errors import ConditionInputUnknown, UnknownCondition

if TYPE_CHECKING:
    from django.http import QueryDict

    from pycal_dashboard.conditions.evidence import Evidence
    from pycal_dashboard.conditions.group.base import ConditionGroup
    from pycal_dashboard.conditions.state.scope import Scope
    from pycal_dashboard.models import Issue, Project

# the groups in the order of the menu
GROUPS: dict[str, type[ConditionGroup]] = {
    group.id: group
    for group in (
        LabelsGroup,
        BranchGroup,
        CiGroup,
        StatusGroup,
        ReviewsGroup,
        AuthorGroup,
        AuthorTypeGroup,
        TextGroup,
        DashboardGroup,
    )
}
# which pull requests the column shows: all, those it applies to, those it does not apply to
# and skip: a condition of Skip if, which skips the step and hides the pull requests from the
# filter that it applies to; skip_off: one of Skip if that is switched off. So each condition of
# a filter has its type (a quality check, or Skip if) and whether it is active.
FILTERS = ("all", "applies", "not", "skip", "skip_off")
# the first part of a column joined with others by AND: ``and<number>~``, such as ``and1~``
JOINED = re.compile(r"and([1-9][0-9]{0,2})")


@dataclass(frozen=True)
class Column:
    """A column of conditions, kept in the address of the table as ``col``.

    The value is ``<group>~<filter>~<choice>~...``, with ``%`` and ``~`` of a part escaped,
    such as ``branch~all~outdated~conflict`` or ``labels~applies~present~needs review``.
    A column joined with others by AND starts with the number of the AND, such as
    ``and1~labels~applies~present~bug`` (see
    :class:`~pycal_dashboard.conditions.group.conjunction.Conjunction`), and the NOT of its
    condition with ``not``, such as ``not~text~skip~title~contains~WIP``: every condition can
    be inverted (:meth:`inverted`), its NOT holds when it does not
    (:class:`~pycal_dashboard.conditions.condition.negation.Not`).

    Attributes:
        group: The group of conditions.
        choices: Its choices.
        filter: ``all``, ``applies`` or ``not``.
        joined: The number of the AND that it is a part of in its filter; 0 for none.
        negated: Whether it is the NOT of the condition of its group and choices.
    """

    group: type[ConditionGroup]
    choices: tuple[str, ...]
    filter: str = "all"
    joined: int = 0
    negated: bool = False

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
        joined = JOINED.fullmatch(parts[0])
        if joined:
            parts = parts[1:] or [""]
        negated = parts[0] == "not"
        if negated:
            parts = parts[1:] or [""]
        group = GROUPS.get(parts[0])
        if group is None:
            raise UnknownCondition(parts[0])
        filter = parts[1] if len(parts) > 1 else "all"
        if filter not in FILTERS:
            raise ConditionInputUnknown(f"filter: {filter}")
        number = int(joined[1]) if joined else 0
        column = cls(group, group.check(tuple(parts[2:])), filter, number, negated)
        return column.writing(column.condition)  # such as absent for the NOT of present

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

    @cached_property
    def condition(self) -> Any:  # noqa: ANN401 - a condition, an OR or a NOT
        """The condition that the column checks, made by the factory of its group and choices.

        It is the NOT of that condition when the column is negated.
        """
        return ConditionFactory().decode(self.group, self.choices, self.negated)

    def writing(self, condition: Any) -> Column:  # noqa: ANN401 - a condition, an OR or a NOT
        """The column with another condition of its group, written by the factory.

        Parameters:
            condition: The condition, such as the NOT of that of the column.

        Returns:
            The column with the choices that write the condition, negated if they are those of
            its NOT; its filter and AND stay.

        Raises:
            ConditionNotInGroup: The group has no choices for the condition.
        """
        choices, negated = ConditionFactory().encode(self.group, condition)
        return replace(self, choices=choices, negated=negated)

    def encode(self) -> str:
        """The value of the column in the address.

        Returns:
            Such as ``branch~all~outdated``, ``and1~branch~all~outdated`` when it is joined, or
            ``not~branch~all~outdated`` when it is negated.
        """
        parts = (f"and{self.joined}",) if self.joined else ()
        parts += ("not",) if self.negated else ()
        parts += (self.group.id, self.filter, *self.choices)
        # only % and the separator ~ are escaped: the address escapes the rest once
        return "~".join(part.replace("%", "%25").replace("~", "%7E") for part in parts)

    def applies(self, issue: Issue, scope: Scope | None = None) -> bool | None:
        """Whether the condition of the column applies to a pull request.

        Parameters:
            issue: The pull request.
            scope: The repositories of the project, for the states of its author; its
                repository when None.

        Returns:
            True or False; None while its data is not complete. The NOT of the condition, when
            the column is negated.
        """
        return self.condition.check(issue, scope)

    def evidence(
        self, issue: Issue, scope: Scope | None = None, project: Project | None = None
    ) -> list[Evidence]:
        """The least that shows why the condition of the column holds for a pull request, or not.

        Parameters:
            issue: The pull request.
            scope: The repositories of the project, for the states of its author.
            project: The project, for its pages.

        Returns:
            The links, such as to the checks on GitHub.
        """
        return self.condition.evidence(issue, scope, project)

    @property
    def kinds(self) -> tuple[str, ...]:
        """The kinds of reviews that the column counts: its choice, else all of them."""
        start = {"reviews": 2, "author": 3}.get(self.group.id)
        return checked(self.choices[start:]) if start is not None else ALL

    @property
    def checks(self) -> bool:
        """Whether the column is a quality check: a task of a step, which the filter filters by."""
        return self.filter in ("applies", "not")

    @property
    def skips(self) -> bool:
        """Whether the column is an active condition of Skip if: it applies, the step is skipped."""
        return self.filter == "skip"

    @property
    def kind(self) -> str:
        """The type of the condition in a filter: ``skip`` for Skip if, else ``check``."""
        return "skip" if self.filter in ("skip", "skip_off") else "check"

    @property
    def active(self) -> bool:
        """Whether the condition is switched on in its filter, as a quality check or Skip if."""
        return self.filter not in ("all", "skip_off")

    def switched(self, on: bool) -> Column:
        """The column switched on or off, keeping its type.

        Parameters:
            on: Whether it is on.

        Returns:
            The column: a quality check shows what it applies to when on and all when off;
            Skip if is ``skip`` or ``skip_off``.

        Examples:
            >>> from pycal_dashboard.conditions.group.status import StatusGroup
            >>> Column(StatusGroup, ("open",), "skip").switched(False).filter
            'skip_off'
            >>> Column(StatusGroup, ("open",), "not").switched(True).filter
            'not'
        """
        if self.kind == "skip":
            return replace(self, filter="skip" if on else "skip_off")
        if not on:
            return replace(self, filter="all")
        return replace(self, filter=self.filter if self.checks else "applies")

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
        return True  # all, and skip, which hides the pull requests it applies to instead

    def holds(self, result: bool | None) -> bool | None:
        """Whether the condition holds as the column filters, for a result.

        A column that shows the pull requests it does not apply to holds when it does not
        apply, such as *it is not open*; the others when it applies.

        Parameters:
            result: Whether the condition applies; None while not known.

        Returns:
            True, False, or None while not known.

        Examples:
            >>> from pycal_dashboard.conditions.group.status import StatusGroup
            >>> Column(StatusGroup, ("open",), "not").holds(False)
            True
        """
        if result is None or self.filter != "not":
            return result
        return not result

    @property
    def summary(self) -> str:
        """The header of the column in words, for its title and screen readers."""
        summary = self.group.summary(self.choices)
        return gettext("NOT %(condition)s") % {"condition": summary} if self.negated else summary

    @property
    def sentence(self) -> str:
        """The condition as it filters, as a part of a sentence, such as ``it is open``.

        A negated column that shows the pull requests it does not apply to reads as the
        condition: two NOTs.
        """
        return self.group.sentence(self.choices, negative=(self.filter == "not") != self.negated)

    @property
    def head(self) -> list[dict]:
        """The shortest header of the column, see ``ConditionGroup.head``; NOT first, if so."""
        head = self.group.head(self.choices)
        return [{"text": gettext("NOT"), "kind": "not"}, *head] if self.negated else head

    def toggled(self, result: str) -> str:
        """The filter after a click on the toggle of the check marks or the crosses.

        Both are on to show all pull requests. Switching off the last one that is on switches
        the other one on, so that the column always shows some.

        Parameters:
            result: ``applies`` for the check marks, ``not`` for the crosses.

        Returns:
            The filter: ``all``, ``applies`` or ``not``.

        Examples:
            >>> from pycal_dashboard.conditions.group.status import StatusGroup
            >>> column = Column(StatusGroup, ("open",))
            >>> column.toggled("applies"), column.toggled("not")
            ('not', 'applies')
            >>> Column(StatusGroup, ("open",), "applies").toggled("applies")
            'not'
            >>> Column(StatusGroup, ("open",), "not").toggled("applies")
            'all'
        """
        other = "not" if result == "applies" else "applies"
        if self.filter in ("all", "skip", "skip_off"):
            return other  # switch this one off
        if self.filter == result:
            return other  # the last one that was on: the other one instead
        return "all"  # switch this one on too

    def inverted(self) -> Column:
        """The column of the opposite condition: every condition can be inverted.

        It has the NOT of its condition when its group writes that without a NOT (the factory):
        label absent for present, below for at least, or the condition of a negated column.
        Else the opposite choices of its group, such as closed and merged for open; else a
        quality check that is on inverts its filter: the pull requests it does not apply to,
        such as *it is not auto-merging*; else, such as when it is off or of Skip if, it is the
        NOT of the condition (``negated``). Inverting it again gives it back.

        Returns:
            The inverted column.

        Examples:
            >>> from pycal_dashboard.conditions.group.status import StatusGroup
            >>> from pycal_dashboard.conditions.group.text import TextGroup
            >>> Column(StatusGroup, ("auto_merge",), "applies").inverted().encode()
            'status~not~auto_merge'
            >>> Column(StatusGroup, ("open",), "applies").inverted().encode()
            'status~applies~closed~merged'
            >>> wip = Column(TextGroup, ("title", "contains", "WIP"), "skip")
            >>> wip.inverted().encode(), wip.inverted().inverted() == wip
            ('not~text~skip~title~contains~WIP', True)
        """
        negation = self.writing(self.condition.negate())
        if not negation.negated:
            return negation
        choices = self.group.opposite(self.choices)
        if choices is not None:
            return replace(self, choices=choices)
        if self.filter in ("applies", "not"):
            return replace(self, filter="not" if self.filter == "applies" else "applies")
        return negation

    def opposite(self) -> Column | None:
        """The opposite of a column that shows only those it does not apply to.

        It shows those that the opposite applies to, when that is the same for sure: the NOT of
        its condition when its group writes that without a NOT, such as label absent for label
        present, or the opposite choices of its group, such as closed and merged for open.

        Returns:
            The opposite column; None if there is none for sure, or the column does not show
            only those it does not apply to.

        Examples:
            >>> from pycal_dashboard.conditions.group.labels import LabelsGroup
            >>> Column(LabelsGroup, ("present", "bug"), "not").opposite().encode()
            'labels~applies~absent~bug'
        """
        if self.filter != "not" or self.negated:
            return None
        negation = self.writing(self.condition.negate())
        if not negation.negated:
            return replace(negation, filter="applies")
        choices = self.group.opposite(self.choices)
        return replace(self, choices=choices, filter="applies") if choices else None

    def shown(self, result: str) -> bool:
        """Whether the toggle of the check marks (``applies``) or crosses (``not``) is on.

        Parameters:
            result: ``applies`` or ``not``.

        Returns:
            True if the column shows the pull requests with this result.
        """
        return self.filter in ("all", "skip", "skip_off", result)
