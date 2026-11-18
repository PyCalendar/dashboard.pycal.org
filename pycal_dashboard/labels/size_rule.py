"""The size of a pull request: the lines it adds and removes."""

from pycal_dashboard.errors import PullRequestSizeUnknown

from .rule import LabelRule

# the largest number of changed lines of each label; larger is XL
LIMITS = ((9, "size: XS"), (49, "size: S"), (249, "size: M"), (999, "size: L"))


class SizeRule(LabelRule):
    """``size: XS`` to ``size: XL``: small pull requests are reviewed sooner."""

    name = "size"
    description = (
        "The lines a pull request adds and removes: XS up to 9, S up to 49, M up to 249, "
        "L up to 999 and XL above. Reviewers find small pull requests quickly."
    )
    labels = {
        "size: XS": ("c6dcef", "Changes up to 9 lines"),
        "size: S": ("8fbbe0", "Changes up to 49 lines"),
        "size: M": ("3b79aa", "Changes up to 249 lines"),
        "size: L": ("ffd43b", "Changes up to 999 lines"),
        "size: XL": ("a3242f", "Changes 1000 lines or more"),
    }

    def choose(self, pull: dict) -> str | None:
        """The size label.

        Args:
            pull: The pull request, with ``additions`` and ``deletions``.

        Returns:
            The label.

        Raises:
            PullRequestSizeUnknown: GitHub did not send the numbers of lines.

        Examples:
            >>> SizeRule().choose({"additions": 3, "deletions": 6})
            'size: XS'
            >>> SizeRule().choose({"additions": 1000, "deletions": 0})
            'size: XL'
        """
        additions, deletions = pull.get("additions"), pull.get("deletions")
        if not isinstance(additions, int) or not isinstance(deletions, int):
            raise PullRequestSizeUnknown(f"#{pull.get('number')}")
        lines = additions + deletions
        for limit, label in LIMITS:
            if lines <= limit:
                return label
        return "size: XL"
