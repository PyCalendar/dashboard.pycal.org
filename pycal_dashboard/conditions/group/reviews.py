"""The group of reviews: how many reviews a pull request has, compared with a number."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils.translation import gettext, ngettext
from django.utils.translation import gettext_lazy as _

from pycal_dashboard.conditions.condition.reviews import Reviews
from pycal_dashboard.conditions.group.base import ConditionGroup
from pycal_dashboard.conditions.input.comparison import COMPARISONS, INVERSE, NOT_EXACTLY
from pycal_dashboard.conditions.review_kinds import ALL, CHOICES, DISMISSED_HELP, checked
from pycal_dashboard.conditions.review_kinds import text as kinds_text
from pycal_dashboard.conditions.spec.reviews import ReviewsData
from pycal_dashboard.errors import ConditionInputMissing, ConditionInputUnknown

if TYPE_CHECKING:
    from django.http import QueryDict

    from pycal_dashboard.conditions.evidence import Evidence
    from pycal_dashboard.conditions.state.scope import Scope
    from pycal_dashboard.models import Issue, Project

DEFAULT = "at_least"
LEGACY = "comments"  # saved before the kinds: all kinds count


def values(choices: tuple[str, ...]) -> dict:
    """The configuration of the condition ``reviews`` of the choices of a column.

    Parameters:
        choices: The comparison, the number and the kinds, if not all.

    Returns:
        ``comparison``, ``reviews`` and ``kinds``.

    Examples:
        >>> values(("below", "2", "approved"))
        {'comparison': 'below', 'reviews': 2, 'kinds': ('approved',)}
    """
    return {"comparison": choices[0], "reviews": int(choices[1]), "kinds": checked(choices[2:])}


class ReviewsGroup(ConditionGroup):
    """The reviews of a pull request compared with a number: the condition ``reviews``.

    The choices are the comparison, such as ``at_least``, the number, from 0 up, and the kinds
    of reviews that count, such as ``approved``, when not all of them do
    (:mod:`~pycal_dashboard.conditions.review_kinds`). A choice of the number alone, as columns
    were saved before, is at least that number; ``comments``, as they were saved before, is all
    kinds.
    """

    id = "reviews"
    title = _("Reviews")
    comparisons = COMPARISONS  # for the menu of the column
    kinds = CHOICES  # the kinds of reviews, for the switches of the menu
    kinds_help = DISMISSED_HELP
    default = DEFAULT

    @classmethod
    def check(cls, choices: tuple[str, ...]) -> tuple[str, ...]:
        """Check the comparison and the number.

        Parameters:
            choices: The comparison, the number and the kinds of reviews if not all; or the
                number alone: at least.

        Returns:
            The choices, without the kinds when all of them count.

        Raises:
            ConditionInputMissing: There is no number.
            ConditionInputUnknown: A choice after the number is no kind of review.
            ConditionError: The comparison is not known, or the number is not one from 0 up.
        """
        if len(choices) == 1:
            choices = (DEFAULT, *choices)
        if len(choices) < 2 or not choices[1].strip():
            raise ConditionInputMissing("reviews: reviews")
        unknown = [kind for kind in choices[2:] if kind not in CHOICES and kind != LEGACY]
        if unknown:
            raise ConditionInputUnknown(f"reviews: {', '.join(unknown)}")
        found = Reviews.configure({"comparison": choices[0], "reviews": choices[1]})
        kinds = checked(choices[2:])
        return found["comparison"], str(found["reviews"]), *(() if kinds == ALL else kinds)

    @classmethod
    def parse(cls, form: QueryDict) -> tuple[str, ...]:
        """The comparison and the number of a form.

        Parameters:
            form: ``reviews_comparison``, ``reviews`` and ``reviews_kinds``, the switches of the
                kinds of reviews that count; ``reviews_kinds_form`` says that the form has them.

        Returns:
            The choices.

        Raises:
            ConditionInputMissing: No kind of review is switched on.
        """
        kinds = tuple(form.getlist("reviews_kinds"))
        if form.get("reviews_kinds_form") and not kinds:
            raise ConditionInputMissing("reviews: kinds")
        return cls.check((form.get("reviews_comparison", DEFAULT), form.get("reviews", ""), *kinds))

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
        return Reviews.check(issue, values(choices))

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
        return Reviews.evidence(issue, values(choices), scope, project)

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
        count = len(ReviewsData.counted(issue, checked(choices[2:])))
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
        return (inverse, *choices[1:]) if inverse else None

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
        kinds = checked(choices[2:])
        if kinds != ALL:
            return ngettext(
                "it has %(comparison)s %(number)s review: %(kinds)s",
                "it has %(comparison)s %(number)s reviews: %(kinds)s",
                number,
            ) % {"comparison": words, "number": number, "kinds": kinds_text(kinds)}
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
        head = [{"text": f"{gettext('reviews')} {sign} {choices[1]}", "kind": "number"}]
        kinds = checked(choices[2:])
        if kinds != ALL:
            head.append({"text": ", ".join(gettext(CHOICES[k][1]) for k in kinds), "kind": "kinds"})
        return head

    @classmethod
    def summary(cls, choices: tuple[str, ...]) -> str:
        """Such as ``Reviews: at least 2``.

        Parameters:
            choices: The comparison and the number.

        Returns:
            The header.
        """
        found = {"comparison": gettext(COMPARISONS[choices[0]][1]), "number": choices[1]}
        kinds = checked(choices[2:])
        if kinds != ALL:
            found["kinds"] = kinds_text(kinds)
            return gettext("Reviews: %(comparison)s %(number)s (%(kinds)s)") % found
        return gettext("Reviews: %(comparison)s %(number)s") % found
