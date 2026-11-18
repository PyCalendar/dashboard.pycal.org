"""The first contribution of a person to a repository."""

from .rule import LabelRule

# GitHub's author_association of people who have not contributed to the repository before
FIRST = {"FIRST_TIME_CONTRIBUTOR", "FIRST_TIMER"}


class FirstContributionRule(LabelRule):
    """``first contribution``: the author has no merged pull request in the repository yet."""

    name = "first-contribution"
    description = (
        "The author has not contributed to the repository before, as GitHub says. "
        "Maintainers welcome them and guide them through their first review."
    )
    labels = {"first contribution": ("ffd43b", "The first contribution of the author")}

    def choose(self, pull: dict) -> str | None:
        """The label for a first contribution.

        Args:
            pull: The pull request, with ``author_association``.

        Returns:
            The label, or None.

        Examples:
            >>> FirstContributionRule().choose({"author_association": "FIRST_TIME_CONTRIBUTOR"})
            'first contribution'
            >>> FirstContributionRule().choose({"author_association": "MEMBER"}) is None
            True
        """
        if pull.get("author_association") in FIRST:
            return "first contribution"
        return None
