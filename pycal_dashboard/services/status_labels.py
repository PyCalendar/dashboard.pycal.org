"""The status labels of the steps on GitHub: which step a pull request is in."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from django.conf import settings

from pycal_dashboard.actions import LabelAdded, LabelRemoved, StepLabelSaved
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

if TYPE_CHECKING:
    from pycal_dashboard.models import PullRequestStep, Repository

log = logging.getLogger(__name__)
PREFIX = "Step: "  # the labels of steps, such as "Step: Review", next to other labels
MAX_NAME = 50  # GitHub allows labels of at most 50 characters
MAX_DESCRIPTION = 100  # and descriptions of at most 100
DEFAULT_COLOR = "ededed"  # the gray of GitHub for a label: a step without a color
NEXT_OR_LAST = re.compile(r'<([^>]+)>;\s*rel="last"')


def label_name(step: PullRequestStep) -> str:
    """The name of the label of a step on GitHub.

    Parameters:
        step: The step.

    Returns:
        Such as ``Step: Review``, at most 50 characters.
    """
    return (PREFIX + step.name)[:MAX_NAME].strip()


def step_name(label: str) -> str:
    """The name of a step from the name of its label, renamed on GitHub.

    Parameters:
        label: The name of the label, such as ``Step: Peer review``.

    Returns:
        Such as ``Peer review``: without the prefix, if it has one.

    Examples:
        >>> step_name("Step: Peer review"), step_name("Peer review")
        ('Peer review', 'Peer review')
    """
    name = label[len(PREFIX) :] if label.lower().startswith(PREFIX.lower()) else label
    return " ".join(name.split())[:100] or label


def label_color(step: PullRequestStep) -> str:
    """The color of the label of a step: that of the step, else the gray of GitHub.

    Parameters:
        step: The step, whose color is such as ``#bbf7d0`` or "".

    Returns:
        Such as ``bbf7d0``, without ``#``.
    """
    return (step.color or "").lstrip("#").lower() or DEFAULT_COLOR


def step_color(label: str) -> str:
    """The color of a step from the color of its label, changed on GitHub.

    Parameters:
        label: Such as ``d73a4a``.

    Returns:
        Such as ``#d73a4a``; "" for the gray of GitHub: no color.

    Examples:
        >>> step_color("D73A4A"), step_color("ededed")
        ('#d73a4a', '')
    """
    color = label.lower().lstrip("#")
    return "" if color == DEFAULT_COLOR or not re.fullmatch(r"[0-9a-f]{6}", color) else f"#{color}"


def description(step: PullRequestStep) -> str:
    """The description of the label of a step: who made it, and the link to the step.

    Parameters:
        step: The step.

    Returns:
        Such as ``Created by dashboard.pycal.org: https://.../steps/?step_id=7``; the link alone
        when both do not fit into 100 characters.
    """
    url = f"{settings.SITE_URL}{step.project.path('steps/')}?step_id={step.pk}"
    text = f"Created by {settings.SITE_NAME}: {url}"
    return text if len(text) <= MAX_DESCRIPTION else url[:MAX_DESCRIPTION]


class StatusLabels:
    """The status labels of the steps of a project in a repository, after each update of it.

    Each step has a label in each repository of the project (``StepLabel``), such as
    *Step: Review*, with the color of the step and a description that links the step; a label
    renamed or recolored on GitHub renames or recolors the step. On the open pull requests that
    have the message of the project (``PullRequestComment``), the label shows the step they are
    in, as the project says (``Project.step_labels``):

    ``automatic``
        The site puts the label of the step a pull request is in on it, and removes the others.
    ``manual``
        People put the labels on the pull requests; the site does not.

    Either way, a step label that a person put on a pull request puts it into that step
    (``PullRequestPlace.chosen``); when a pull request has several, the one added last stays
    and the site removes the others. Without any, the pull request is in the step of its
    conditions again. Every write to GitHub is an action of the log.
    """

    def __init__(self, project: Project):
        """The steps of a project.

        Parameters:
            project: The project, with ``step_labels`` other than ``off``.
        """
        self.project = project
        self.automatic = project.step_labels == Project.LABELS_AUTOMATIC
        self.steps = list(project.steps.select_related("project"))

    def sync(self, repository: Repository) -> None:
        """Keep the labels of the steps in a repository and on its pull requests.

        Parameters:
            repository: The repository that was updated, with the GitHub App.
        """
        if not self.steps or not repository.app_installed:
            return
        names = self.define(repository)
        self.place(repository, names)

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
        """Put the label of its step on each open pull request with the message, as the mode says.

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
        with_message = PullRequestComment.objects.filter(project=self.project).values("issue")
        pulls = (
            Issue.objects.filter(
                repository=repository, pull_request=True, state=Issue.OPEN, pk__in=with_message
            )
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
            chosen = current if not self.automatic or current != place.labeled else None
            labeled = None
            if self.automatic and chosen is None:
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
