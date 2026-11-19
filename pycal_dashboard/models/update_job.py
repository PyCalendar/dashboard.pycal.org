"""The update of a project in the background: its repositories read from GitHub."""

from django.conf import settings
from django.db import models


class UpdateJob(models.Model):
    """One update of the repositories of a project, run by the worker in the background.

    ``done`` of ``total`` repositories are read; the page of the project shows it as a progress
    bar.
    """

    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    STATUSES = [(QUEUED, "queued"), (RUNNING, "running"), (DONE, "done"), (FAILED, "failed")]
    ACTIVE = (QUEUED, RUNNING)

    project = models.ForeignKey("Project", on_delete=models.CASCADE, related_name="updates")
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    status = models.CharField(max_length=10, choices=STATUSES, default=QUEUED)
    done = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField(default=0)
    errors = models.PositiveIntegerField(default=0)  # repositories that could not be read
    created = models.DateTimeField(auto_now_add=True)
    started = models.DateTimeField(null=True, blank=True)
    finished = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self) -> str:
        return f"update of {self.project}: {self.status} {self.done}/{self.total}"

    @property
    def active(self) -> bool:
        """Whether it waits or runs."""
        return self.status in self.ACTIVE

    @property
    def percent(self) -> int:
        """How much is done, 0 to 100."""
        if self.status == self.DONE or not self.total:
            return 100 if self.status == self.DONE else 0
        return min(100, round(100 * self.done / self.total))
