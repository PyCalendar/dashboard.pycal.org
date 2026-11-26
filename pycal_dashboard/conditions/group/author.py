"""The group of the author: a state of the author of a pull request is above a number."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from pycal_dashboard.conditions.condition.author_state import STATES, AuthorState, has_kinds
from pycal_dashboard.conditions.group.base import ConditionGroup
from pycal_dashboard.conditions.input.comparison import (
    COMPARISONS,
    INVERSE,
    NOT_EXACTLY,
    ComparisonInput,
)
from pycal_dashboard.conditions.input.number import NumberInput
from pycal_dashboard.conditions.review_kinds import ALL, CHOICES, checked
from pycal_dashboard.conditions.review_kinds import text as kinds_text
from pycal_dashboard.errors import ConditionInputMissing, ConditionInputUnknown

if TYPE_CHECKING:
    from django.http import QueryDict

    from pycal_dashboard.conditions.state.scope import Scope
    from pycal_dashboard.models import Issue

NUMBER = NumberInput("number", "Number", minimum=0)
COMPARISON = ComparisonInput("comparison", "Comparison")
DEFAULT = "below"  # such as fewer reviews than pull requests


def state_values(choices: tuple[str, ...]) -> dict:
    """The inputs of the state of a column, from the choices after the number.

    Parameters:
        choices: The state, the comparison, the number and the kinds of reviews if not all.

    Returns:
        ``kinds`` for a state that counts reviews, else nothing.
    """
    return {"kinds": checked(choices[3:])} if has_kinds(STATES[choices[0]]) else {}


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
    """A state of the author compared with a number, such as ``review_ratio``.

    The choices are the id of the state, such as ``review_ratio``, the comparison, such as
    ``below``, and the number. The state is
    counted in all repositories of the project that the viewer sees; the condition
    ``review_ratio`` checks the same with the state ``review_ratio``. A choice of the state
    and the number alone, as columns were saved before, is above that number.
    """

    id = "author"
    title = _("Author")
    states = STATES  # for the menu of the column
    comparisons = COMPARISONS
    default = DEFAULT

    @classmethod
    def check(cls, choices: tuple[str, ...]) -> tuple[str, ...]:
        """Check the state, the comparison and the number.

        Parameters:
            choices: The id of the state, the comparison, the number and, for a state that
                counts reviews, their kinds if not all; or the state and the number alone: above.

        Returns:
            The choices, the number as people write it, without the kinds when all count.

        Raises:
            ConditionInputMissing: There is no number.
            ConditionInputUnknown: The state, the comparison or a kind of review is not known.
            ConditionError: The number is wrong.
        """
        if len(choices) == 2:
            choices = (choices[0], "above", choices[1])
        if len(choices) < 3 or not choices[2].strip():
            raise ConditionInputMissing("author: number")
        if choices[0] not in STATES:
            raise ConditionInputUnknown(f"author: {choices[0]}")
        extra = [kind for kind in choices[3:] if kind not in CHOICES]
        if extra:
            raise ConditionInputUnknown(f"author: {', '.join(extra)}")
        kinds = checked(choices[3:]) if has_kinds(STATES[choices[0]]) else ALL
        found = (choices[0], COMPARISON.parse(choices[1]), number_text(NUMBER.parse(choices[2])))
        return (*found, *(() if kinds == ALL else kinds))

    @classmethod
    def parse(cls, form: QueryDict) -> tuple[str, ...]:
        """The state, the comparison and the number of a form.

        Parameters:
            form: ``state``, ``comparison``, ``number`` and ``author_kinds``, the switches of
                the kinds of reviews, with ``author_kinds_form``.

        Returns:
            The choices.

        Raises:
            ConditionInputMissing: A state that counts reviews, and no kind switched on.
        """
        state = form.get("state", "")
        kinds = tuple(form.getlist("author_kinds"))
        counts_reviews = state in STATES and has_kinds(STATES[state])
        if counts_reviews and form.get("author_kinds_form") and not kinds:
            raise ConditionInputMissing("author: kinds")
        return cls.check(
            (
                state,
                form.get("comparison", DEFAULT),
                form.get("number", ""),
                *(kinds if counts_reviews else ()),
            )
        )

    @classmethod
    def specs(cls, choices: tuple[str, ...]) -> list[dict]:
        """The condition ``author_state`` of the state, the comparison and the number.

        Parameters:
            choices: The state, the comparison, the number and the kinds of reviews if not all.

        Returns:
            The spec.

        Examples:
            >>> AuthorGroup.specs(("pull_requests_opened", "below", "2"))[0]["number"]
            2.0
            >>> AuthorGroup.specs(("reviews_given", "below", "2", "approved"))[0]["kinds"]
            ('approved',)
        """
        spec = {
            "id": AuthorState.id,
            "state": choices[0],
            "comparison": choices[1],
            "number": float(choices[2]),
        }
        return [{**spec, **state_values(choices)}]

    @classmethod
    def choices_of(cls, specs: list[dict]) -> tuple[str, ...] | None:
        """The choices of ``author_state``, and of its NOT: the opposite comparison.

        Parameters:
            specs: The specs of the conditions.

        Returns:
            The state, the comparison, the number and the kinds if not all; None for other
            conditions, and for the NOT of exactly.
        """
        if len(specs) != 1 or specs[0].get("id") not in (AuthorState.id, AuthorState.negate().id):
            return None
        spec = specs[0]
        comparison = spec["comparison"]
        if spec["id"] != AuthorState.id:
            comparison = INVERSE.get(comparison)
            if comparison is None:
                return None
        kinds = checked(spec["kinds"]) if has_kinds(STATES[spec["state"]]) else ALL
        found = (spec["state"], comparison, number_text(spec["number"]))
        return (*found, *(() if kinds == ALL else kinds))

    @classmethod
    def cell(cls, issue: Issue, choices: tuple[str, ...], scope: Scope | None = None) -> list[dict]:
        """The number of the author, such as ``1.5``.

        Parameters:
            issue: The pull request.
            choices: The state, the comparison and the number.
            scope: The repositories of the project.

        Returns:
            The number, when it is known.
        """
        value = STATES[choices[0]].observe(issue, scope, state_values(choices))
        return [] if value is None else [{"text": number_text(value), "kind": "number"}]

    @classmethod
    def unknown(cls, issue: Issue, choices: tuple[str, ...]) -> str:
        """Why the state is not known: no author, or the reviews of a repository not read.

        Parameters:
            issue: The pull request.
            choices: The state, the comparison and the number.

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
        """Such as ``PR author has a review to pull request ratio below 1``.

        Parameters:
            choices: The state, the comparison and the number.
            negative: The pull requests that it does not apply to.

        Returns:
            The part of the sentence.
        """
        state, comparison = STATES[choices[0]], choices[1]
        if negative:
            comparison = INVERSE.get(comparison, "")
        if comparison:
            words = gettext(COMPARISONS[comparison][2 if state.counted else 1])
        else:
            words = gettext(NOT_EXACTLY)
        text = gettext(state.phrase) % {"comparison": words, "number": choices[2]}
        kinds = state_values(choices).get("kinds", ALL)
        if kinds != ALL:
            text += gettext(" (reviews: %(kinds)s)") % {"kinds": kinds_text(kinds)}
        return text

    @classmethod
    def head(cls, choices: tuple[str, ...]) -> list[dict]:
        """Such as ``Review to pull request ratio < 1``.

        Parameters:
            choices: The state, the comparison and the number.

        Returns:
            One part.
        """
        title = gettext(STATES[choices[0]].title)
        sign = COMPARISONS[choices[1]][0]
        head = [{"text": f"{title} {sign} {choices[2]}", "kind": "number"}]
        kinds = state_values(choices).get("kinds", ALL)
        if kinds != ALL:
            head.append({"text": ", ".join(gettext(CHOICES[k][1]) for k in kinds), "kind": "kinds"})
        return head

    @classmethod
    def summary(cls, choices: tuple[str, ...]) -> str:
        """Such as ``Author: review to pull request ratio below 1``.

        Parameters:
            choices: The state, the comparison and the number.

        Returns:
            The header.
        """
        return gettext("Author: %(state)s %(comparison)s %(number)s") % {
            "state": gettext(STATES[choices[0]].title).lower(),
            "comparison": gettext(COMPARISONS[choices[1]][1]),
            "number": choices[2],
        }
