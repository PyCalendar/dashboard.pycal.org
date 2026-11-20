"""What follows when a pull request completes a step: the actions of the step."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pycal_dashboard.actions import LabelAdded
from pycal_dashboard.conditions.group.column import Column
from pycal_dashboard.conditions.state.scope import Scope
from pycal_dashboard.models import Issue, PullRequestPlace
from pycal_dashboard.services.step_assignment import StepAssignment

if TYPE_CHECKING:
    from pycal_dashboard.models import Project, PullRequestStep, Repository

log = logging.getLogger(__name__)
# the kinds of actions of a step, with what they need
KINDS = {"add_label": "label"}


class StepCompletion:
    """Watch the open pull requests of a repository go through the steps of a project.

    After each update of a repository, the step of each of its open pull requests is compared
    with its place at the last update (``PullRequestPlace``). A pull request that left its step
    with all tasks of the step done completed it: the actions of the step follow, such as
    adding a label on GitHub. The first time a pull request is seen, its place is only
    recorded, so that nothing happens for the steps it completed before.
    """

    def __init__(self, project: Project):
        """The steps of a project.

        Parameters:
            project: The project.
        """
        self.project = project
        self.assignment = StepAssignment(project, Scope.of(project))

    def complete(self, step: PullRequestStep, issue: Issue) -> bool:
        """Whether no task of a step is to do for a pull request.

        Parameters:
            step: The step.
            issue: The pull request.

        Returns:
            True if no condition in force of its filter shows the pull request.
        """
        columns = [Column.decode(value) for value in step.filter.columns]
        return not any(
            column.shows(column.applies(issue, self.assignment.scope))
            for column in columns
            if column.filter != "all"
        )

    def observe(self, repository: Repository) -> list[tuple[Issue, PullRequestStep]]:
        """Record where the open pull requests of a repository are; act on completed steps.

        Parameters:
            repository: The repository that was updated.

        Returns:
            The pull requests that completed a step, with the step.
        """
        completed = []
        places = {
            place.issue_id: place
            for place in PullRequestPlace.objects.filter(
                project=self.project, issue__repository=repository
            ).select_related("step__filter")
        }
        pulls = (
            Issue.objects.filter(repository=repository, pull_request=True, state=Issue.OPEN)
            .select_related("author", "repository__installation", "pull_state")
            .prefetch_related("labels", "reviews")
        )
        for issue in pulls:
            step = self.assignment.step_of(issue)
            place = places.get(issue.pk)
            if place is None:  # seen for the first time: only where it is
                PullRequestPlace.objects.create(project=self.project, issue=issue, step=step)
                continue
            left = place.step
            if left is not None and left != step and self.complete(left, issue):
                completed.append((issue, left))
                self.act(issue, left)
            if place.step != step:
                place.step = step
                place.save(update_fields=["step", "updated"])
        return completed

    @staticmethod
    def act(issue: Issue, step: PullRequestStep) -> None:
        """Do the actions of a step that a pull request completed; each failure is logged.

        Parameters:
            issue: The pull request.
            step: The step it completed.
        """
        if not issue.repository.app_installed:
            log.info("%s: no GitHub App for the actions of %s", issue, step)
            return
        for action in step.actions or []:
            try:
                if action.get("kind") == "add_label" and action.get("label"):
                    LabelAdded(issue, action["label"], step).run()
            except Exception:  # one failing action does not stop the others
                log.exception("%s: the action %s of %s failed", issue, action, step)
