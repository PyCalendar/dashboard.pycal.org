"""What follows an update from GitHub: the receivers of :mod:`pycal_dashboard.update_signals`."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.dispatch import receiver

from .import_guard import IMPORT_GUARD
from .models import Project
from .update_signals import project_updated, repository_updated

if TYPE_CHECKING:
    from pycal_dashboard.models import Repository


@receiver(repository_updated)
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
            results = ColumnResults(list(repositories))
            for value in values:
                results.of(Column.decode(value))
