"""The slugs of projects, ``/projects/<slug>/<name>/``: their rules and suggestions.

A slug has the letters of a GitHub handle (a to z, 0 to 9 and single hyphens inside), and at
most one ``~`` between the account and the name of a repository, such as ``collective~icalendar``.
It is kept in lower case. New projects get a random one of six hexadecimal digits.
"""

import re
import secrets
from collections.abc import Iterator

from django.utils.text import slugify

PART = r"[a-z0-9]+(?:-[a-z0-9]+)*"
PATTERN = re.compile(rf"{PART}(?:~{PART})?")
MAX_LENGTH = 80
RESERVED = {"new"}  # /projects/new/ creates a project
NUMBERS = 1000  # how far the suggestions count up


def valid(slug: str) -> bool:
    """Whether a slug follows the rules.

    Args:
        slug: The slug, in lower case.

    Returns:
        True if it may be used.

    Examples:
        >>> [valid(a) for a in ["icalendar", "collective~icalendar-2", "a--b", "-a", "a~b~c"]]
        [True, True, False, False, False]
        >>> valid("new"), valid("Upper")
        (False, False)
    """
    return len(slug) <= MAX_LENGTH and slug not in RESERVED and bool(PATTERN.fullmatch(slug))


def normalize(text: str) -> str:
    """Text as a part of a slug: lower case, other characters become single hyphens.

    Args:
        text: Such as the name of a repository.

    Returns:
        The part, "" if nothing remains.

    Examples:
        >>> normalize("My_Repo.py"), normalize("..."), normalize("Ünïcode")
        ('my-repo-py', '', 'unicode')
    """
    separated = slugify(re.sub(r"[\W_]+", "-", text))  # slugify drops dots without a hyphen
    return re.sub(r"[^a-z0-9]+", "-", separated.lower()).strip("-")


def random_slug() -> str:
    """A random slug of six hexadecimal digits, such as ``3f9a0c``.

    Returns:
        The slug; it may be taken.
    """
    return secrets.token_hex(3)


def suggestions(full_name: str) -> Iterator[str]:
    """The sluges to propose for a project of one repository, best first.

    Args:
        full_name: The repository, such as ``collective/icalendar``.

    Yields:
        The name of the repository, then ``account~name``, then it with 2, 3 ... at the end.

    Examples:
        >>> from itertools import islice
        >>> list(islice(suggestions("collective/icalendar"), 4))
        ['icalendar', 'collective~icalendar', 'collective~icalendar-2', 'collective~icalendar-3']
    """
    owner, _slash, name = full_name.partition("/")
    owner, name = normalize(owner), normalize(name)
    both = f"{owner}~{name}"[: MAX_LENGTH - 5]
    for slug in (name, both):
        if valid(slug):
            yield slug
    for number in range(2, NUMBERS):
        if valid(f"{both}-{number}"):
            yield f"{both}-{number}"
