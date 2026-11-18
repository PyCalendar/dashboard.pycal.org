"""The rules of ``PULL_REQUEST_LABELS`` and the change of labels they ask for."""

from dataclasses import dataclass, field

from pycal_dashboard.errors import UnknownLabelRule

from .first_contribution_rule import FirstContributionRule
from .rule import LabelRule
from .size_rule import SizeRule

RULES: dict[str, type[LabelRule]] = {rule.name: rule for rule in (SizeRule, FirstContributionRule)}


@dataclass(frozen=True)
class RuleSet:
    """The rules that label the pull requests of the site."""

    rules: tuple[LabelRule, ...] = field(default_factory=tuple)

    @classmethod
    def parse(cls, value: str) -> "RuleSet":
        """The rules of the setting.

        Args:
            value: The names of the rules, separated by commas.

        Returns:
            The rules.

        Raises:
            UnknownLabelRule: A name is not a rule.

        Examples:
            >>> [rule.name for rule in RuleSet.parse("size, first-contribution").rules]
            ['size', 'first-contribution']
            >>> RuleSet.parse("").rules
            ()
        """
        names = [name.strip() for name in value.split(",") if name.strip()]
        for name in names:
            if name not in RULES:
                raise UnknownLabelRule(f"{name!r}; known: {', '.join(sorted(RULES))}")
        return cls(tuple(RULES[name]() for name in names))

    def managed(self) -> set[str]:
        """The labels that belong to the rules.

        Returns:
            The names of the labels.
        """
        return {label for rule in self.rules for label in rule.labels}

    def wanted(self, pull: dict) -> set[str]:
        """The labels of the rules for a pull request.

        Args:
            pull: The pull request as GitHub describes it.

        Returns:
            The labels.
        """
        chosen = (rule.choose(pull) for rule in self.rules)
        return {label for label in chosen if label}

    def changes(self, pull: dict, current: set[str]) -> tuple[set[str], set[str]]:
        """The labels to add and to remove: the smallest change.

        Args:
            pull: The pull request.
            current: Its labels now.

        Returns:
            The labels to add and those to remove; labels of people stay.

        Examples:
            >>> rules = RuleSet.parse("size")
            >>> rules.changes({"additions": 1, "deletions": 0}, {"size: L", "bug"})
            ({'size: XS'}, {'size: L'})
            >>> rules.changes({"additions": 1, "deletions": 0}, {"size: XS"})
            (set(), set())
        """
        wanted = self.wanted(pull)
        return wanted - current, (current & self.managed()) - wanted

    def color(self, label: str) -> tuple[str, str]:
        """The color and description of a label of the rules on GitHub.

        Args:
            label: The name of the label.

        Returns:
            The color without ``#`` and the description.
        """
        for rule in self.rules:
            if label in rule.labels:
                return rule.labels[label]
        return "ededed", ""
