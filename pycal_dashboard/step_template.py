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
from urllib.parse import urlencode

from django.conf import settings
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from pycal_dashboard.models import Issue, Project, PullRequestStep

# the anchor of the merge box on the page of a pull request on GitHub, for people who signed in:
# its checks, its conflicts and the button to merge it, at the end of the conversation
MERGE_BOX = "#partial-pull-merging"
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
            "pr_merge_box": (
                _("the address of the merge box of the pull request on GitHub: checks and merging"),
                "https://github.com/collective/icalendar/pull/42" + MERGE_BOX,
            ),
        },
    ),
    "badge": (
        _("Badge"),
        {
            "pr_badge": (
                _("the badge of the pull request, linked to its page with its steps"),
                "[![](https://dashboard.pycal.org/projects/icalendar/pull/42/badge.svg?repository=collective%2Ficalendar)]"
                "(https://dashboard.pycal.org/projects/icalendar/pull/42/?repository=collective%2Ficalendar)",
            ),
            "pr_badge_url": (
                _("the address of the badge of the pull request: its step and tasks done"),
                "https://dashboard.pycal.org/projects/icalendar/pull/42/badge.svg?repository=collective%2Ficalendar",
            ),
            "pr_steps_url": (
                _("the address of the page of the pull request with its steps on %(site_name)s"),
                "https://dashboard.pycal.org/projects/icalendar/pull/42/?repository=collective%2Ficalendar",
            ),
        },
    ),
    "author": (
        _("Author"),
        {
            "author_mention": (_("who opened the pull request, mentioned"), "@niccokunzmann"),
            "author_name": (
                _("the GitHub name of who opened it, else their GitHub handle"),
                "Nicco Kunzmann",
            ),
            "author_handle": (_("the GitHub handle of who opened it"), "niccokunzmann"),
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
    "message": (
        _("Message"),
        {
            "step_description": (
                _("the summary of the step the pull request is in, in Markdown"),
                "Thanks, @niccokunzmann! A person reviews it soon.",
            ),
            "tasks_all": (
                _("all tasks of the step, those to do first, those done at the bottom"),
                "- [ ] Solve the conflict\n- [x] Review it",
            ),
            "tasks_todo": (
                _("the tasks to do; a sentence when there is nothing to do"),
                "- [ ] Solve the conflict",
            ),
            "tasks_done": (
                _("the tasks done; a sentence when nothing is done"),
                "- [x] Review it",
            ),
        },
    ),
}
# the groups of the templates of steps: the message has more, which steps cannot fill
STEP_GROUPS = {key: group for key, group in GROUPS.items() if key != "message"}
# every variable with what it is, in the order of the groups
# the variables whose values are Markdown that the site makes of its own addresses: not escaped
# and the description and tasks of a step in the message, written by the writers of the project
MARKDOWN_VALUES = {"pr_badge", "step_description", "tasks_all", "tasks_todo", "tasks_done"}
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
            return values[name] if name in MARKDOWN_VALUES else escape(values[name])
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
        "pr_merge_box": issue.url + MERGE_BOX,
        **pull_addresses(project, issue.number, repository.full_name),
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
    return (
        values
        | {"project_name": project.name, **pull_addresses(project, 42, "collective/icalendar")}
        | step_values(step)
    )


def steps_url(project: Project, number: int, repository: str = "", page: str = "") -> str:
    """The address of the page of a pull request with its steps, or of its badge, on this site.

    Parameters:
        project: The project.
        number: The number of the pull request.
        repository: Its repository, such as ``collective/icalendar``: always named in the
            address, so that it stays the same when the project gets another repository with
            a pull request of the same number.
        page: ``badge.svg`` for the badge; "" for the page.

    Returns:
        Such as ``https://dashboard.pycal.org/projects/icalendar/pull/42/``.
    """
    address = f"{settings.SITE_URL}{project.path(f'pull/{number}/{page}')}"
    if repository:
        address += "?" + urlencode({"repository": repository})
    return address


def pull_addresses(project: Project, number: int, repository: str = "") -> dict[str, str]:
    """The variables of the addresses of a pull request on this site, and its badge.

    Parameters:
        project: The project.
        number: The number of the pull request.
        repository: Its repository, see :func:`steps_url`.

    Returns:
        ``pr_steps_url``, ``pr_badge_url`` and ``pr_badge``, the badge in Markdown linked to
        the page: made of the addresses of the site only, so it is not escaped.
    """
    page = steps_url(project, number, repository)
    badge = steps_url(project, number, repository, "badge.svg")
    return {"pr_steps_url": page, "pr_badge_url": badge, "pr_badge": f"[![]({badge})]({page})"}
