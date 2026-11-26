"""The condition ``text_matches``: the title or the description of a pull request matches."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pycal_dashboard.conditions.condition.base import Condition
from pycal_dashboard.conditions.input.boolean import BooleanInput
from pycal_dashboard.conditions.input.choice import ChoiceInput
from pycal_dashboard.conditions.input.text import TextInput
from pycal_dashboard.conditions.spec.issue import IssueData
from pycal_dashboard.conditions.text_match import FIELDS, MAX_PATTERN, MODES, check, matches

if TYPE_CHECKING:
    from pycal_dashboard.models import Issue


class TextMatches(Condition):
    """A text of a pull request matches: it starts with, ends with or contains a text, or a regex.

    Holds when the text of the input ``field`` (``title`` or ``description``) matches the
    input ``text`` as the input ``mode`` says: ``starts``, ``ends``, ``contains`` or
    ``regex``. The case of letters does not matter, unless ``case_sensitive`` is on. A regex
    has at most 100 characters and none of the forms that can be slow, such as ``(a+)+``.
    """

    id = "text_matches"
    title = "Text matches"
    description = "The title or the description of a pull request matches a text or a regex."
    inputs = (
        ChoiceInput("field", "Field", "title or description.", choices=FIELDS),
        ChoiceInput("mode", "Mode", "starts, ends, contains or regex.", choices=MODES),
        TextInput("text", "Text", "The text to match, or the regex.", max_length=MAX_PATTERN),
        BooleanInput(
            "case_sensitive",
            "Case sensitive",
            "Whether the case of letters matters; it does not by default.",
            required=False,
            default=False,
        ),
    )
    data = (IssueData(),)

    @classmethod
    def configure(cls, config: dict | None = None, context: dict | None = None) -> dict:
        """Check a configuration, and that the text or the regex is valid.

        Parameters:
            config: The inputs by name.
            context: Not used.

        Returns:
            The values.

        Raises:
            TextPatternInvalid: The regex is wrong or may be slow.
        """
        values = super().configure(config, context)
        check(values["mode"], values["text"])
        return values

    def assess(self, issue: Issue) -> bool:
        """Whether the text of the pull request matches.

        Parameters:
            issue: The pull request.

        Returns:
            True if it matches.
        """
        values = self.values
        text = issue.title if values["field"] == "title" else issue.description or ""
        return matches(text, values["mode"], values["text"], values.get("case_sensitive", False))
