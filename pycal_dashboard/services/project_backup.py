"""The backup of a project as a file of YAML: its settings, repositories, filters and steps."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from pycal_dashboard.conditions.group.column import Column
from pycal_dashboard.errors import BackupInvalid, BackupVersionUnknown, DashboardError
from pycal_dashboard.import_guard import IMPORT_GUARD
from pycal_dashboard.models import PullRequestFilter, PullRequestPlace, PullRequestStep
from pycal_dashboard.step_actions import normalized

if TYPE_CHECKING:
    from pycal_dashboard.models import Project

# the version of the format; raise it with every change that older sites cannot read
VERSION = 1
MAX_SIZE = 1_000_000  # bytes of a file to restore


class ProjectBackup:
    """Export a project as YAML, and restore a project from such a file.

    The file has ``dashboard_backup``, the version of its format, ``documentation``, the
    address of the description of the format, the ``project`` with its name and
    description, its ``repositories``, its ``filters`` and its ``steps``. Restoring replaces
    the filters and steps, sets the name and the description, and lists the repositories to
    add; the visibility and the address of the project stay as they are.
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
            },
            "repositories": sorted(r.full_name for r in project.repositories.all()),
            "filters": [
                {"name": saved.name, "description": saved.description, "columns": saved.columns}
                for saved in project.filters.order_by("name")
            ],
            "steps": [
                {
                    "name": step.name,
                    "filter": step.filter.name,
                    "summary": step.summary,
                    "hidden": step.hidden,
                    "color": step.color,
                    "tasks": step.conditions or {},
                    "actions": normalized(step.actions),
                }
                for step in project.steps.select_related("filter")
            ],
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

    def restore(self, data: dict) -> list[str]:
        """Replace the filters and steps, and set the name and the description.

        Where the open pull requests are in the steps is forgotten: the next update only
        records it, so that no label is added or removed for the restored steps.

        Parameters:
            data: The data of :meth:`read`.

        Returns:
            The repositories of the file, for the person to add.
        """
        project = self.project
        with transaction.atomic():
            project.name = " ".join(str(data["project"]["name"]).split())[:100]
            project.description = str(data["project"].get("description") or "")
            project.save(update_fields=["name", "description", "updated"])
            PullRequestPlace.objects.filter(project=project).delete()
            project.steps.all().delete()
            project.filters.all().delete()
            filters = {}
            for saved in data.get("filters") or []:
                name = " ".join(str(saved["name"]).split())[:100]
                filters[name] = PullRequestFilter.objects.create(
                    project=project,
                    name=name,
                    description=str(saved.get("description") or ""),
                    columns=[str(value) for value in saved.get("columns") or []],
                )
            for position, step in enumerate(data.get("steps") or []):
                PullRequestStep.objects.create(
                    project=project,
                    filter=filters[step["filter"]],
                    name=" ".join(str(step.get("name") or step["filter"]).split())[:100],
                    summary=str(step.get("summary") or ""),
                    hidden=bool(step.get("hidden")),
                    color=_color(step.get("color")),
                    conditions=step.get("tasks") or {},
                    actions=normalized(step.get("actions")),
                    position=position,
                )
        return [str(name) for name in data.get("repositories") or []]


def _color(value: Any) -> str:  # noqa: ANN401 - a value of YAML
    """The color of a step from a file: such as ``#bbf7d0``, else none.

    Parameters:
        value: The value of the file.

    Returns:
        The color, or "".

    Examples:
        >>> _color("#BBF7D0"), _color("red; x"), _color(None)
        ('#bbf7d0', '', '')
    """
    text = str(value or "").lower()
    return text if re.fullmatch(r"#[0-9a-f]{6}", text) else ""


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
