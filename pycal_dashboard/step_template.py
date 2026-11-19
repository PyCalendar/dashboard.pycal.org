"""Templates of the steps of pull requests: ``{variable}`` replaced, safely, then Markdown.

The summary of a step and the description of its conditions are written by the people of a
project, and the values come from GitHub, written by anybody: a title such as
``[click](https://evil.example)`` must stay text. So only the variables of :data:`VARIABLES`
are replaced, nothing else of the template is evaluated, and each value is escaped for
Markdown; the result is shown with the filter ``|markdown``, cleaned by nh3.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from pycal_dashboard.models import Issue, Project

# the variables of the templates, with what they are
VARIABLES = {
    "author": _("the GitHub name of who opened the pull request"),
    "title": _("the title of the pull request"),
    "number": _("the number of the pull request"),
    "url": _("the address of the pull request on GitHub"),
    "repository": _("the name of the repository"),
    "full_name": _("the account and the name of the repository"),
    "owner": _("the account of the repository"),
    "project": _("the name of the project"),
    "step": _("the name of the step"),
}
VARIABLE = re.compile(r"\{([a-z_]+)\}")
# the characters that make Markdown, escaped in values with a backslash
MARKDOWN = re.compile(r"([\\`*_{}\[\]()#+\-.!|<>~])")


def escape(value: str) -> str:
    r"""A value as text in Markdown: no links, emphasis or HTML of its own.

    Parameters:
        value: The value, such as the title of a pull request.

    Returns:
        The value with the characters of Markdown escaped, on one line.

    Examples:
        >>> escape("[click](https://evil.example) *now*")
        '\\[click\\]\\(https://evil\\.example\\) \\*now\\*'
    """
    return MARKDOWN.sub(r"\\\1", " ".join(str(value).split()))


def expand(template: str, values: dict[str, str]) -> str:
    r"""The template with its variables replaced by their values, escaped for Markdown.

    Parameters:
        template: Such as ``Thanks, @{author}!``.
        values: The values of the variables; a variable without one stays as it is.

    Returns:
        The Markdown.

    Examples:
        >>> expand("Thanks, @{author}! {unknown} {{author}}", {"author": "octo_cat"})
        'Thanks, @octo\\_cat! {unknown} {octo\\_cat}'
    """

    def replace(match: re.Match) -> str:
        name = match[1]
        if name in VARIABLES and name in values:
            return escape(values[name])
        return match[0]

    return VARIABLE.sub(replace, template or "")


def values_of(issue: Issue, project: Project, step: str = "") -> dict[str, str]:
    """The values of the variables for a pull request.

    Parameters:
        issue: The pull request.
        project: The project.
        step: The name of the step.

    Returns:
        The values by the names of the variables.
    """
    repository = issue.repository
    return {
        "author": issue.author.login if issue.author else "",
        "title": issue.title,
        "number": str(issue.number),
        "url": issue.url,
        "repository": repository.name,
        "full_name": repository.full_name,
        "owner": repository.owner,
        "project": project.name,
        "step": step,
    }


def example(project: Project, step: str = "") -> dict[str, str]:
    """Values of the variables for the preview of a template, without a pull request.

    Parameters:
        project: The project.
        step: The name of the step.

    Returns:
        The values by the names of the variables.
    """
    repository = project.repositories.first()
    full_name = repository.full_name if repository else "octocat/hello-world"
    owner, name = full_name.split("/", 1)
    return {
        "author": "octocat",
        "title": "Fix the time zones",
        "number": "42",
        "url": f"https://github.com/{full_name}/pull/42",
        "repository": name,
        "full_name": full_name,
        "owner": owner,
        "project": project.name,
        "step": step,
    }
