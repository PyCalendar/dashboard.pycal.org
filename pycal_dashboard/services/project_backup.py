"""The backup of a project as a file of YAML: all that people decided about it.

Its settings, repositories, filters, steps with the skips of pull requests, message and
roles. Restoring compares it with the project first (:class:`~.restore_plan.RestorePlan`).
The file is sorted inside, so that two backups or snapshots compare line by line (``diff``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.utils import timezone

from pycal_dashboard.conditions.group.column import Column
from pycal_dashboard.errors import BackupInvalid, BackupVersionUnknown, DashboardError
from pycal_dashboard.import_guard import IMPORT_GUARD
from pycal_dashboard.models import CheckSkip, ProjectMember, PullRequestMessage, StepSkip
from pycal_dashboard.step_actions import normalized

if TYPE_CHECKING:
    from pycal_dashboard.models import Project

# the version of the format; raise it with every change that older sites cannot read
VERSION = 1
MAX_SIZE = 1_000_000  # bytes of a file to restore


class ProjectBackup:
    """Export a project as YAML, and restore a project from such a file.

    The file has ``dashboard_backup``, the version of its format, ``documentation``, the
    address of the description of the format, the ``project`` with its name, description and
    step labels, its ``repositories``, its ``filters``, its ``steps`` with the skips of pull
    requests, its ``message`` with the edited one, and the ``members`` with their roles.
    ``tests/test_backup.py`` checks that every field that people decide is in it. Restoring
    is :class:`~pycal_dashboard.services.restore_plan.RestorePlan`.

    What has no order of its own is sorted, so that the same project always gives the same
    file: the repositories, filters, members, skips, GitHub handles, numbers of pull requests,
    labels and the keys of the tasks. The steps keep their order from left to right, and the
    columns of a filter theirs, as both mean something.
    """

    def __init__(self, project: Project):
        """The backup of a project.

        Parameters:
            project: The project.
        """
        self.project = project

    @staticmethod
    def documentation() -> str:
        """The address of the description of the format."""
        return f"{settings.DOCS_URL.rstrip('/')}/reference/backup.html"

    @staticmethod
    def handles(names: list | None) -> list[str]:
        """GitHub handles as the file keeps them: sorted, whatever the case.

        Parameters:
            names: The handles, such as the authors whose pull requests skip a step.

        Returns:
            The handles, sorted.

        Examples:
            >>> ProjectBackup.handles(["octocat", "Monalisa", "bob"])
            ['bob', 'Monalisa', 'octocat']
        """
        return sorted((str(name) for name in names or []), key=lambda name: (name.lower(), name))

    @staticmethod
    def listed(names: list | None) -> list[str]:
        """Numbers of pull requests as the file keeps them: by repository, then by number.

        Parameters:
            names: Such as ``42`` and ``collective/icalendar#7``.

        Returns:
            The numbers alone first, then those with their repository.

        Examples:
            >>> ProjectBackup.listed(["100", "a/b#3", "9"])
            ['9', '100', 'a/b#3']
        """

        def key(name: str) -> tuple:
            repository, _hash, number = name.rpartition("#")
            return (repository.lower(), int(number) if number.isdigit() else 0, name)

        return sorted((str(name) for name in names or []), key=key)

    @staticmethod
    def actions(actions: dict | list | None) -> dict[str, dict[str, list[str]]]:
        """The actions of a step as the file keeps them: the labels of each sorted.

        Parameters:
            actions: As the step keeps them.

        Returns:
            For each trigger, the labels to ``add`` and to ``remove``.

        Examples:
            >>> ProjectBackup.actions({"enter": {"add": ["b", "A"]}})["enter"]["add"]
            ['A', 'b']
        """
        return {
            trigger: {kind: ProjectBackup.handles(labels) for kind, labels in kinds.items()}
            for trigger, kinds in normalized(actions).items()
        }

    @staticmethod
    def ordered(value: Any) -> Any:  # noqa: ANN401 - a value of JSON
        """A value of JSON with the keys of each mapping sorted, such as the tasks of a step.

        Parameters:
            value: The value.

        Returns:
            The same value, its mappings sorted by their keys.

        Examples:
            >>> ProjectBackup.ordered({"b": 1, "a": {"d": 2, "c": 3}})
            {'a': {'c': 3, 'd': 2}, 'b': 1}
        """
        if isinstance(value, dict):
            return {key: ProjectBackup.ordered(value[key]) for key in sorted(value, key=str)}
        if isinstance(value, list):
            return [ProjectBackup.ordered(item) for item in value]
        return value

    def data(self) -> dict:
        """The project as the file keeps it.

        Returns:
            The data, in the order of the file.
        """
        project = self.project
        return {
            "dashboard_backup": VERSION,
            "documentation": self.documentation(),
            "exported": timezone.now().isoformat(timespec="seconds"),
            "site": settings.SITE_URL,
            "project": {
                "name": project.name,
                "slug": project.slug,
                "description": project.description,
                "public": project.public,
                "step_labels": project.step_labels,
            },
            "repositories": sorted(r.full_name for r in project.repositories.all()),
            "filters": [  # the columns keep their order: that of the table
                {"name": saved.name, "description": saved.description, "columns": saved.columns}
                for saved in sorted(project.filters.all(), key=lambda f: (f.name.lower(), f.name))
            ],
            "steps": [
                {
                    "name": step.name,
                    "filter": step.filter.name,
                    "summary": step.summary,
                    "hidden": step.hidden,
                    "color": step.color,
                    "tasks": self.ordered(step.conditions or {}),
                    "actions": self.actions(step.actions),
                    "skip_authors": self.handles(step.skip_authors),
                    "skips": self.skips(step.pk),
                }
                for step in project.steps.select_related("filter")  # from left to right
            ],
            "message": self.message(),
            "members": sorted(
                (
                    {"handle": member.user.profile.github_name, "role": member.role}
                    for member in ProjectMember.objects.filter(project=project).select_related(
                        "user__profile"
                    )
                    if getattr(member.user, "profile", None) and member.user.profile.github_name
                ),
                key=lambda member: (member["handle"].lower(), member["handle"]),
            ),
        }

    @staticmethod
    def skips(step: int) -> list[dict]:
        """The skips of a step and of its quality checks for pull requests, as the file keeps them.

        Parameters:
            step: The id of the step.

        Returns:
            Each with the ``repository`` and ``number`` of the pull request, the ``condition``
            of the quality check (only for the skip of a quality check), ``by``, the GitHub
            handle of who skipped it, the ``reason`` and when it was ``created``; sorted by the
            repository, the number and the condition, the skip of the step first.
        """
        found = []
        for model in (StepSkip, CheckSkip):
            skips = model.objects.filter(step=step).select_related(
                "issue__repository", "user__profile"
            )
            for skip in skips:
                entry = {
                    "repository": skip.issue.repository.full_name,
                    "number": skip.issue.number,
                    "by": getattr(getattr(skip.user, "profile", None), "github_name", "") or "",
                    "reason": skip.reason,
                    "created": skip.created.isoformat(timespec="seconds"),
                }
                if model is CheckSkip:
                    entry = {**entry, "condition": skip.condition}
                found.append(entry)
        return sorted(
            found,
            key=lambda skip: (
                skip["repository"].lower(),
                skip["number"],
                skip.get("condition", ""),
                skip["created"],
            ),
        )

    def message(self) -> dict | None:
        """The message of the tab PR Sync, as the file keeps it; None without one."""
        message = PullRequestMessage.objects.filter(project=self.project).first()
        if message is None:
            return None
        return {
            "template": message.template,
            "draft": message.draft,
            "listed": self.listed(message.listed),
            "to_listed": message.to_listed,
            "authors": self.handles(message.authors),
            "to_authors": message.to_authors,
            "signup_text": message.signup_text,
            "to_new": message.to_new,
            "to_open": message.to_open,
            "to_closed": message.to_closed,
        }

    def export(self) -> str:
        """The backup as YAML, with a comment that says what it is.

        Returns:
            The text of the file.
        """
        with IMPORT_GUARD:  # see import_guard.py
            import yaml

        head = (
            f"# A backup of the project {self.project.name} of {settings.SITE_URL}.\n"
            f"# The format, version {VERSION}: {self.documentation()}\n"
        )
        body = yaml.safe_dump(
            self.data(), allow_unicode=True, sort_keys=False, default_flow_style=False, width=100
        )
        return head + body

    @staticmethod
    def read(text: str) -> dict:
        """The data of a file, checked, before anything is changed.

        Parameters:
            text: The YAML.

        Returns:
            The data.

        Raises:
            BackupInvalid: It is no YAML, too large, or a part is missing or wrong.
            BackupVersionUnknown: Its version is not that of this site.
        """
        with IMPORT_GUARD:  # see import_guard.py
            import yaml

        if len(text) > MAX_SIZE:
            raise BackupInvalid(f"larger than {MAX_SIZE} bytes")
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as error:
            raise BackupInvalid(f"not YAML: {error}") from None
        if not isinstance(data, dict) or "dashboard_backup" not in data:
            raise BackupInvalid("dashboard_backup is missing: no backup of a project")
        if data["dashboard_backup"] != VERSION:
            raise BackupVersionUnknown(str(data["dashboard_backup"]))
        project = data.get("project") or {}
        if not isinstance(project, dict) or not str(project.get("name") or "").strip():
            raise BackupInvalid("project: the name is missing")
        repositories = data.get("repositories") or []
        if not isinstance(repositories, list) or not all(isinstance(r, str) for r in repositories):
            raise BackupInvalid("repositories: a list of names such as collective/icalendar")
        names = set()
        for saved in data.get("filters") or []:
            name = " ".join(str(_get(saved, "name", "filters")).split())[:100]
            if not name or name in names:
                raise BackupInvalid(f"filters: a name is missing or twice: {name!r}")
            names.add(name)
            for value in _get(saved, "columns", f"filter {name}") or []:
                try:
                    Column.decode(str(value))
                except DashboardError as error:
                    raise BackupInvalid(f"filter {name}: {value}: {error.title}") from None
        for step in data.get("steps") or []:
            if _get(step, "filter", "steps") not in names:
                raise BackupInvalid(f"step {step.get('name')!r}: no filter {step['filter']!r}")
        return data


def _get(item: Any, key: str, where: str) -> Any:  # noqa: ANN401 - a value of YAML
    """A value of a mapping of the file.

    Parameters:
        item: The mapping, such as a filter.
        key: The key.
        where: Where it is, for the error.

    Returns:
        The value.

    Raises:
        BackupInvalid: It is no mapping, or the key is missing.
    """
    if not isinstance(item, dict) or key not in item:
        raise BackupInvalid(f"{where}: {key} is missing")
    return item[key]
