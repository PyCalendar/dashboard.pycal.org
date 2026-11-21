"""How a text of a pull request matches: starts with, ends with, contains, or a regex.

The texts are the title and the description of a pull request. A regular expression is short
and refuses the forms that can take very long to match, such as nested repetitions, because
the table of pull requests evaluates the columns of its address for every visitor.
"""

from __future__ import annotations

import functools
import re

from django.utils.translation import gettext_noop

from pycal_dashboard.errors import TextPatternInvalid

# the texts of a pull request that a condition matches, with their names for people
FIELDS = {"title": gettext_noop("title"), "description": gettext_noop("description")}
# how a text matches, with their words for people
MODES = {
    "starts": gettext_noop("starts with"),
    "ends": gettext_noop("ends with"),
    "contains": gettext_noop("contains"),
    "regex": gettext_noop("matches the regex"),
}
MAX_PATTERN = 100  # the most characters of a text to match or of a regex
# a repetition of a group that repeats itself, such as (a+)+, and back-references: slow forms
SLOW = re.compile(r"\((?:[^()\\]|\\.)*[+*}](?:[^()\\]|\\.)*\)\s*[+*{]|\\[1-9]|\(\?P=")


def check(mode: str, pattern: str) -> str:
    """Check a text to match, or a regular expression.

    Parameters:
        mode: One of ``MODES``.
        pattern: The text, or the regular expression for ``regex``.

    Returns:
        The pattern.

    Raises:
        TextPatternInvalid: It is empty, too long, or a regex that is wrong or may be slow.

    Examples:
        >>> check("regex", "^(fix|feat):")
        '^(fix|feat):'
        >>> check("regex", "(a+)+b")
        Traceback (most recent call last):
        ...
        pycal_dashboard.errors.conditions.TextPatternInvalid: may be slow: (a+)+b
    """
    if not pattern or len(pattern) > MAX_PATTERN:
        raise TextPatternInvalid(f"at most {MAX_PATTERN} characters: {pattern[:20]!r}")
    if mode == "regex":
        if SLOW.search(pattern):
            raise TextPatternInvalid(f"may be slow: {pattern}")
        try:
            compiled(pattern, True)
        except re.error as error:
            raise TextPatternInvalid(f"{error}: {pattern}") from None
    return pattern


@functools.lru_cache(maxsize=256)
def compiled(pattern: str, case: bool) -> re.Pattern:
    """A regular expression, compiled once.

    Parameters:
        pattern: The regular expression.
        case: Whether the case of letters matters.

    Returns:
        The compiled expression.
    """
    return re.compile(pattern, 0 if case else re.IGNORECASE)


def matches(text: str, mode: str, pattern: str, case: bool = False) -> bool:
    """Whether a text matches.

    Parameters:
        text: The text, such as the title of a pull request.
        mode: One of ``MODES``.
        pattern: The text to match, or the regular expression.
        case: Whether the case of letters matters; it does not by default.

    Returns:
        True if it matches.

    Examples:
        >>> title = "Fix the build"
        >>> matches(title, "starts", "fix"), matches(title, "starts", "fix", True)
        (True, False)
        >>> matches("feat: steps", "regex", r"^(fix|feat):"), matches("a WIP b", "contains", "wip")
        (True, True)
    """
    if mode == "regex":
        return compiled(pattern, case).search(text) is not None
    if not case:
        text, pattern = text.casefold(), pattern.casefold()
    if mode == "starts":
        return text.startswith(pattern)
    if mode == "ends":
        return text.endswith(pattern)
    return pattern in text
