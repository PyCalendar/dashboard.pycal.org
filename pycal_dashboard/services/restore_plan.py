"""What restoring a backup changes in a project; only what adds is made without a checkbox.

A backup is compared with the project before anything changes: what it adds, such as a new
filter, is made at once; what deletes or replaces something, such as a filter that was added
after the backup, is made only when the person ticks it. So restoring loses nothing unless the
person says so.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.translation import gettext, ngettext

from pycal_dashboard.errors import BackupInvalid, DashboardError
from pycal_dashboard.models import (
    Issue,
    Profile,
    Project,
    ProjectMember,
    PullRequestFilter,
    PullRequestMessage,
    PullRequestPlace,
    PullRequestStep,
    StepSkip,
)
from pycal_dashboard.step_actions import normalized

from .project_access import ProjectAccess
from .project_editor import ProjectEditor
from .restore_change import RestoreChange

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser

# the fields of the message in a backup, which restoring compares and sets
MESSAGE_FIELDS = ("template", "draft", "listed", "to_listed", "to_new", "to_open", "to_closed")


def clean_name(value: Any) -> str:  # noqa: ANN401 - a value of YAML
    r"""A name of a file, on one line, as the site keeps names.

    Parameters:
        value: The value of the file.

    Returns:
        At most 100 characters.

    Examples:
        >>> clean_name("  Peer\n review ")
        'Peer review'
    """
    return " ".join(str(value or "").split())[:100]


def color(value: Any) -> str:  # noqa: ANN401 - a value of YAML
    """The color of a step from a file: such as ``#bbf7d0``, else none.

    Parameters:
        value: The value of the file.

    Returns:
        The color, or "".

    Examples:
        >>> color("#BBF7D0"), color("red; x"), color(None)
        ('#bbf7d0', '', '')
    """
    text = str(value or "").lower()
    return text if re.fullmatch(r"#[0-9a-f]{6}", text) else ""


def step_fields(entry: dict) -> dict:
    """The fields of a step of a file, as the site keeps them, without its filter.

    Parameters:
        entry: The step of the file.

    Returns:
        ``summary``, ``hidden``, ``color``, ``conditions``, ``actions`` and ``skip_authors``.
    """
    return {
        "summary": str(entry.get("summary") or ""),
        "hidden": bool(entry.get("hidden")),
        "color": color(entry.get("color")),
        "conditions": entry.get("tasks") or {},
        "actions": normalized(entry.get("actions")),
        "skip_authors": [str(name) for name in entry.get("skip_authors") or []][:100],
    }


def message_fields(entry: dict) -> dict:
    """The fields of the message of a file, as the site keeps them.

    Parameters:
        entry: The message of the file.

    Returns:
        The fields of ``MESSAGE_FIELDS``.
    """
    draft = entry.get("draft")
    return {
        "template": str(entry.get("template") or ""),
        "draft": None if draft is None else str(draft),
        "listed": [str(name) for name in entry.get("listed") or []],
        "to_listed": bool(entry.get("to_listed", True)),
        "to_new": bool(entry.get("to_new")),
        "to_open": bool(entry.get("to_open")),
        "to_closed": bool(entry.get("to_closed")),
    }


class RestorePlan:
    """The changes that a backup makes in a project, compared before anything is changed.

    Filters and steps are the same when their names are: those of the file that the project
    lacks are added; those that differ are replaced, and those that the file lacks are deleted,
    each only when the person ticks it. The order of the steps changes only when ticked, too;
    new steps come last. The name, the description, the step labels and the message are
    replaced when ticked; roles are given only when ticked, as they are decisions about
    permissions. The skips of pull requests are added, and the repositories that the project
    lacks are added after it (:attr:`repositories`).
    """

    def __init__(self, project: Project, data: dict):
        """The plan of a backup for a project.

        Parameters:
            project: The project.
            data: The backup, checked by
                :meth:`~pycal_dashboard.services.project_backup.ProjectBackup.read`.

        Raises:
            BackupInvalid: The message or a role is not as a backup keeps it.
        """
        self.project = project
        self.data = data
        self.filters = {clean_name(entry["name"]): entry for entry in data.get("filters") or []}
        self.steps = [
            (clean_name(entry.get("name") or entry["filter"]), entry)
            for entry in data.get("steps") or []
        ]
        message = data.get("message")
        if message is not None and not isinstance(message, dict):
            raise BackupInvalid("message: a mapping with template and the switches")
        members = data.get("members") or []
        if not isinstance(members, list) or not all(
            isinstance(member, dict) and member.get("role") in ProjectMember.RANK
            for member in members
        ):
            raise BackupInvalid("members: a list of handle and role: read, write or owner")
        self.changes = self.compare()

    @property
    def repositories(self) -> list[str]:
        """The repositories of the file that the project lacks, to add as the tab does."""
        known = {repository.full_name.lower() for repository in self.project.repositories.all()}
        return [
            str(name) for name in self.data.get("repositories") or [] if name.lower() not in known
        ]

    def compare(self) -> list[RestoreChange]:
        """The changes, in the order in which they are shown.

        Returns:
            The changes; empty when the project has all of the file already.
        """
        return [
            *self.compare_project(),
            *self.compare_filters(),
            *self.compare_steps(),
            *self.compare_message(),
            *self.compare_skips(),
            *self.compare_members(),
            *(
                [
                    RestoreChange(
                        "repositories",
                        gettext("Add the repositories %(names)s")
                        % {"names": ", ".join(self.repositories)},
                    )
                ]
                if self.repositories
                else []
            ),
        ]

    def compare_project(self) -> list[RestoreChange]:
        """The name, the description and the step labels of the project.

        Returns:
            The changes of those that differ, each to tick.
        """
        project, entry = self.project, self.data["project"]
        changes = []
        name = clean_name(entry["name"])
        if name != project.name:
            text = gettext("Rename the project from “%(old)s” to “%(new)s”")
            changes.append(
                RestoreChange("name", text % {"old": project.name, "new": name}, confirm=True)
            )
        if "description" in entry and str(entry["description"] or "") != project.description:
            text = gettext("Replace the description of the project with that of the backup")
            changes.append(RestoreChange("description", text, confirm=True))
        labels = entry.get("step_labels")
        if labels in Project.LABEL_MODES and labels != project.step_labels:
            text = (
                gettext("Switch the step labels on")
                if labels == Project.LABELS_SYNC
                else gettext("Switch the step labels off: their labels are deleted on GitHub")
            )
            changes.append(RestoreChange("step_labels", text, confirm=True))
        return changes

    def compare_filters(self) -> list[RestoreChange]:
        """The filters: added, replaced or deleted.

        Returns:
            The changes.
        """
        current = {saved.name: saved for saved in self.project.filters.all()}
        steps = {step.filter_id: step for step in self.project.steps.all()}
        changes = []
        for name, entry in self.filters.items():
            saved = current.get(name)
            columns = [str(value) for value in entry.get("columns") or []]
            description = str(entry.get("description") or "")
            if saved is None:
                text = gettext("Add the filter “%(name)s”") % {"name": name}
                changes.append(RestoreChange(f"filter-add:{name}", text))
            elif (saved.description, saved.columns) != (description, columns):
                text = gettext("Replace the filter “%(name)s” with that of the backup")
                changes.append(
                    RestoreChange(f"filter-replace:{name}", text % {"name": name}, confirm=True)
                )
        for name, saved in current.items():
            if name in self.filters:
                continue
            step = steps.get(saved.pk)
            text = (
                gettext(
                    "Delete the filter “%(name)s” and its step “%(step)s”, added after the backup"
                )
                if step
                else gettext("Delete the filter “%(name)s”, added after the backup")
            ) % {"name": name, "step": step.name if step else ""}
            changes.append(RestoreChange(f"filter-delete:{name}", text, confirm=True))
        return changes

    def compare_steps(self) -> list[RestoreChange]:
        """The steps: added, replaced, deleted, and their order.

        Returns:
            The changes.
        """
        current = list(self.project.steps.select_related("filter"))
        by_name = {step.name: step for step in current}
        changes = []
        for name, entry in self.steps:
            step = by_name.get(name)
            if step is None:
                text = gettext("Add the step “%(name)s”") % {"name": name}
                changes.append(RestoreChange(f"step-add:{name}", text))
                continue
            fields = step_fields(entry)
            now = {field: getattr(step, field) for field in fields}
            now["actions"] = normalized(step.actions)
            if now != fields or step.filter.name != clean_name(entry["filter"]):
                text = gettext("Replace the step “%(name)s” with that of the backup")
                changes.append(
                    RestoreChange(f"step-replace:{name}", text % {"name": name}, confirm=True)
                )
        names = {name for name, _entry in self.steps}
        for step in current:
            if step.name not in names and step.filter.name in self.filters:
                text = gettext("Delete the step “%(name)s”, added after the backup")
                changes.append(
                    RestoreChange(f"step-delete:{step.name}", text % {"name": step.name}, True)
                )
        wanted = [name for name, _entry in self.steps if name in by_name]
        if [step.name for step in current if step.name in names] != wanted:
            text = gettext("Order the steps as in the backup")
            changes.append(RestoreChange("step-order", text, confirm=True))
        return changes

    def compare_message(self) -> list[RestoreChange]:
        """The message of the tab PR Sync: added, or replaced when it differs.

        Returns:
            The change, or none.
        """
        entry = self.data.get("message")
        if entry is None:
            return []
        message = PullRequestMessage.objects.filter(project=self.project).first()
        if message is None:
            return [RestoreChange("message", gettext("Add the message of PR Sync"))]
        fields = message_fields(entry)
        if "draft" not in entry:  # a backup of before the drafts: the draft stays
            fields["draft"] = message.draft
        if {field: getattr(message, field) for field in fields} == fields:
            return []
        text = gettext("Replace the message of PR Sync and its synchronization")
        return [RestoreChange("message", text, confirm=True)]

    def skips(self) -> list[tuple[str, Issue, Any, dict]]:
        """The skips of the file that the project lacks and whose pull requests it knows.

        Returns:
            The name of the step, the pull request, the profile of who skipped it or None,
            and the skip of the file, with its ``reason`` and when it was ``created``.
        """
        known = set(
            StepSkip.objects.filter(step__project=self.project).values_list(
                "step__name", "issue__repository__full_name", "issue__number"
            )
        )
        found = []
        for name, entry in self.steps:
            for skip in entry.get("skips") or []:
                if not isinstance(skip, dict):
                    raise BackupInvalid(f"step {name}: skips: a list of mappings")
                repository, number = str(skip.get("repository") or ""), skip.get("number")
                if (name, repository, number) in known:
                    continue
                issue = Issue.objects.filter(
                    repository__in=self.project.repositories.all(),
                    repository__full_name__iexact=repository,
                    number=number,
                ).first()
                if issue is not None:
                    by = Profile.with_github_name(str(skip.get("by") or ""))
                    found.append((name, issue, by, skip))
        return found

    def compare_skips(self) -> list[RestoreChange]:
        """The skips of steps for pull requests that the project lacks.

        Returns:
            One change that adds them, or none.
        """
        count = len(self.skips())
        if not count:
            return []
        text = ngettext(
            "Add %(count)s skip of a step for a pull request",
            "Add %(count)s skips of steps for pull requests",
            count,
        ) % {"count": count}
        return [RestoreChange("skips", text)]

    def compare_members(self) -> list[RestoreChange]:
        """The roles of the file that differ: to tick, as they decide permissions.

        Returns:
            The changes, and a note for each person who never signed in.
        """
        current = {
            member.user_id: member.role
            for member in ProjectMember.objects.filter(project=self.project)
        }
        changes = []
        for entry in self.data.get("members") or []:
            handle, role = str(entry.get("handle") or "").removeprefix("@"), entry["role"]
            profile = Profile.with_github_name(handle)
            if profile is None:
                text = gettext("@%(handle)s never signed in: no role") % {"handle": handle}
                changes.append(RestoreChange(f"member:{handle}", text, note=True))
            elif current.get(profile.user_id) != role:
                text = gettext("Give @%(handle)s the role %(role)s") % {
                    "handle": handle,
                    "role": role,
                }
                changes.append(RestoreChange(f"member:{handle}:{role}", text, confirm=True))
        return changes

    def apply(self, confirmed: set[str], user: AbstractBaseUser) -> list[str]:
        """Make the changes that only add, and those that the person ticked.

        Parameters:
            confirmed: The keys of the ticked changes; others that delete or replace stay.
            user: The owner who restores.

        Returns:
            What could not be made, for the person.
        """
        keys = {
            change.key
            for change in self.changes
            if not change.note and (not change.confirm or change.key in confirmed)
        }
        notes: list[str] = []
        with transaction.atomic():
            self.apply_project(keys)
            changed = self.apply_deletions(keys)
            self.apply_filters(keys)
            changed |= self.apply_steps(keys, notes)
            if "message" in keys:
                self.apply_message()
            if "skips" in keys:
                self.apply_skips()
            if changed:  # the next update only records where they are: no label is written
                PullRequestPlace.objects.filter(project=self.project).delete()
        self.apply_members(keys, user, notes)
        return notes

    def apply_project(self, keys: set[str]) -> None:
        """Set the name, the description and the step labels, if ticked.

        Parameters:
            keys: The changes to make.
        """
        project, entry = self.project, self.data["project"]
        if not keys & {"name", "description", "step_labels"}:
            return
        if "name" in keys:
            project.name = clean_name(entry["name"])
        if "description" in keys:
            project.description = str(entry.get("description") or "")
        if "step_labels" in keys:
            project.step_labels = entry["step_labels"]
        project.save(update_fields=["name", "description", "step_labels", "updated"])

    def apply_deletions(self, keys: set[str]) -> bool:
        """Delete the ticked steps and filters, with the step of a filter.

        Parameters:
            keys: The changes to make.

        Returns:
            Whether a step was deleted.
        """
        names = {key.split(":", 1)[1] for key in keys if key.startswith("step-delete:")}
        steps = self.project.steps.filter(name__in=names)
        changed = steps.exists()
        steps.delete()
        names = {key.split(":", 1)[1] for key in keys if key.startswith("filter-delete:")}
        filters = self.project.filters.filter(name__in=names)
        changed |= PullRequestStep.objects.filter(filter__in=filters).exists()
        filters.delete()
        return changed

    def apply_filters(self, keys: set[str]) -> None:
        """Add the filters of the file, and replace those ticked.

        Parameters:
            keys: The changes to make.
        """
        for name, entry in self.filters.items():
            fields = {
                "description": str(entry.get("description") or ""),
                "columns": [str(value) for value in entry.get("columns") or []],
            }
            if f"filter-add:{name}" in keys:
                PullRequestFilter.objects.create(project=self.project, name=name, **fields)
            elif f"filter-replace:{name}" in keys:
                self.project.filters.filter(name=name).update(**fields, updated=timezone.now())

    def apply_steps(self, keys: set[str], notes: list[str]) -> bool:
        """Add the steps of the file, replace those ticked, and order them if ticked.

        Parameters:
            keys: The changes to make.
            notes: What could not be made, which this adds to.

        Returns:
            Whether a step was added, replaced or moved.
        """
        changed = False
        filters = {saved.name: saved for saved in self.project.filters.all()}
        for name, entry in self.steps:
            add, replace = f"step-add:{name}" in keys, f"step-replace:{name}" in keys
            if not (add or replace):
                continue
            saved = filters[clean_name(entry["filter"])]
            other = PullRequestStep.objects.filter(filter=saved).exclude(
                project=self.project, name=name
            )
            if other.exists():  # a filter has one step at most
                text = gettext(
                    "The step “%(name)s” is not restored: its filter “%(filter)s” is that of "
                    "the step “%(other)s”."
                )
                notes.append(
                    text % {"name": name, "filter": saved.name, "other": other.first().name}
                )
                continue
            fields = {**step_fields(entry), "filter": saved}
            if add:
                last = self.project.steps.aggregate(last=Max("position"))["last"]
                PullRequestStep.objects.create(
                    project=self.project,
                    name=name,
                    position=0 if last is None else last + 1,
                    **fields,
                )
            else:
                self.project.steps.filter(name=name).update(**fields, updated=timezone.now())
            changed = True
        steps = list(self.project.steps.order_by("position", "pk"))
        if "step-order" in keys:
            order = {name: index for index, (name, _entry) in enumerate(self.steps)}
            steps.sort(key=lambda step: order.get(step.name, len(order)))
            changed = True
        for position, step in enumerate(steps):  # without gaps
            if step.position != position:
                PullRequestStep.objects.filter(pk=step.pk).update(position=position)
        return changed

    def apply_message(self) -> None:
        """Set the message of the tab PR Sync; new pull requests are those from now on."""
        entry = self.data["message"]
        fields = message_fields(entry)
        if "draft" not in entry:  # a backup of before the drafts: the draft stays
            del fields["draft"]
        fields["new_since"] = timezone.now() if fields["to_new"] else None
        PullRequestMessage.objects.update_or_create(project=self.project, defaults=fields)

    def apply_skips(self) -> None:
        """Add the skips of the file that the project lacks."""
        steps = {step.name: step for step in self.project.steps.all()}
        for name, issue, by, entry in self.skips():
            if name not in steps:
                continue
            skip, made = StepSkip.objects.get_or_create(
                step=steps[name],
                issue=issue,
                defaults={
                    "user": by.user if by else None,
                    "reason": str(entry.get("reason") or ""),
                },
            )
            try:
                created = parse_datetime(str(entry.get("created") or ""))
            except ValueError:  # such as a 31st of February
                created = None
            if made and created:  # when it was skipped, not restored
                StepSkip.objects.filter(pk=skip.pk).update(created=created)

    def apply_members(self, keys: set[str], user: AbstractBaseUser, notes: list[str]) -> None:
        """Give the ticked roles, as an owner shares the project.

        Parameters:
            keys: The changes to make.
            user: The owner who restores.
            notes: What could not be made, which this adds to.
        """
        editor = ProjectEditor(ProjectAccess(self.project, user))
        for key in sorted(keys):
            if not key.startswith("member:"):
                continue
            _member, handle, role = key.split(":", 2)
            try:
                editor.share(handle, role)
            except DashboardError as error:
                notes.append(f"@{handle}: {error.title}")
