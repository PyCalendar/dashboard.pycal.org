"""The badge of a pull request: the step it is in and how many of its tasks are done."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from django.core.cache import cache
from django.utils.translation import get_language, gettext

from pycal_dashboard import badges
from pycal_dashboard.badges import LABEL_COLOR
from pycal_dashboard.services.column_results import ColumnResults
from pycal_dashboard.services.progress import PullRequestProgress

if TYPE_CHECKING:
    from pycal_dashboard.models import Issue, Project, Repository

# the colors of the badge: tasks to do; outside of the steps, or no steps
TODO = "#fe7d37"
NONE = "#9f9f9f"
CACHED_SECONDS = 7 * 24 * 3600  # the key changes with the data, so it may stay long
KINDS = {"svg": ("image/svg+xml", badges.svg), "png": ("image/png", badges.png)}


class PullRequestBadge:
    """The badge of a pull request in a project, such as *Triage 3/4*, cached.

    The step is the one the pull request is in (:class:`PullRequestProgress`), with how many of
    its tasks are done. The badge is drawn once and kept in the cache of Django under a key made
    of what it depends on: the pull request, when the repositories were last updated, and the
    steps with their filters. A change of any of them makes a new key, so nothing is computed
    again until something changed.
    """

    def __init__(self, issue: Issue, project: Project, repositories: list[Repository]):
        """The badge of a pull request.

        Parameters:
            issue: The pull request.
            project: The project whose steps it goes through.
            repositories: The repositories of the project that the person sees, in which the
                states of the author are counted.
        """
        self.issue = issue
        self.project = project
        self.repositories = repositories

    def version(self) -> str:
        """What the badge depends on, as a short hash: also its ETag.

        Returns:
            The hash; it changes when the repositories are updated or the steps change.
        """
        steps = list(
            self.project.steps.values_list(
                "pk", "position", "updated", "filter__updated", "filter__columns"
            )
        )
        repositories = sorted(
            (repository.pk, repository.updated, repository.reviews_changed)
            for repository in self.repositories
        )
        parts = repr((self.issue.pk, self.issue.changed, repositories, steps))
        return hashlib.sha256(parts.encode()).hexdigest()[:20]

    def texts(self) -> tuple[str, str, str, str]:
        """The label, the value, the color of the value and the color of the label.

        Returns:
            Such as ``("Triage", "3/4", "#fe7d37", "#bbf7d0")``: the step, its tasks done and
            all of them, with the color of the step behind its name (gray without one);
            ``("Steps", "outside", ...)`` when no task of any step is to do, outside of the
            usual steps; ``("Steps", "none", ...)`` without steps.
        """
        results = ColumnResults(self.repositories, project=self.project)
        progress = PullRequestProgress(self.issue, self.project, results.scope, results)
        if progress.current:
            current = progress.current
            done = f"{current.done}/{len(current.tasks)}"
            return current.step.name, done, TODO, current.step.color or LABEL_COLOR
        if progress.steps:  # no task of any step is to do
            return gettext("Steps"), gettext("outside"), NONE, LABEL_COLOR
        return gettext("Steps"), gettext("none"), NONE, LABEL_COLOR

    def render(self, kind: str) -> tuple[bytes, str, str]:
        """The badge, from the cache when nothing changed since it was drawn.

        Parameters:
            kind: ``svg`` or ``png``.

        Returns:
            The bytes, their media type and the version (``ETag``).
        """
        media, draw = KINDS[kind]
        version = self.version()
        key = f"badge:{kind}:{get_language()}:{version}"
        found = cache.get(key)
        if found is None:
            found = draw(*self.texts())
            cache.set(key, found, CACHED_SECONDS)
        return found, media, version
