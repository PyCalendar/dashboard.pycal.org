"""The message of a project as a comment on its pull requests: which ones, and its text."""

from __future__ import annotations

import hashlib
import logging
import re
from typing import TYPE_CHECKING

from django.db.models import Q
from django.utils.text import capfirst
from django.utils.translation import gettext

from pycal_dashboard.actions import MessageWritten
from pycal_dashboard.import_guard import IMPORT_GUARD
from pycal_dashboard.models import Issue, PullRequestComment, PullRequestMessage
from pycal_dashboard.services.column_results import ColumnResults
from pycal_dashboard.services.progress import PullRequestProgress
from pycal_dashboard.services.step_overrides import StepOverrides
from pycal_dashboard.step_template import expand, values_of

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from pycal_dashboard.models import Project, Repository
    from pycal_dashboard.services.progress import Task

log = logging.getLogger(__name__)
# a pull request by its number, or with its repository: 42, #42, collective/icalendar#42
LISTED = re.compile(r"^(?:([\w.-]+/[\w.-]+))?#?(\d+)$")


class MessageComments:
    """The comments of the message of a project on its pull requests.

    The scope of the message says which pull requests get it: those listed by their numbers,
    the new ones (opened after their switch was switched on), the open ones, and the closed
    and merged ones. After each update of a repository (a receiver of ``repository_updated``),
    :meth:`sync` writes the message on those of its pull requests that lack it and updates
    those whose text changed, with the variables of steps and those of the message.
    """

    def __init__(self, project: Project, repositories: list[Repository] | None = None):
        """The message of a project.

        Parameters:
            project: The project.
            repositories: The repositories the person sees; all of the project by default.
        """
        self.project = project
        self.repositories = (
            list(repositories) if repositories is not None else list(project.repositories.all())
        )
        self.results = ColumnResults(self.repositories)
        self.scope = self.results.scope
        self._overrides: StepOverrides | None = None  # the skips, read when first needed

    def marker(self) -> str:
        """The hidden line that ends every comment of the message: what wrote it."""
        return f"<!-- dashboard.pycal.org: the message of the project {self.project.slug} -->"

    @staticmethod
    def listed(text: str) -> tuple[list[str], list[str]]:
        """The pull requests of the field of numbers, and what is no number of one.

        Parameters:
            text: Such as ``42, #43 collective/icalendar#44``.

        Returns:
            The numbers as kept, such as ``42`` and ``collective/icalendar#44``, and the rest.

        Examples:
            >>> MessageComments.listed("42, #43 collective/icalendar#44 x")
            (['42', '43', 'collective/icalendar#44'], ['x'])
        """
        found, wrong = [], []
        for part in re.split(r"[,\s]+", text.strip()):
            match = LISTED.match(part)
            if not part:
                continue
            if match is None:
                wrong.append(part)
                continue
            name = f"{match[1]}#{match[2]}" if match[1] else match[2]
            if name not in found:
                found.append(name)
        return found, wrong

    def pulls(self, message: PullRequestMessage) -> QuerySet[Issue]:
        """The pull requests in the scope of a message, the newest first.

        Parameters:
            message: The message, also one that is not saved, such as for its preview.

        Returns:
            The query of the pull requests; none when no scope is switched on.
        """
        wanted = Q(pk__in=[])
        if message.to_listed:
            for name in message.listed or []:
                repository, _hash, number = str(name).rpartition("#")
                one = Q(number=int(number))
                if repository:
                    one &= Q(repository__full_name__iexact=repository)
                wanted |= one
        if message.to_open:
            wanted |= Q(state=Issue.OPEN)
        if message.to_new and message.new_since:
            wanted |= Q(created__gte=message.new_since)
        if message.to_closed:
            wanted |= Q(state=Issue.CLOSED)
        return (
            Issue.objects.filter(repository__in=self.repositories, pull_request=True)
            .filter(wanted)
            .order_by("-created", "-pk")
        )

    @staticmethod
    def task_line(task: Task, done: bool) -> str:
        """A task as an item of a list of tasks of GitHub, checked when it is done.

        Its description follows on the next lines, indented by two spaces, so that it belongs
        to the item, after a line break (two spaces after the title); its empty lines stay
        empty.

        Parameters:
            task: The task.
            done: Whether it is done.

        Returns:
            Such as ``- [x] Review it`` and ``  Ask in the chat.`` below it.
        """
        text = " ".join((task.summary or capfirst(str(task.column.sentence))).split())
        lines = [f"- [{'x' if done else ' '}] {text}"]
        description = (task.description or "").strip().splitlines()
        if description:  # two spaces: a line break after the title, not one line with it
            lines[0] += "  "
        for line in description:
            lines.append(f"  {line}".rstrip())
        return "\n".join(lines)

    def values(self, issue: Issue) -> dict[str, str]:
        """The values of the variables for a pull request: those of steps and of the message.

        Parameters:
            issue: The pull request.

        Returns:
            The values by the names of the variables.
        """
        if self._overrides is None:
            self._overrides = StepOverrides(self.project)
        progress = PullRequestProgress(
            issue, self.project, self.scope, self.results, self._overrides
        )
        current = progress.current
        values = {"step_name": "", "step_number": "", "step_id": ""} | values_of(
            issue, self.project, current.step if current else None
        )  # in no step: empty
        tasks = current.tasks if current else []
        todo = [self.task_line(task, False) for task in tasks if task.state == "todo"]
        unknown = [self.task_line(task, False) for task in tasks if task.state == "unknown"]
        done = [self.task_line(task, True) for task in tasks if task.state == "done"]
        summary = expand(current.step.summary, values) if current else ""
        return values | {
            "step_description": summary,
            "tasks_all": "\n".join(todo + unknown + done),
            "tasks_todo": "\n".join(todo) or gettext("Nothing to do."),
            "tasks_done": "\n".join(done) or gettext("Nothing is done yet."),
        }

    def body(self, issue: Issue, template: str) -> str:
        """The text of the comment on a pull request.

        Parameters:
            issue: The pull request.
            template: The template of the message.

        Returns:
            The Markdown, with the hidden line of :meth:`marker` at its end.
        """
        return f"{expand(template, self.values(issue)).strip()}\n\n{self.marker()}\n"

    def sync(self, repository: Repository) -> int:
        """Write or update the message on the pull requests of a repository in its scope.

        A comment whose text would be the same is not written again. Without the GitHub App
        on the repository, nothing is written.

        Parameters:
            repository: The repository that was updated.

        Returns:
            How many comments were written or updated.
        """
        message = PullRequestMessage.objects.filter(project=self.project).first()
        if message is None or not message.template.strip() or not repository.app_installed:
            return 0
        pulls = (
            self.pulls(message)
            .filter(repository=repository)
            .select_related("author", "repository__installation", "pull_state")
            .prefetch_related("labels", "reviews")
        )
        comments = {
            comment.issue_id: comment
            for comment in PullRequestComment.objects.filter(
                project=self.project, issue__repository=repository
            )
        }
        client = None
        written = 0
        for issue in pulls:
            body = self.body(issue, message.template)
            digest = hashlib.sha256(body.encode()).hexdigest()
            comment = comments.get(issue.pk)
            if comment is not None and comment.digest == digest:
                continue
            if client is None:
                with IMPORT_GUARD:  # see import_guard.py
                    from pycal_dashboard.github.installation_token import InstallationToken

                client = InstallationToken.client(repository.installation.github_id)
            try:
                action = MessageWritten(client, issue, body, comment.github_id if comment else None)
                action.run()
            except Exception:  # one pull request does not stop the others
                log.exception("%s: the message was not written", issue)
                continue
            PullRequestComment.objects.update_or_create(
                project=self.project,
                issue=issue,
                defaults={"github_id": action.github_id, "digest": digest},
            )
            written += 1
        return written
