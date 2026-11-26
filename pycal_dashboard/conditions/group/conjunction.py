"""Conditions of a filter joined by AND or by OR: one condition of a step, of several columns."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from django.utils.translation import gettext

from pycal_dashboard.conditions.group.column import Column

if TYPE_CHECKING:
    from collections.abc import Iterable

    from pycal_dashboard.conditions.evidence import Evidence
    from pycal_dashboard.conditions.state.scope import Scope
    from pycal_dashboard.models import Issue, Project


@dataclass(frozen=True)
class Conjunction:
    """Columns of a filter joined by AND, or by OR, which a step uses as one condition.

    The columns of an AND have the same number (``Column.joined``) and the same type: quality checks
    or Skip if. Joined by OR (``Column.operator``, the same for all of them, that of the first), it
    holds when one of its conditions in force holds, as it filters, such as *PR is a draft or PR has
    the label WIP*; a radio choice of the page of saving a filter turns an AND into an OR and back.
    As a quality check, the AND keeps a pull request in the step while all of its conditions in
    force hold, as each of them filters, such as *PR is open and PR has the label bug*; as a
    condition of Skip if, it skips the step when all of them apply. A column that is off is no part
    of it. It is used like a column where the filter and the steps use their conditions: its value
    (:meth:`encode`) is that of its columns without their numbers, joined with ``&``, or with ``|``
    for an OR, which keeps the summary and the description of the step and the skips.

    Attributes:
        columns: The columns, in their order in the filter.
    """

    columns: tuple[Column, ...]

    @classmethod
    def of(cls, columns: Iterable[Column]) -> list[Column | Conjunction]:
        """The conditions of a filter: each column alone, or the columns of an AND together.

        Parameters:
            columns: The columns of the filter, in their order.

        Returns:
            The conditions in the order of their first column; an AND of one column is that
            column.

        Examples:
            >>> from pycal_dashboard.conditions.group.status import StatusGroup
            >>> found = Conjunction.of(Column.decode(value) for value in
            ...     ["and1~status~applies~open", "status~applies~draft", "and1~ci~applies~failing"])
            >>> [item.encode() for item in found]
            ['status~applies~open&ci~applies~failing', 'status~applies~draft']
        """
        columns = list(columns)
        found: list[Column | Conjunction] = []
        for numbers in cls.indices(columns):
            if len(numbers) == 1:
                found.append(replace(columns[numbers[0]], joined=0, operator="and"))
            else:
                found.append(cls(tuple(columns[number] for number in numbers)))
        return found

    @staticmethod
    def indices(columns: list[Column]) -> list[list[int]]:
        """The places of the columns of each condition of a filter, see :meth:`of`.

        Parameters:
            columns: The columns of the filter, in their order.

        Returns:
            For each condition, in the order of its first column, the places of its columns.

        Examples:
            >>> values = ["and1~status~applies~open", "status~applies~draft",
            ...     "and1~ci~applies~failing"]
            >>> Conjunction.indices([Column.decode(value) for value in values])
            [[0, 2], [1]]
        """
        groups: dict[tuple[str, int], list[int]] = {}
        found: list[list[int]] = []
        for index, column in enumerate(columns):
            if not column.joined:
                found.append([index])
                continue
            key = (column.kind, column.joined)
            if key not in groups:
                groups[key] = []
                found.append(groups[key])
            groups[key].append(index)
        return found

    @classmethod
    def of_values(cls, values: Iterable[str]) -> list[Column | Conjunction]:
        """The conditions of the values of the columns of a filter, as it keeps them.

        Parameters:
            values: Such as ``["and1~status~applies~open", "and1~ci~applies~failing"]``.

        Returns:
            The conditions, see :meth:`of`.
        """
        return cls.of(Column.decode(value) for value in values)

    @staticmethod
    def normalized(columns: Iterable[Column]) -> list[Column]:
        """The columns with the numbers of their ANDs counted from 1 in their order.

        A column that is alone in its AND, or whose AND has columns of the other type, of which
        it is the only one, joins no AND.

        Parameters:
            columns: The columns, in their order.

        Returns:
            The same columns, with the numbers of their ANDs.

        Examples:
            >>> from pycal_dashboard.conditions.group.status import StatusGroup
            >>> found = Conjunction.normalized(Column.decode(value) for value in
            ...     ["and5~status~applies~open", "and2~status~applies~draft",
            ...      "and5~ci~applies~failing"])
            >>> [column.encode() for column in found]
            ['and1~status~applies~open', 'status~applies~draft', 'and1~ci~applies~failing']
        """
        columns = list(columns)
        sizes: dict[tuple[str, int], int] = {}
        for column in columns:
            if column.joined:
                key = (column.kind, column.joined)
                sizes[key] = sizes.get(key, 0) + 1
        numbers: dict[tuple[str, int], int] = {}
        operators: dict[tuple[str, int], str] = {}  # that of the first column of each
        found = []
        for column in columns:
            key = (column.kind, column.joined)
            if not column.joined or sizes[key] < 2:
                found.append(replace(column, joined=0, operator="and"))
                continue
            numbers.setdefault(key, len(numbers) + 1)
            operator = operators.setdefault(key, column.operator)
            found.append(replace(column, joined=numbers[key], operator=operator))
        return found

    @property
    def joined(self) -> int:
        """The number of the AND in its filter."""
        return self.columns[0].joined

    @property
    def kind(self) -> str:
        """The type of the condition in a filter: ``skip`` for Skip if, else ``check``."""
        return self.columns[0].kind

    @property
    def operator(self) -> str:
        """``and`` or ``or``: how its conditions are joined."""
        return self.columns[0].operator

    @property
    def in_force(self) -> tuple[Column, ...]:
        """Its columns that are switched on: the conditions that it joins."""
        return tuple(column for column in self.columns if column.active)

    @property
    def active(self) -> bool:
        """Whether a condition of it is switched on, so that it is a part of its filter."""
        return bool(self.in_force)

    @property
    def checks(self) -> bool:
        """Whether it is a quality check in force: a task of a step."""
        return self.kind == "check" and self.active

    @property
    def skips(self) -> bool:
        """Whether it is a condition of Skip if in force: it applies, the step is skipped."""
        return self.kind == "skip" and self.active

    @property
    def filter(self) -> str:
        """As the filter of a column: ``applies`` as a quality check, else ``skip``."""
        if self.kind == "skip":
            return "skip" if self.active else "skip_off"
        return "applies" if self.active else "all"

    def encode(self) -> str:
        """The value of the condition in a step: those of its columns, joined with ``&``.

        Returns:
            Such as ``status~applies~open&ci~applies~failing``; ``|`` between them for an OR.
        """
        separator = "|" if self.operator == "or" else "&"
        return separator.join(
            replace(column, joined=0, operator="and").encode() for column in self.columns
        )

    @staticmethod
    def combined(results: Iterable[bool | None]) -> bool | None:
        """The AND of the results of conditions, of which some may not be known.

        Parameters:
            results: Whether each condition holds; None while not known.

        Returns:
            False when one does not hold; else None when one is not known; else True.

        Examples:
            >>> Conjunction.combined([True, None, False]), Conjunction.combined([True, None])
            (False, None)
        """
        found: bool | None = True
        for result in results:
            if result is False:
                return False
            if result is None:
                found = None
        return found

    @staticmethod
    def either(results: Iterable[bool | None]) -> bool | None:
        """The OR of the results of conditions, of which some may not be known.

        Parameters:
            results: Whether each condition holds; None while not known.

        Returns:
            True when one holds; else None when one is not known; else False.

        Examples:
            >>> Conjunction.either([False, None, True]), Conjunction.either([False, None])
            (True, None)
        """
        found: bool | None = False
        for result in results:
            if result is True:
                return True
            if result is None:
                found = None
        return found

    def combine(self, results: Iterable[bool | None]) -> bool | None:
        """The results of its conditions joined by its operator: AND, or OR.

        Parameters:
            results: Whether each condition holds; None while not known.

        Returns:
            True, False, or None while not known.
        """
        return self.either(results) if self.operator == "or" else self.combined(results)

    def results(self, found: list[dict[int, bool | None]]) -> dict[int, bool | None]:
        """Whether the AND holds for each pull request, from the results of its columns.

        Parameters:
            found: The results of each column in force (``in_force``), by the id of the pull
                request.

        Returns:
            True, False, or None while not known, by the id of the pull request.
        """
        if not found:
            return {}
        columns = self.in_force
        return {
            pk: self.combine(
                column.holds(cells.get(pk)) for column, cells in zip(columns, found, strict=True)
            )
            for pk in found[0]
        }

    def applies(self, issue: Issue, scope: Scope | None = None) -> bool | None:
        """Whether all conditions of the AND hold for a pull request, as each of them filters.

        For an OR, whether one of them holds.

        Parameters:
            issue: The pull request.
            scope: The repositories of the project, for the states of its author; its
                repository when None.

        Returns:
            True or False; None while the data of one is not complete.
        """
        return self.combine(column.holds(column.applies(issue, scope)) for column in self.in_force)

    def holds(self, result: bool | None) -> bool | None:
        """Whether the AND holds, for its result (:meth:`applies`).

        Parameters:
            result: Its result.

        Returns:
            The same.
        """
        return result

    def shows(self, result: bool | None) -> bool:
        """Whether the filter shows a pull request by the AND, for its result.

        Parameters:
            result: Whether all of its conditions hold.

        Returns:
            As a quality check, True when they hold; as Skip if, True: it hides those it
            applies to instead.
        """
        return result is True if self.kind == "check" else True

    def evidence(
        self, issue: Issue, scope: Scope | None = None, project: Project | None = None
    ) -> list[Evidence]:
        """The evidence of every condition of the AND, in its order; of an OR, those that hold.

        An OR of which none holds shows the evidence of all of them.

        Parameters:
            issue: The pull request.
            scope: The repositories of the project, for the states of its author.
            project: The project, for its pages.

        Returns:
            The links, such as to the checks on GitHub.
        """
        columns = self.in_force
        if self.operator == "or":
            holding = [c for c in columns if c.holds(c.applies(issue, scope))]
            columns = tuple(holding) or columns
        return [item for column in columns for item in column.evidence(issue, scope, project)]

    @staticmethod
    def joined_text(parts: Iterable[str], operator: str = "and") -> str:
        """Texts joined by *and*, or by *or*.

        Parameters:
            parts: Such as ``["PR is open", "PR has the label bug"]``.
            operator: ``and`` or ``or``.

        Returns:
            Such as ``PR is open and PR has the label bug``.
        """
        found = ""
        for part in parts:
            if not found:
                found = str(part)
            elif operator == "or":
                found = gettext("%(conditions)s or %(condition)s") % {
                    "conditions": found,
                    "condition": part,
                }
            else:
                found = gettext("%(conditions)s and %(condition)s") % {
                    "conditions": found,
                    "condition": part,
                }
        return found

    @property
    def sentence(self) -> str:
        """The conditions in force as a part of a sentence, joined by *and* or by *or*."""
        parts = (str(c.sentence) for c in self.in_force or self.columns)
        return self.joined_text(parts, self.operator)

    @property
    def summary(self) -> str:
        """The headers of its columns in words, joined by *and* or by *or*."""
        parts = (str(c.summary) for c in self.in_force or self.columns)
        return self.joined_text(parts, self.operator)
