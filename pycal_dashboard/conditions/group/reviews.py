"""The group of reviews: a pull request has at least a number of reviews."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils.translation import gettext, ngettext
from django.utils.translation import gettext_lazy as _

from pycal_dashboard.conditions.condition.reviews_at_least import ReviewsAtLeast
from pycal_dashboard.conditions.group.base import ConditionGroup
from pycal_dashboard.conditions.spec.reviews import COUNTED
from pycal_dashboard.errors import ConditionInputMissing

if TYPE_CHECKING:
    from django.http import QueryDict

    from pycal_dashboard.conditions.state.scope import Scope
    from pycal_dashboard.models import Issue


class ReviewsGroup(ConditionGroup):
    """At least a number of reviews: ``reviews_at_least``.

    The choice is the number, from 1 up; reviews of comments only do not count.
    """

    id = "reviews"
    title = _("Reviews")

    @classmethod
    def check(cls, choices: tuple[str, ...]) -> tuple[str, ...]:
        """Check the number.

        Parameters:
            choices: The number of reviews.

        Returns:
            The choices.

        Raises:
            ConditionInputMissing: There is no number.
            ConditionError: It is not a whole number from 1 up.
        """
        if len(choices) != 1 or not choices[0].strip():
            raise ConditionInputMissing("reviews: reviews")
        return (str(ReviewsAtLeast.configure({"reviews": choices[0]})["reviews"]),)

    @classmethod
    def parse(cls, form: QueryDict) -> tuple[str, ...]:
        """The number of a form.

        Parameters:
            form: ``reviews``.

        Returns:
            The choices.
        """
        return cls.check((form.get("reviews", ""),))

    @classmethod
    def applies(
        cls, issue: Issue, choices: tuple[str, ...], scope: Scope | None = None
    ) -> bool | None:
        """Whether the pull request has at least the number of reviews.

        Parameters:
            issue: The pull request.
            choices: The number.
            scope: Not used: the reviews are of the pull request itself.

        Returns:
            True or False; None while the reviews are not read.
        """
        return ReviewsAtLeast.check(issue, {"reviews": int(choices[0])})

    @classmethod
    def cell(cls, issue: Issue, choices: tuple[str, ...], scope: Scope | None = None) -> list[dict]:
        """How many reviews it has, such as ``2 reviews``.

        Parameters:
            issue: The pull request.
            choices: The number.
            scope: Not used.

        Returns:
            The number of reviews, when they are read.
        """
        if not ReviewsAtLeast.complete(issue):
            return []
        count = sum(review.state in COUNTED for review in issue.reviews.all())
        text = ngettext("%(count)s review", "%(count)s reviews", count) % {"count": count}
        return [{"text": text, "kind": "number"}]

    @classmethod
    def sentence(cls, choices: tuple[str, ...], negative: bool = False) -> str:
        """Such as ``it has at least 2 reviews`` or ``it has fewer than 2 reviews``.

        Parameters:
            choices: The number.
            negative: The pull requests that it does not apply to.

        Returns:
            The part of the sentence.
        """
        number = int(choices[0])
        if negative:
            return ngettext(
                "it has fewer than %(number)s review",
                "it has fewer than %(number)s reviews",
                number,
            ) % {"number": number}
        return ngettext(
            "it has at least %(number)s review", "it has at least %(number)s reviews", number
        ) % {"number": number}

    @classmethod
    def head(cls, choices: tuple[str, ...]) -> list[dict]:
        """Such as ``≥ 2 reviews``.

        Parameters:
            choices: The number.

        Returns:
            One part.
        """
        number = int(choices[0])
        text = ngettext("≥ %(number)s review", "≥ %(number)s reviews", number)
        return [{"text": text % {"number": number}, "kind": "number"}]

    @classmethod
    def summary(cls, choices: tuple[str, ...]) -> str:
        """Such as ``Reviews: at least 2``.

        Parameters:
            choices: The number.

        Returns:
            The header.
        """
        return gettext("Reviews: at least %(number)s") % {"number": choices[0]}
