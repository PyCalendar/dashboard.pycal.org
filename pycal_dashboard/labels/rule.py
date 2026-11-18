"""The base of the rules that label pull requests."""


class LabelRule:
    """A rule chooses at most one of its labels for a pull request.

    The labels of a rule belong to it: the rule removes those that do not apply any more and
    never touches the labels of people or other rules.
    """

    name = ""  # the name in PULL_REQUEST_LABELS
    description = ""  # for the page Labels and the documentation
    # label name: (color without #, description on GitHub)
    labels: dict[str, tuple[str, str]] = {}

    def choose(self, pull: dict) -> str | None:
        """The label of this rule for a pull request.

        Args:
            pull: The pull request as GitHub describes it.

        Returns:
            One of :attr:`labels`, or None for none of them.
        """
        raise NotImplementedError
