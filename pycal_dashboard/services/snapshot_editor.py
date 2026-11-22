"""Take, download and delete the snapshots of a project, with the rights of a person."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils import timezone

from pycal_dashboard.errors import SnapshotNotFound
from pycal_dashboard.models import ProjectSnapshot

from .project_backup import ProjectBackup

if TYPE_CHECKING:
    from .project_access import ProjectAccess

# the snapshots that a project keeps at most; taking another deletes the oldest
MAX_SNAPSHOTS = 100


class SnapshotEditor:
    """The snapshots of a project, as a person may use them.

    Writers take and download snapshots, as they download backups; only the owners delete them
    or restore them, as restoring can replace filters and steps (``ProjectAccess``).
    """

    def __init__(self, access: ProjectAccess):
        """The snapshots of the project of an access.

        Parameters:
            access: The project with the rights of the person.
        """
        self.access = access
        self.project = access.project

    def take(self) -> ProjectSnapshot:
        """Keep the backup of the project now; beyond :data:`MAX_SNAPSHOTS`, the oldest goes.

        Returns:
            The snapshot.

        Raises:
            ProjectReadOnly: The person may not change the project.
        """
        self.access.require_write()
        snapshot = ProjectSnapshot.objects.create(
            project=self.project,
            text=ProjectBackup(self.project).export(),
            created_by=self.access.user if self.access.user.is_authenticated else None,
        )
        old = self.project.snapshots.values_list("pk", flat=True)[MAX_SNAPSHOTS:]
        ProjectSnapshot.objects.filter(pk__in=list(old)).delete()
        return snapshot

    def find(self, pk: int) -> ProjectSnapshot:
        """A snapshot of the project, for a writer.

        Parameters:
            pk: Its id.

        Returns:
            The snapshot.

        Raises:
            ProjectReadOnly: The person may not change the project.
            SnapshotNotFound: The project has no such snapshot.
        """
        self.access.require_write()
        found = self.project.snapshots.filter(pk=pk).first()
        if found is None:
            raise SnapshotNotFound(str(pk))
        return found

    def delete(self, pk: int) -> ProjectSnapshot:
        """Delete a snapshot.

        Parameters:
            pk: Its id.

        Returns:
            The deleted snapshot.

        Raises:
            ProjectOwnersOnly: Only the owners delete snapshots.
            SnapshotNotFound: The project has no such snapshot.
        """
        self.access.require_owner()
        found = self.find(pk)
        found.delete()
        return found

    @staticmethod
    def filename(snapshot: ProjectSnapshot) -> str:
        """The name of the file of a snapshot, as that of a backup, with its time.

        Parameters:
            snapshot: The snapshot.

        Returns:
            Such as ``icalendar-snapshot-2026-11-22-1030.yaml``.
        """
        when = timezone.localtime(snapshot.created).strftime("%Y-%m-%d-%H%M")
        return f"{snapshot.project.slug}-snapshot-{when}.yaml"
