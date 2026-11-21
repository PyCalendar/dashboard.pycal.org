"""What follows an update from GitHub: the receivers of :mod:`pycal_dashboard.update_signals`."""

from __future__ import annotations

import functools
import logging
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from django.dispatch import receiver

from .import_guard import IMPORT_GUARD
from .models import Project
from .update_signals import project_updated, repository_updated

if TYPE_CHECKING:
    from pycal_dashboard.models import Repository

log = logging.getLogger(__name__)
SLOW = 1.0  # seconds: a receiver that takes longer says so in the log


def timed(function: Callable) -> Callable:
    """Log how long a receiver took when it took longer than :data:`SLOW` seconds.

    The work after an update runs in the thread of the updates of the web process: the log
    names what took long, such as on a small server.

    Parameters:
        function: The receiver.

    Returns:
        The receiver, which logs its time.
    """

    @functools.wraps(function)
    def run(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        start = time.perf_counter()
        try:
            return function(*args, **kwargs)
        finally:
            seconds = time.perf_counter() - start
            if seconds > SLOW:
                about = kwargs.get("repository") or kwargs.get("project")
                log.info("%s for %s took %.1f s", function.__name__, about, seconds)

    return run


@receiver(repository_updated)
@timed
def mark_projects(sender: type, repository: Repository, **kwargs: Any):
    """Keep the time of the last update of the projects of a repository.

    A project is as fresh as its oldest repository: ``updated`` is the oldest time a repository
    of it was read, None while one was never read.

    Parameters:
        sender: Who sent the signal.
        repository: The repository that was read.
        **kwargs: More of the signal.
    """
    for project in Project.objects.filter(repositories=repository):
        times = list(project.repositories.values_list("updated", flat=True))
        updated = None if not times or None in times else min(times)
        if updated != project.updated:
            Project.objects.filter(pk=project.pk).update(updated=updated)
            project.updated = updated
            project_updated.send(sender=Project, project=project)


@receiver(repository_updated)
@timed
def sync_status_labels(sender: type, repository: Repository, **kwargs: Any):
    """Keep the step labels in a repository and on its pull requests, or delete them when off.

    See :class:`~pycal_dashboard.services.status_labels.StatusLabels`: before the actions of
    the steps and the messages, which follow the step that a person chose with a label.

    Parameters:
        sender: Who sent the signal.
        repository: The repository that was read.
        **kwargs: More of the signal.
    """
    with IMPORT_GUARD:  # see import_guard.py: what writes to GitHub, only when needed
        from pycal_dashboard.services.status_labels import StatusLabels
    on = Project.objects.filter(repositories=repository, step_labels=Project.LABELS_SYNC)
    labeled = Project.objects.filter(  # off, with labels to delete
        repositories=repository, steps__labels__repository=repository
    )
    for project in (on | labeled).distinct():
        StatusLabels(project).sync(repository)


@receiver(repository_updated)
@timed
def complete_steps(sender: type, repository: Repository, **kwargs: Any):
    """Act on the steps that the open pull requests of a repository completed.

    See :class:`~pycal_dashboard.services.step_completion.StepCompletion`: only projects with
    steps watch where their pull requests are.

    Parameters:
        sender: Who sent the signal.
        repository: The repository that was read.
        **kwargs: More of the signal.
    """
    with IMPORT_GUARD:  # see import_guard.py: what writes to GitHub, only when needed
        from pycal_dashboard.services.step_completion import StepCompletion

    for project in Project.objects.filter(repositories=repository, steps__isnull=False).distinct():
        StepCompletion(project).observe(repository)


@receiver(repository_updated)
@timed
def prepare_results(sender: type, repository: Repository, **kwargs: Any):
    """Evaluate the columns of the saved filters and steps after an update, for fast pages.

    The results are kept in the cache under the new version of the repositories
    (:class:`~pycal_dashboard.services.column_results.ColumnResults`), for the public
    repositories of a project and for all of them, as visitors and collaborators see them.

    Parameters:
        sender: Who sent the signal.
        repository: The repository that was read.
        **kwargs: More of the signal.
    """
    with IMPORT_GUARD:  # see import_guard.py
        from pycal_dashboard.conditions.group.column import Column
        from pycal_dashboard.services.column_results import ColumnResults

    for project in Project.objects.filter(repositories=repository).prefetch_related("filters"):
        values = {value for saved in project.filters.all() for value in saved.columns}
        if not values:
            continue
        everything = list(project.repositories.all())
        public = [found for found in everything if not found.private]
        for repositories in {tuple(everything), tuple(public)}:
            results = ColumnResults(list(repositories), project=project)
            for value in values:
                results.of(Column.decode(value))


@receiver(repository_updated)
@timed
def write_messages(sender: type, repository: Repository, **kwargs: Any):
    """Write or update the message of each project as a comment on the pull requests in scope.

    See :class:`~pycal_dashboard.services.message_comments.MessageComments`: a message changes
    with its template and with the values of its variables, which an update can change.

    Parameters:
        sender: Who sent the signal.
        repository: The repository that was read.
        **kwargs: More of the signal.
    """
    with IMPORT_GUARD:  # see import_guard.py: what writes to GitHub, only when needed
        from pycal_dashboard.services.message_comments import MessageComments

    for project in Project.objects.filter(repositories=repository, message__isnull=False):
        MessageComments(project).sync(repository)
