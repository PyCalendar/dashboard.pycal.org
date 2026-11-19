"""Whether a project is up to date, being updated, or needs an update."""

from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from pycal_dashboard.models import Project, UpdateJob

# an update older than this is out of date
FRESH = timedelta(days=1)


@dataclass(frozen=True)
class ProjectStatus:
    """The state of the data of a project, shown on its page.

    Attributes:
        state: ``updating``, ``never``, ``failed``, ``outdated`` or ``current``.
        job: The last update, None before the first.
        failed: The repositories whose last reading failed.
    """

    state: str
    job: UpdateJob | None
    failed: tuple = ()

    @property
    def updating(self) -> bool:
        """Whether an update waits or runs."""
        return self.state == "updating"

    @property
    def up_to_date(self) -> bool:
        """Whether every repository was read in the last day without an error."""
        return self.state == "current"

    @classmethod
    def of(cls, project: Project, repositories: list) -> "ProjectStatus":
        """The status of a project.

        Args:
            project: The project.
            repositories: Its repositories that the visitor sees.

        Returns:
            The status.
        """
        job = project.updates.first()
        # read after the job: the worker ends a job and marks the project in one transaction, so
        # a done job comes with the time of its update, also if it ended since the page began
        project.refresh_from_db(fields=["updated"])
        failed = tuple(r for r in repositories if r.error_code)
        if job is not None and job.active:
            return cls("updating", job, failed)
        if job is not None and job.status == UpdateJob.FAILED:
            return cls("failed", job, failed)
        if project.updated is None:
            return cls("never", job, failed)
        if failed:
            return cls("failed", job, failed)
        unread = any(r.updated is None for r in repositories)
        if unread or project.updated < timezone.now() - FRESH:
            return cls("outdated", job, failed)
        return cls("current", job, failed)
