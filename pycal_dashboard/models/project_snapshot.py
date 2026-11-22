"""A snapshot of a project: its backup, kept on the site, with when and by whom."""

from django.conf import settings
from django.db import models


class ProjectSnapshot(models.Model):
    """The backup of a project at a moment, kept on the site instead of downloaded.

    ``text`` is the YAML of :class:`~pycal_dashboard.services.project_backup.ProjectBackup`, so
    a snapshot is restored as a backup, and its download is a backup. ``created_by`` is who took
    it; None when that person deleted their account.
    """

    project = models.ForeignKey("Project", on_delete=models.CASCADE, related_name="snapshots")
    text = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="snapshots",
    )

    class Meta:
        ordering = ["-created", "-pk"]

    def __str__(self) -> str:
        return f"{self.project}: {self.created:%Y-%m-%d %H:%M}"
