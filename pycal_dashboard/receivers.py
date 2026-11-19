"""What follows an update from GitHub: the receivers of :mod:`pycal_dashboard.update_signals`."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.dispatch import receiver

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
