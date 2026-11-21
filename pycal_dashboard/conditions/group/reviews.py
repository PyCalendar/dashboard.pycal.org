"""The group of reviews: how many reviews a pull request has, compared with a number."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils.translation import gettext, ngettext
from django.utils.translation import gettext_lazy as _

from pycal_dashboard.conditions.condition.reviews import Reviews
from pycal_dashboard.conditions.group.base import ConditionGroup
from pycal_dashboard.conditions.input.comparison import COMPARISONS, INVERSE, NOT_EXACTLY
from pycal_dashboard.conditions.spec.reviews import COUNTED
from pycal_dashboard.errors import ConditionInputMissing

if TYPE_CHECKING:
    from django.http import QueryDict

    from pycal_dashboard.conditions.evidence import Evidence
    from pycal_dashboard.conditions.state.scope import Scope
    from pycal_dashboard.models import Issue, Project

DEFAULT = "at_least"


class ReviewsGroup(ConditionGroup):
    """The reviews of a pull request compared with a number: the condition ``reviews``.

    The choices are the comparison, such as ``at_least``, and the number, from 0 up; reviews
    of comments only do not count. A choice of the number alone, as columns were saved
    before, is at least that number.
    """

    id = "reviews"
    title = _("Reviews")
    comparisons = COMPARISONS  # for the menu of the column
    default = DEFAULT

    @classmethod
    def check(cls, choices: tuple[str, ...]) -> tuple[str, ...]:
        """Check the comparison and the number.

        Parameters:
            choices: The comparison and the number; or the number alone: at least.

        Returns:
            The choices.

        Raises:
            ConditionInputMissing: There is no number.
            ConditionError: The comparison is not known, or the number is not one from 0 up.
        """
        if len(choices) == 1:
            choices = (DEFAULT, *choices)
        if len(choices) != 2 or not choices[1].strip():
            raise ConditionInputMissing("reviews: reviews")
        values = Reviews.configure({"comparison": choices[0], "reviews": choices[1]})
        return values["comparison"], str(values["reviews"])

    @classmethod
    def parse(cls, form: QueryDict) -> tuple[str, ...]:
        """The comparison and the number of a form.

        Parameters:
            form: ``reviews_comparison`` and ``reviews``.

        Returns:
            The choices.
        """
        return cls.check((form.get("reviews_comparison", DEFAULT), form.get("reviews", "")))

    @classmethod
    def applies(
        cls, issue: Issue, choices: tuple[str, ...], scope: Scope | None = None
    ) -> bool | None:
        """Whether the number of reviews of the pull request compares with the number.

        Parameters:
            issue: The pull request.
            choices: The comparison and the number.
            scope: Not used: the reviews are of the pull request itself.

        Returns:
            True or False; None while the reviews are not read.
        """
        return Reviews.check(issue, {"comparison": choices[0], "reviews": int(choices[1])})

    @classmethod
    def evidence(
        cls,
        issue: Issue,
        choices: tuple[str, ...],
        scope: Scope | None = None,
        project: Project | None = None,
    ) -> list[Evidence]:
        """As many reviews as decide the condition, see ``Reviews.evidence``.

        Parameters:
            issue: The pull request.
            choices: The comparison and the number.
            scope: Not used.
            project: Not used.

        Returns:
            The links.
        """
        values = {"comparison": choices[0], "reviews": int(choices[1])}
        return Reviews.evidence(issue, values, scope, project)

    @classmethod
    def cell(cls, issue: Issue, choices: tuple[str, ...], scope: Scope | None = None) -> list[dict]:
        """How many reviews it has, such as ``2 reviews``.

        Parameters:
            issue: The pull request.
            choices: The comparison and the number.
            scope: Not used.

        Returns:
            The number of reviews, when they are read.
        """
        if not Reviews.complete(issue):
            return []
        count = sum(review.state in COUNTED for review in issue.reviews.all())
        text = ngettext("%(count)s review", "%(count)s reviews", count) % {"count": count}
        return [{"text": text, "kind": "number"}]

    @classmethod
    def invert(cls, choices: tuple[str, ...]) -> tuple[str, ...] | None:
        """The opposite comparison, such as below 2 for at least 2.

        Parameters:
            choices: The comparison and the number.

        Returns:
            The choices; None for exactly, which has no opposite comparison.
        """
        inverse = INVERSE.get(choices[0])
        return (inverse, choices[1]) if inverse else None

    @classmethod
    def sentence(cls, choices: tuple[str, ...], negative: bool = False) -> str:
        """Such as ``it has at least 2 reviews`` or ``it has fewer than 2 reviews``.

        Parameters:
            choices: The comparison and the number.
            negative: The pull requests that it does not apply to.

        Returns:
            The part of the sentence.
        """
        comparison, number = choices[0], int(choices[1])
        if negative:
            comparison = INVERSE.get(comparison, "")
        words = gettext(COMPARISONS[comparison][2]) if comparison else gettext(NOT_EXACTLY)
        return ngettext(
            "it has %(comparison)s %(number)s review",
            "it has %(comparison)s %(number)s reviews",
            number,
        ) % {"comparison": words, "number": number}

    @classmethod
    def head(cls, choices: tuple[str, ...]) -> list[dict]:
        """Such as ``reviews ≥ 2``.

        Parameters:
            choices: The comparison and the number.

        Returns:
            One part.
        """
        sign = COMPARISONS[choices[0]][0]
        return [{"text": f"{gettext('reviews')} {sign} {choices[1]}", "kind": "number"}]

    @classmethod
    def summary(cls, choices: tuple[str, ...]) -> str:
        """Such as ``Reviews: at least 2``.

        Parameters:
            choices: The comparison and the number.

        Returns:
            The header.
        """
        return gettext("Reviews: %(comparison)s %(number)s") % {
            "comparison": gettext(COMPARISONS[choices[0]][1]),
            "number": choices[1],
        }
