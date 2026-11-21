"""The step labels on GitHub: which step a pull request is in."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from pycal_dashboard.actions import LabelAdded, LabelRemoved, StepLabelDeleted, StepLabelSaved
from pycal_dashboard.github.installation_token import InstallationToken
from pycal_dashboard.models import (
    Issue,
    Label,
    Project,
    PullRequestComment,
    PullRequestPlace,
    StepLabel,
)
from pycal_dashboard.services.step_assignment import StepAssignment
from pycal_dashboard.step_label_names import (
    description,
    label_color,
    label_name,
    step_color,
    step_name,
)

if TYPE_CHECKING:
    from pycal_dashboard.models import PullRequestStep, Repository

log = logging.getLogger(__name__)
NEXT_OR_LAST = re.compile(r'<([^>]+)>;\s*rel="last"')


class StatusLabels:
    """The step labels of a project in a repository, after each update of it.

    With the step labels on (``Project.step_labels`` is ``sync``), each step has a label in
    each repository of the project (``StepLabel``), such as *Step: Review*, with the color of the
    step and a description that links the step; a label renamed or recolored on GitHub renames
    or recolors the step. People put the labels on pull requests by hand; on the open pull
    requests with the PR Sync on (``PullRequestComment``), the site puts the label of the step
    they are in on them and removes the others.

    A step label that a person put on a pull request puts it into that step
    (``PullRequestPlace.chosen``); when a pull request has several, the one added last stays
    and the site removes the others. Without any, the pull request is in the step of its
    conditions again. With the step labels off, the site deletes the labels of the steps that it
    made (:meth:`remove`). Every write to GitHub is an action of the log.
    """

    def __init__(self, project: Project):
        """The steps of a project.

        Parameters:
            project: The project.
        """
        self.project = project
        self.on = project.step_labels == Project.LABELS_SYNC
        self.steps = list(project.steps.select_related("project"))

    def sync(self, repository: Repository) -> None:
        """Keep the labels of the steps in a repository and on its pull requests.

        Parameters:
            repository: The repository that was updated, with the GitHub App.
        """
        if not repository.app_installed:
            return
        if not self.on:
            self.remove(repository)
            return
        if not self.steps:
            return
        names = self.define(repository)
        self.place(repository, names)

    def remove(self, repository: Repository) -> None:
        """Delete the labels of the steps in a repository on GitHub, with the step labels off.

        Only the labels the site made or took for the steps (``StepLabel``) are deleted; the
        pull requests are in the steps of their conditions again.

        Parameters:
            repository: The repository.
        """
        found = StepLabel.objects.filter(repository=repository, step__project=self.project)
        for saved in found.select_related("step"):
            label = repository.labels.filter(github_id=saved.github_id).first()
            if label is not None:
                try:
                    StepLabelDeleted(repository, saved.step, label.name).run()
                except Exception:  # one label does not stop the others
                    log.exception("%s: the label %s could not be deleted", repository, label)
                    continue
                label.delete()
            saved.delete()
        PullRequestPlace.objects.filter(project=self.project, issue__repository=repository).exclude(
            chosen=None, labeled=None
        ).update(chosen=None, labeled=None)

    def define(self, repository: Repository) -> dict[int, str]:
        """Create or change the label of each step in a repository; follow changes on GitHub.

        Parameters:
            repository: The repository.

        Returns:
            The name of the label of each step, by the id of the step.
        """
        names = {}
        known = {found.step_id: found for found in StepLabel.objects.filter(repository=repository)}
        labels = {label.github_id: label for label in repository.labels.all() if label.github_id}
        for step in self.steps:
            saved = known.get(step.pk)
            label = labels.get(saved.github_id) if saved and saved.github_id else None
            if saved and label:  # what changed on GitHub changes the step
                changed = []
                if label.name != saved.name:
                    step.name = step_name(label.name)
                    changed.append("name")
                if label.color.lower() != saved.color:
                    step.color = step_color(label.color)
                    changed.append("color")
                if changed:
                    step.save(update_fields=[*changed, "updated"])
            name, color, text = label_name(step), label_color(step), description(step)
            if label is None:  # a label of that name already, such as one made before
                label = repository.labels.filter(name__iexact=name).first()
            if label is None or (label.name, label.color.lower(), label.description) != (
                name,
                color,
                text,
            ):
                try:
                    label = self.save(repository, step, label, name, color, text)
                except Exception:  # one label does not stop the others
                    log.exception("%s: the label of %s could not be saved", repository, step)
                    continue
            StepLabel.objects.update_or_create(
                step=step,
                repository=repository,
                defaults={"github_id": label.github_id, "name": name, "color": color},
            )
            names[step.pk] = name
        return names

    @staticmethod
    def save(
        repository: Repository,
        step: PullRequestStep,
        label: Label | None,
        name: str,
        color: str,
        text: str,
    ) -> Label:
        """Create or change a label on GitHub, and keep it as the site knows the labels.

        Parameters:
            repository: The repository.
            step: The step of the label.
            label: The label to change; None to create it.
            name: Its name.
            color: Its color.
            text: Its description.

        Returns:
            The label, as GitHub has it now.
        """
        old = label.name if label else ""
        action = StepLabelSaved(repository, step, name, color, text, old=old)
        action.run()
        github_id = action.label.get("id") or (label.github_id if label else None)
        if label is None:
            label = Label(repository=repository)
        label.github_id, label.name, label.color, label.description = github_id, name, color, text
        label.save()
        return label

    def place(self, repository: Repository, names: dict[int, str]) -> None:
        """Follow the labels that people put on, and label the pull requests with the PR Sync on.

        Parameters:
            repository: The repository.
            names: The name of the label of each step, by the id of the step.
        """
        steps = {step.pk: step for step in self.steps}
        by_id = {
            found.github_id: steps[found.step_id]
            for found in StepLabel.objects.filter(repository=repository, step__in=self.steps)
            if found.github_id and found.step_id in names
        }
        synced = set(
            PullRequestComment.objects.filter(project=self.project).values_list("issue", flat=True)
        )
        pulls = (
            Issue.objects.filter(repository=repository, pull_request=True, state=Issue.OPEN)
            .select_related("author", "repository__installation", "pull_state")
            .prefetch_related("labels", "reviews")
        )
        assignment = StepAssignment(self.project)
        for issue in pulls:
            place = PullRequestPlace.objects.filter(project=self.project, issue=issue).first()
            if place is None:  # seen for the first time: where its conditions put it
                place = PullRequestPlace.objects.create(
                    project=self.project, issue=issue, step=assignment.step_of(issue, False)
                )
            ids = [found.github_id for found in issue.labels.all()]
            on = [by_id[github_id] for github_id in ids if github_id in by_id]
            if len(on) > 1:  # the one added last stays
                keep = self.newest(issue, {names[step.pk]: step for step in on}) or on[-1]
                for step in on:
                    if step != keep:
                        self.write(LabelRemoved, issue, names[step.pk], step)
                on = [keep]
            current = on[0] if on else None
            automatic = issue.pk in synced  # the PR Sync is on: the site labels it
            chosen = current if not automatic or current != place.labeled else None
            labeled = None
            if automatic and chosen is None:
                labeled = assignment.step_of(issue, chosen=False)
                if current is not None and current != labeled:
                    self.write(LabelRemoved, issue, names[current.pk], current)
                if labeled is not None and current != labeled and labeled.pk in names:
                    self.write(LabelAdded, issue, names[labeled.pk], labeled)
            if (place.chosen, place.labeled) != (chosen, labeled):
                place.chosen, place.labeled = chosen, labeled
                place.save(update_fields=["chosen", "labeled", "updated"])

    @staticmethod
    def write(action: type, issue: Issue, name: str, step: PullRequestStep) -> None:
        """Add or remove the label of a step on a pull request; a failure is logged.

        Parameters:
            action: ``LabelAdded`` or ``LabelRemoved``.
            issue: The pull request.
            name: The name of the label.
            step: The step.
        """
        try:
            action(issue, name, step, "status").run()
        except Exception:  # one pull request does not stop the others
            log.exception("%s: the label %s could not be changed", issue, name)

    @staticmethod
    def newest(issue: Issue, labels: dict[str, PullRequestStep]) -> PullRequestStep | None:
        """The step whose label was added last to a pull request, from its events on GitHub.

        Parameters:
            issue: The pull request.
            labels: The steps of the labels it has, by the name of the label.

        Returns:
            The step; None when its events do not say.
        """
        client = InstallationToken.client(issue.repository.installation.github_id)
        path = f"/repos/{issue.repository.full_name}/issues/{issue.number}/events"
        try:
            answer = client.request("GET", path, params={"per_page": 100})
            last = NEXT_OR_LAST.search(answer.headers.get("link", ""))
            events = (client.request("GET", last[1]) if last else answer).json()
        except Exception:
            log.exception("%s: its events could not be read", issue)
            return None
        lower = {name.lower(): step for name, step in labels.items()}
        for event in reversed(events):
            name = str((event.get("label") or {}).get("name", "")).lower()
            if event.get("event") == "labeled" and name in lower:
                return lower[name]
        return None
