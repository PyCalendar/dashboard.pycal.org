"""The group of the author: a state of the author of a pull request is above a number."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from pycal_dashboard.conditions.group.base import ConditionGroup
from pycal_dashboard.conditions.input.number import NumberInput
from pycal_dashboard.conditions.state.own_pull_requests_closed import OwnPullRequestsClosed
from pycal_dashboard.conditions.state.pull_requests_opened import PullRequestsOpened
from pycal_dashboard.conditions.state.review_ratio import ReviewRatio
from pycal_dashboard.conditions.state.reviews_given import ReviewsGiven
from pycal_dashboard.errors import ConditionInputMissing, ConditionInputUnknown

if TYPE_CHECKING:
    from django.http import QueryDict

    from pycal_dashboard.conditions.state.person import PersonState
    from pycal_dashboard.conditions.state.scope import Scope
    from pycal_dashboard.models import Issue

# the states of the author that a column compares, in the order of the menu
STATES: dict[str, type[PersonState]] = {
    state.id: state
    for state in (ReviewRatio, ReviewsGiven, PullRequestsOpened, OwnPullRequestsClosed)
}
NUMBER = NumberInput("above", "Above", minimum=0)


def number_text(number: float) -> str:
    """A number as people read it: ``1.5``, ``2``, ``∞``.

    Parameters:
        number: The number.

    Returns:
        Its text.

    Examples:
        >>> number_text(2.0), number_text(0.333333), number_text(float("inf"))
        ('2', '0.33', '∞')
    """
    if math.isinf(number):
        return "∞"
    return f"{round(number, 2):g}"


class AuthorGroup(ConditionGroup):
    """A state of the author above a number, such as ``review_ratio_above``.

    The choices are the id of the state, such as ``review_ratio``, and the number. The state is
    counted in all repositories of the project that the viewer sees; the condition
    ``review_ratio_above`` checks the same with the state ``review_ratio``.
    """

    id = "author"
    title = _("Author")
    states = STATES  # for the menu of the column

    @classmethod
    def check(cls, choices: tuple[str, ...]) -> tuple[str, ...]:
        """Check the state and the number.

        Parameters:
            choices: The id of the state and the number.

        Returns:
            The choices, the number as people write it.

        Raises:
            ConditionInputMissing: There is no number.
            ConditionInputUnknown: The state is not known.
            ConditionError: The number is wrong.
        """
        if len(choices) != 2 or not choices[1].strip():
            raise ConditionInputMissing("author: above")
        if choices[0] not in STATES:
            raise ConditionInputUnknown(f"author: {choices[0]}")
        return choices[0], number_text(NUMBER.parse(choices[1]))

    @classmethod
    def parse(cls, form: QueryDict) -> tuple[str, ...]:
        """The state and the number of a form.

        Parameters:
            form: ``state`` and ``above``.

        Returns:
            The choices.
        """
        return cls.check((form.get("state", ""), form.get("above", "")))

    @classmethod
    def applies(
        cls, issue: Issue, choices: tuple[str, ...], scope: Scope | None = None
    ) -> bool | None:
        """Whether the state of the author is above the number.

        Parameters:
            issue: The pull request.
            choices: The state and the number.
            scope: The repositories of the project.

        Returns:
            True or False; None while the data of a repository is not complete, or without
            an author.
        """
        if not issue.pull_request:
            return None
        return STATES[choices[0]].above(issue, float(choices[1]), scope)

    @classmethod
    def cell(cls, issue: Issue, choices: tuple[str, ...], scope: Scope | None = None) -> list[dict]:
        """The number of the author, such as ``1.5``.

        Parameters:
            issue: The pull request.
            choices: The state and the number.
            scope: The repositories of the project.

        Returns:
            The number, when it is known.
        """
        value = STATES[choices[0]].observe(issue, scope)
        return [] if value is None else [{"text": number_text(value), "kind": "number"}]

    @classmethod
    def unknown(cls, issue: Issue, choices: tuple[str, ...]) -> str:
        """Why the state is not known: no author, or the reviews of a repository not read.

        Parameters:
            issue: The pull request.
            choices: The state and the number.

        Returns:
            The reason, translated.
        """
        if issue.author_id is None:
            return gettext("not known: GitHub does not say who opened it")
        return gettext(
            "not known yet: the reviews of a repository of the project are not read yet; they "
            "need the GitHub App"
        )

    @classmethod
    def sentence(cls, choices: tuple[str, ...], negative: bool = False) -> str:
        """Such as ``its author has a review to pull request ratio above 1.5``.

        Parameters:
            choices: The state and the number.
            negative: The pull requests that it does not apply to.

        Returns:
            The part of the sentence.
        """
        return gettext(STATES[choices[0]].phrase[1 if negative else 0]) % {"number": choices[1]}

    @classmethod
    def head(cls, choices: tuple[str, ...]) -> list[dict]:
        """Such as ``Review to pull request ratio > 1.5``.

        Parameters:
            choices: The state and the number.

        Returns:
            One part.
        """
        title = gettext(STATES[choices[0]].title)
        return [{"text": f"{title} > {choices[1]}", "kind": "number"}]

    @classmethod
    def summary(cls, choices: tuple[str, ...]) -> str:
        """Such as ``Author: review to pull request ratio above 1.5``.

        Parameters:
            choices: The state and the number.

        Returns:
            The header.
        """
        return gettext("Author: %(state)s above %(number)s") % {
            "state": gettext(STATES[choices[0]].title).lower(),
            "number": choices[1],
        }
