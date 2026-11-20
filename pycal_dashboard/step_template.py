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
    from pycal_dashboard.models import Issue, Project, PullRequestStep

# the variables of the templates in their groups, by an id: the title of the group, and each
# variable with what it is and an example
GROUPS = {
    "pr": (
        _("Pull request"),
        {
            "pr_title": (_("the title of the pull request"), "Fix the time zones"),
            "pr_number": (_("the number of the pull request"), "42"),
            "pr_url": (
                _("the address of the pull request on GitHub"),
                "https://github.com/collective/icalendar/pull/42",
            ),
        },
    ),
    "author": (
        _("Author"),
        {
            "author_mention": (_("who opened the pull request, mentioned"), "@niccokunzmann"),
            "author_name": (
                _("the name of who opened it, else the GitHub name"),
                "Nicco Kunzmann",
            ),
            "author_handle": (_("the GitHub name of who opened it"), "niccokunzmann"),
        },
    ),
    "repository": (
        _("Repository"),
        {
            "repository_name": (_("the name of the repository"), "icalendar"),
            "repository_full_name": (
                _("the account and the name of the repository"),
                "collective/icalendar",
            ),
            "repository_owner": (_("the account of the repository"), "collective"),
        },
    ),
    "project": (_("Project"), {"project_name": (_("the name of the project"), "iCalendar")}),
    "step": (
        _("Step"),
        {
            "step_name": (_("the name of the step"), "Review"),
            "step_number": (_("the place of the step, counted from 1"), "2"),
            "step_id": (_("the id of the step"), "7"),
        },
    ),
}
# every variable with what it is, in the order of the groups
VARIABLES = {
    name: about[0] for _title, members in GROUPS.values() for name, about in members.items()
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
        template: Such as ``Thanks, {author_mention}!``.
        values: The values of the variables; a variable without one stays as it is.

    Returns:
        The Markdown.

    Examples:
        >>> expand("Thanks, {author_mention}! {unknown}", {"author_mention": "@octo_cat"})
        'Thanks, @octo\\_cat! {unknown}'
    """

    def replace(match: re.Match) -> str:
        name = match[1]
        if name in VARIABLES and name in values:
            return escape(values[name])
        return match[0]

    return VARIABLE.sub(replace, template or "")


def values_of(issue: Issue, project: Project, step: PullRequestStep | None = None) -> dict:
    """The values of the variables for a pull request.

    Parameters:
        issue: The pull request.
        project: The project.
        step: The step, if the template is of one.

    Returns:
        The values by the names of the variables.
    """
    repository = issue.repository
    author = issue.author
    login = author.login if author else ""
    values = {
        "pr_title": issue.title,
        "pr_number": str(issue.number),
        "pr_url": issue.url,
        "author_mention": f"@{login}" if login else "",
        "author_name": (author.name or login) if author else "",
        "author_handle": login,
        "repository_name": repository.name,
        "repository_full_name": repository.full_name,
        "repository_owner": repository.owner,
        "project_name": project.name,
    }
    return values | step_values(step)


def step_values(step: PullRequestStep | None) -> dict[str, str]:
    """The values of the variables of a step.

    Parameters:
        step: The step; None for none.

    Returns:
        Its name, number (its place, from 1) and id.
    """
    if step is None:
        return {}
    number = list(step.project.steps.values_list("pk", flat=True)).index(step.pk) + 1
    return {"step_name": step.name, "step_number": str(number), "step_id": str(step.pk)}


def example(project: Project, step: PullRequestStep | None = None) -> dict[str, str]:
    """Values of the variables for the preview of a template, without a pull request.

    Parameters:
        project: The project.
        step: The step, if the template is of one.

    Returns:
        The examples of the variables, with the project and the step as they are.
    """
    values = {
        name: about[1] for _title, members in GROUPS.values() for name, about in members.items()
    }
    return values | {"project_name": project.name} | step_values(step)
