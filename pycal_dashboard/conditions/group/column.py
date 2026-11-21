"""A column of conditions in the table of pull requests: a group, its choices and a filter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import unquote

from pycal_dashboard.conditions.group.author import AuthorGroup
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
        TextGroup,
        DashboardGroup,
    )
}
# which pull requests the column shows: all, those it applies to, those it does not apply to
# and skip: a condition of Skip if, which skips the step and hides the pull requests from the
# filter that it applies to; skip_off: one of Skip if that is switched off. So each condition of
# a filter has its type (a quality check, or Skip if) and whether it is active.
FILTERS = ("all", "applies", "not", "skip", "skip_off")


@dataclass(frozen=True)
class Column:
    """A column of conditions, kept in the address of the table as ``col``.

    The value is ``<group>~<filter>~<choice>~...``, with ``%`` and ``~`` of a part escaped,
    such as ``branch~all~outdated~conflict`` or ``labels~applies~present~needs review``.

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
        # only % and the separator ~ are escaped: the address escapes the rest once
        return "~".join(part.replace("%", "%25").replace("~", "%7E") for part in parts)

    def applies(self, issue: Issue, scope: Scope | None = None) -> bool | None:
        """Whether the condition of the column applies to a pull request.

        Parameters:
            issue: The pull request.
            scope: The repositories of the project, for the states of its author; its
                repository when None.

        Returns:
            True or False; None while its data is not complete.
        """
        return self.group.applies(issue, self.choices, scope)

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
        return self.group.evidence(issue, self.choices, scope, project)

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
            return Column(self.group, self.choices, "skip" if on else "skip_off")
        if not on:
            return Column(self.group, self.choices, "all")
        return Column(self.group, self.choices, self.filter if self.checks else "applies")

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

    @property
    def summary(self) -> str:
        """The header of the column in words, for its title and screen readers."""
        return self.group.summary(self.choices)

    @property
    def sentence(self) -> str:
        """The condition as it filters, as a part of a sentence, such as ``it is open``."""
        return self.group.sentence(self.choices, negative=self.filter == "not")

    @property
    def head(self) -> list[dict]:
        """The shortest header of the column, see ``ConditionGroup.head``."""
        return self.group.head(self.choices)

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

    def inverted(self) -> Column | None:
        """The column that shows exactly the pull requests that this one does not show.

        Its group inverts its choices where it can, such as label absent for present or below
        for at least; else its filter is inverted: the pull requests it does not apply to,
        such as *it is not auto-merging*.

        Returns:
            The inverted column; None for a column that does not filter.

        Examples:
            >>> from pycal_dashboard.conditions.group.status import StatusGroup
            >>> Column(StatusGroup, ("auto_merge",), "applies").inverted().encode()
            'status~not~auto_merge'
            >>> Column(StatusGroup, ("open",), "applies").inverted().encode()
            'status~applies~closed~merged'
        """
        choices = self.group.invert(self.choices)
        if choices is not None and self.filter != "all":
            return Column(self.group, choices, self.filter)
        if self.filter in ("all", "skip", "skip_off"):  # Skip if inverts by its choices only
            return None
        return Column(self.group, self.choices, "not" if self.filter == "applies" else "applies")

    def opposite(self) -> Column | None:
        """The opposite of a column that shows only those it does not apply to.

        It shows those that the opposite applies to, when that is the same for sure, such as
        label absent for label present.

        Returns:
            The opposite column; None if there is none for sure, or the column does not show
            only those it does not apply to.

        Examples:
            >>> from pycal_dashboard.conditions.group.labels import LabelsGroup
            >>> Column(LabelsGroup, ("present", "bug"), "not").opposite().encode()
            'labels~applies~absent~bug'
        """
        if self.filter != "not":
            return None
        choices = self.group.opposite(self.choices)
        return Column(self.group, choices, "applies") if choices else None

    def shown(self, result: str) -> bool:
        """Whether the toggle of the check marks (``applies``) or crosses (``not``) is on.

        Parameters:
            result: ``applies`` or ``not``.

        Returns:
            True if the column shows the pull requests with this result.
        """
        return self.filter in ("all", "skip", "skip_off", result)
