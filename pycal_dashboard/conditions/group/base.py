"""A group of conditions as a column of the table of pull requests."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar

from django.utils.translation import gettext

if TYPE_CHECKING:
    from django.http import QueryDict

    from pycal_dashboard.models import Issue


class ConditionGroup(ABC):
    """Conditions that people choose together, such as the states of a branch.

    A group reads its choices from a form (:meth:`parse`), says whether they apply to a pull
    request (:meth:`applies`), and what its cell shows (:meth:`cell`): a text that is
    translated, with the class of its color.

    Attributes:
        id: The name of the group in the address of the table, such as ``branch``.
        title: The name of the group for people.
    """

    id: ClassVar[str] = ""
    title: ClassVar[str] = ""

    @classmethod
    @abstractmethod
    def parse(cls, form: QueryDict) -> tuple[str, ...]:
        """The choices of the group in a form, checked.

        Parameters:
            form: The fields of the form, such as ``label`` and ``mode``.

        Returns:
            The choices, as the address of the table keeps them.

        Raises:
            ConditionError: A choice is missing or wrong: a subclass of it says how.
        """

    @classmethod
    @abstractmethod
    def check(cls, choices: tuple[str, ...]) -> tuple[str, ...]:
        """Check choices from the address of the table.

        Parameters:
            choices: The choices.

        Returns:
            The choices.

        Raises:
            ConditionError: A choice is missing or wrong.
        """

    @classmethod
    @abstractmethod
    def applies(cls, issue: Issue, choices: tuple[str, ...]) -> bool | None:
        """Whether the condition applies to a pull request.

        Parameters:
            issue: The pull request, with its labels and state.
            choices: The choices.

        Returns:
            True or False; None while its data is not complete.
        """

    @classmethod
    @abstractmethod
    def cell(cls, issue: Issue, choices: tuple[str, ...]) -> list[dict]:
        """What the cell of a pull request shows besides whether the condition applies.

        Parameters:
            issue: The pull request.
            choices: The choices.

        Returns:
            Parts of the cell: ``text`` and ``kind``, such as ``open`` or ``label``, for its
            color.
        """

    @classmethod
    @abstractmethod
    def sentence(cls, choices: tuple[str, ...], negative: bool = False) -> str:
        """The condition as a part of a sentence about a pull request, translated.

        Parameters:
            choices: The choices.
            negative: The pull requests that it does not apply to.

        Returns:
            Such as ``it has the label bug`` or ``its branch is not outdated or in conflict``.
        """

    @classmethod
    def unknown(cls, issue: Issue, choices: tuple[str, ...]) -> str:
        """Why the condition cannot be assessed for a pull request, for its question mark.

        Parameters:
            issue: The pull request.
            choices: The choices.

        Returns:
            The reason, translated.
        """
        return gettext("not known yet: the data of the pull request is not read yet")

    @classmethod
    def opposite(cls, choices: tuple[str, ...]) -> tuple[str, ...] | None:
        """The choices that apply exactly when these do not, if the group knows them.

        A column that shows only the pull requests it does not apply to can then show those
        that its opposite applies to, which reads more easily.

        Parameters:
            choices: The choices.

        Returns:
            The opposite choices; None if there are none for sure.
        """
        return None

    @classmethod
    @abstractmethod
    def head(cls, choices: tuple[str, ...]) -> list[dict]:
        """The shortest header of the column: the parts it shows, such as the states chosen.

        Parameters:
            choices: The choices.

        Returns:
            Parts with ``text`` and ``kind`` for their color; a label also with ``absent``.
        """

    @classmethod
    @abstractmethod
    def summary(cls, choices: tuple[str, ...]) -> str:
        """The header of the column: the group and its choices, translated.

        Parameters:
            choices: The choices.

        Returns:
            Such as ``Branch: outdated, conflict``.
        """
