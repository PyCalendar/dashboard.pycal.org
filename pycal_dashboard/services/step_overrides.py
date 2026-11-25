"""What people decided about the steps of pull requests, besides their conditions.

The skips of steps and of their quality checks, and the steps chosen with their step labels on
GitHub.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pycal_dashboard.models import CheckSkip, Project, PullRequestPlace, StepSkip

if TYPE_CHECKING:
    from collections.abc import Iterable

    from pycal_dashboard.models import Issue, PullRequestStep


class StepOverrides:
    """The steps that pull requests of a project skip, read once for many pull requests.

    A pull request skips a step when a writer skipped it for the pull request (``StepSkip``),
    or when the step skips itself for its author (``PullRequestStep.skip_authors``). A pull
    request is not in a step that it skips: it is in the next one that shows it. A quality
    check that a person skipped for a pull request (``CheckSkip``) keeps it in its step no
    more, as if it was done. With the
    step labels on, a person chooses the step of a pull request with its label
    (``PullRequestPlace.chosen``): the pull request is in that step, see :meth:`chosen`.
    """

    def __init__(self, project: Project, issues: Iterable[Issue] | None = None):
        """The skips of the steps of a project.

        Parameters:
            project: The project.
            issues: The pull requests to read the skips of; all of the project when None.
        """
        skips = StepSkip.objects.filter(step__project=project).select_related("user__profile")
        if issues is not None:
            skips = skips.filter(issue__in=[issue.pk for issue in issues])
        self.skips = {(skip.issue_id, skip.step_id): skip for skip in skips}
        checks = CheckSkip.objects.filter(step__project=project).select_related("user__profile")
        if issues is not None:
            checks = checks.filter(issue__in=[issue.pk for issue in issues])
        self.checks = {(skip.issue_id, skip.step_id, skip.condition): skip for skip in checks}
        self.authors = {
            step.pk: {str(login).lower() for login in step.skip_authors or []}
            for step in project.steps.all()
        }
        self.choices: dict[int, PullRequestStep] = {}
        if project.step_labels != Project.LABELS_OFF:
            places = PullRequestPlace.objects.filter(project=project, chosen__isnull=False)
            if issues is not None:
                places = places.filter(issue__in=[issue.pk for issue in issues])
            self.choices = {
                place.issue_id: place.chosen for place in places.select_related("chosen__filter")
            }

    def chosen(self, pk: int) -> PullRequestStep | None:
        """The step that a person chose for a pull request with its status label.

        Parameters:
            pk: The id of the pull request.

        Returns:
            The step; None when nobody chose one.
        """
        return self.choices.get(pk)

    def skip(
        self, issue: Issue, step: PullRequestStep, login: str | None = None
    ) -> StepSkip | None:
        """Whether a pull request skips a step, and why.

        Parameters:
            issue: The pull request.
            step: The step.
            login: The GitHub handle of its author; that of ``issue.author`` when None.

        Returns:
            The skip of a writer; an unsaved skip (:attr:`StepSkip.automatic`) when the step
            skips itself for the author; None when the pull request does not skip the step.
        """
        found = self.skips.get((issue.pk, step.pk))
        if found is not None:
            return found
        if login is None:
            login = issue.author.login if issue.author_id and issue.author else ""
        if login and login.lower() in self.authors.get(step.pk, ()):
            return StepSkip(step=step, issue=issue)
        return None

    def skips_step(self, pk: int, login: str, step: PullRequestStep) -> bool:
        """Whether the pull request of an id skips a step, without loading the pull request.

        Parameters:
            pk: The id of the pull request.
            login: The GitHub handle of its author, "" for none.
            step: The step.

        Returns:
            True if it skips the step.
        """
        if (pk, step.pk) in self.skips:
            return True
        return bool(login) and login.lower() in self.authors.get(step.pk, ())

    def check_skip(self, pk: int, step: PullRequestStep, condition: str) -> CheckSkip | None:
        """Whether the pull request of an id skips a quality check of a step, and why.

        Parameters:
            pk: The id of the pull request.
            step: The step.
            condition: The quality check: the column of its condition, as the filter keeps it.

        Returns:
            The skip; None when the pull request does not skip the quality check.
        """
        return self.checks.get((pk, step.pk, condition))
