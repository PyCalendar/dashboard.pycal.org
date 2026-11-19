"""The permissions and events of the GitHub App as GitHub names and describes them to people.

The settings of a GitHub App on GitHub group permissions by what they give access to, and name
each in English with a sentence; the site shows the same, so that people find them there. The
text of that page is ``permission_names.txt`` next to this module: the reference of the names
and sentences, which ``tests/test_permission_names.py`` compares. The
names are GitHub's and stay English; the groups, levels and sentences are translated.
"""

from django.utils.translation import gettext_lazy as _

# the groups of permissions as the settings of the app on GitHub show them, in their order
GROUPS = {
    "repository": _("Repository permissions"),
    "organization": _("Organization permissions"),
    "account": _("Account permissions"),
    "enterprise": _("Enterprise permissions"),
    "events": _("Subscribe to events"),
}
# the levels of a permission as GitHub names them
LEVELS = {"read": _("Read-only"), "write": _("Read and write"), "admin": _("Admin")}
# each permission of the API: its group, its name on GitHub and GitHub's sentence
PERMISSIONS = {
    "metadata": (
        "repository",
        "Metadata",
        _("Search repositories, list collaborators, and access repository metadata."),
    ),
    "issues": (
        "repository",
        "Issues",
        _("Issues and related comments, assignees, labels, and milestones."),
    ),
    "pull_requests": (
        "repository",
        "Pull requests",
        _("Pull requests and related comments, assignees, labels, milestones, and merges."),
    ),
    "checks": ("repository", "Checks", _("Checks on code.")),
    "statuses": ("repository", "Commit statuses", _("Commit statuses.")),
    "contents": (
        "repository",
        "Contents",
        _("Repository contents, commits, branches, downloads, releases, and merges."),
    ),
}
# each event of the webhooks: its name on GitHub and GitHub's sentence
EVENTS = {
    "issues": (
        "Issues",
        _("Issue opened, edited, deleted, transferred, closed, reopened, assigned, labeled."),
    ),
    "issue_comment": ("Issue comment", _("Issue comment created, edited, or deleted.")),
    "pull_request": (
        "Pull request",
        _("Pull request opened, edited, closed, labeled, auto merge enabled or disabled."),
    ),
    "pull_request_review": (
        "Pull request review",
        _("Pull request review submitted, edited, or dismissed."),
    ),
    "repository": (
        "Repository",
        _(
            "Repository created, deleted, archived, unarchived, publicized, privatized, "
            "edited, renamed, or transferred."
        ),
    ),
    "public": ("Public", _("Repository changes from private to public.")),
    "label": ("Label", _("Label created, edited, deleted, archived, or unarchived.")),
    "check_run": ("Check run", _("Check run created, requested, rerequested, or completed.")),
    "check_suite": ("Check suite", _("Check suite requested, rerequested, or completed.")),
    "status": ("Status", _("Commit status updated from the API.")),
    "push": ("Push", _("Git push to a repository.")),
}


def grouped(permissions: dict[str, str], events: list[str] | None = None) -> list[dict]:
    """Permissions and events in the groups of GitHub, with their names and sentences.

    Parameters:
        permissions: Permissions by the names of the API, with their level, such as
            ``{"checks": "read"}``.
        events: Events by the names of the API, such as ``["push"]``.

    Returns:
        Each group with its ``title`` and ``items``: ``name``, ``level`` (None for an event)
        and ``description``; in the order of GitHub, empty groups left out. A permission or
        event that the site does not know shows its name of the API.

    Examples:
        >>> [(g["title"], [i["name"] for i in g["items"]]) for g in grouped(
        ...     {"checks": "read"}, ["push"])]
        [('Repository permissions', ['Checks']), ('Subscribe to events', ['Push'])]
    """
    items: dict[str, list[dict]] = {key: [] for key in GROUPS}
    for key, level in permissions.items():
        group, name, description = PERMISSIONS.get(key, ("repository", key, ""))
        items[group].append(
            {"name": name, "level": LEVELS.get(level, level), "description": description}
        )
    for key in events or []:
        name, description = EVENTS.get(key, (key, ""))
        items["events"].append({"name": name, "level": None, "description": description})
    return [
        {"title": GROUPS[key], "items": sorted(found, key=lambda item: item["name"])}
        for key, found in items.items()
        if found
    ]
