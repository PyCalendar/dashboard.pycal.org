"""The queue of the updates of projects: add one, take the next, run it."""

import logging
import time
from collections.abc import Callable
from datetime import timedelta

from django.db import OperationalError, transaction
from django.utils import timezone

from pycal_dashboard.models import Project, UpdateJob

from .repository_update import RepositoryUpdate
from .update_worker import UpdateWorker

# a job that runs longer was stopped, such as with its process: it is taken again
STUCK = timedelta(minutes=10)
# how often a write is tried while another writes to SQLite, with this pause between
ATTEMPTS = 5
PAUSE = 0.2

log = logging.getLogger(__name__)


def retrying(write: Callable):
    """Run a write to the database again while the database is busy, such as SQLite.

    Args:
        write: The write.

    Returns:
        What it returns.

    Raises:
        OperationalError: The database stayed busy.
    """
    for attempt in range(1, ATTEMPTS + 1):
        try:
            return write()
        except OperationalError:
            if attempt == ATTEMPTS:
                raise
            time.sleep(PAUSE * attempt)
    return None  # never reached


class UpdateQueue:
    """Updates of projects, which the worker runs one after another in the background."""

    @staticmethod
    def add(project: Project, user=None) -> UpdateJob:
        """Queue an update of a project, unless one waits or runs, and start the worker.

        Args:
            project: The project.
            user: Who asked for it, None for the site.

        Returns:
            The job that waits or runs.
        """
        job = UpdateJob.objects.filter(project=project, status__in=UpdateJob.ACTIVE).first()
        if job is None:
            job = UpdateJob.objects.create(
                project=project, requested_by=user, total=project.repositories.count()
            )
        UpdateWorker.start()
        return job

    @staticmethod
    def claim() -> UpdateJob | None:
        """Take the oldest job that waits, or one that got stuck, and mark it as running.

        Only one worker gets a job, also if several look at the same time.

        Returns:
            The job, None if none waits.
        """
        stuck = timezone.now() - STUCK
        for job in UpdateJob.objects.filter(status=UpdateJob.QUEUED).order_by("created")[:1]:
            taken = UpdateJob.objects.filter(pk=job.pk, status=UpdateJob.QUEUED)
            if taken.update(status=UpdateJob.RUNNING, started=timezone.now()):
                job.refresh_from_db()
                return job
        for job in UpdateJob.objects.filter(status=UpdateJob.RUNNING, started__lt=stuck)[:1]:
            taken = UpdateJob.objects.filter(pk=job.pk, started=job.started)
            if taken.update(started=timezone.now(), done=0, errors=0):
                job.refresh_from_db()
                return job
        return None

    @classmethod
    def run(cls, job: UpdateJob) -> UpdateJob:
        """Read every repository of the project of a job, and count the progress.

        Args:
            job: The claimed job.

        Returns:
            The job, done.
        """
        repositories = list(job.project.repositories.all())
        job.total = len(repositories)
        retrying(lambda: job.save(update_fields=["total"]))
        for repository in repositories:
            if not retrying(RepositoryUpdate(repository).run):
                job.errors += 1
            job.done += 1
            retrying(lambda: job.save(update_fields=["done", "errors"]))
        retrying(lambda: cls.finish(job, UpdateJob.DONE))
        return job

    @staticmethod
    def finish(job: UpdateJob, status: str) -> None:
        """End a job; a done one marks its project as updated.

        Args:
            job: The job.
            status: ``done`` or ``failed``.
        """
        with transaction.atomic():
            job.status = status
            job.finished = timezone.now()
            job.save(update_fields=["status", "finished"])
            if status == UpdateJob.DONE:
                Project.objects.filter(pk=job.project_id).update(updated=job.finished)

    @classmethod
    def work(cls) -> int:
        """Run the jobs until none waits.

        Returns:
            How many jobs ran.
        """
        count = 0
        while (job := retrying(cls.claim)) is not None:
            try:
                cls.run(job)
            except Exception:  # the job ends as failed; the next ones run
                log.exception("The update of %s failed", job.project)
                retrying(lambda: cls.finish(job, UpdateJob.FAILED))  # noqa: B023
            count += 1
        return count
