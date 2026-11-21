"""The status labels of the steps on GitHub: which step a pull request with the message is in."""

import pytest

from pycal_dashboard.models import (
    Issue,
    LogAction,
    Project,
    PullRequestComment,
    PullRequestFilter,
    PullRequestPlace,
    PullRequestStep,
    Repository,
    StepLabel,
)
from pycal_dashboard.services.progress import PullRequestProgress
from pycal_dashboard.services.project_editor import ProjectEditor
from pycal_dashboard.services.repository_update import RepositoryUpdate
from pycal_dashboard.services.status_labels import description

pytestmark = pytest.mark.django_db
REPO = "collective/icalendar"


@pytest.fixture
def project(github, bob):
    """Conflict (1) in Conflicts, Ready (2) in Review, Other (3) without the message."""
    github.add_repository(REPO, installation=11)
    github.add_label(REPO, "needs review", "", "fbca04")
    github.add_issue(REPO, "Conflict", pull_request=True, mergeable_state="dirty")
    github.add_issue(REPO, "Ready", pull_request=True, labels=("needs review",))
    github.add_issue(REPO, "Other", pull_request=True, mergeable_state="dirty")
    repository = Repository.objects.create(full_name=REPO)
    project = ProjectEditor.create(bob, "iCalendar", slug="icalendar")
    project.repositories.add(repository)
    for position, (name, column, color) in enumerate(
        (
            ("Conflicts", "branch~applies~conflict", "#fecaca"),
            ("Review", "labels~applies~present~needs review", ""),
        )
    ):
        saved = PullRequestFilter.objects.create(project=project, name=name, columns=[column])
        PullRequestStep.objects.create(
            project=project, filter=saved, name=name, position=position, color=color
        )
    update(project)  # the pull requests are known, then they get the message
    for number in (1, 2):
        issue = Issue.objects.get(number=number)
        PullRequestComment.objects.create(project=project, issue=issue, github_id=number, digest="")
    return project


def update(project):
    assert RepositoryUpdate(project.repositories.get()).run()


def mode(project, value):
    Project.objects.filter(pk=project.pk).update(step_labels=value)
    project.refresh_from_db()


def labels_of(github, number):
    return sorted(
        label["name"] for label in github.repositories[REPO]["issues"][number - 1]["labels"]
    )


def repository_label(github, name):
    return next(label for label in github.repositories[REPO]["labels"] if label["name"] == name)


def place(number):
    return PullRequestPlace.objects.get(issue__number=number)


def test_off_writes_nothing(github, project):
    github.requests.clear()
    update(project)
    assert not [r for r in github.writes() if "/labels" in r.url.path]
    assert not StepLabel.objects.exists()


def test_automatic_creates_the_labels_and_puts_them_on(github, project, settings):
    settings.SITE_URL = "https://dashboard.example.org"
    settings.SITE_NAME = "Dashboard"
    mode(project, "automatic")
    update(project)
    conflicts, review = PullRequestStep.objects.order_by("position")
    label = repository_label(github, "Step: Conflicts")
    assert label["color"] == "fecaca"
    assert label["description"] == (
        "Created by Dashboard: "
        f"https://dashboard.example.org/projects/icalendar/steps/?step_id={conflicts.pk}"
    )
    assert repository_label(github, "Step: Review")["color"] == "ededed"  # no color: gray
    assert description(review).endswith(f"?step_id={review.pk}")
    assert labels_of(github, 1) == ["Step: Conflicts"]
    assert labels_of(github, 2) == ["Step: Review", "needs review"]
    assert labels_of(github, 3) == []  # without the message
    assert (place(1).labeled, place(1).chosen) == (conflicts, None)
    texts = list(LogAction.objects.values_list("text", flat=True))
    assert any("Label Step: Review created in collective/icalendar" in t for t in texts)
    assert any("Label Step: Review added to collective/icalendar#2: it is in" in t for t in texts)
    github.requests.clear()
    update(project)  # again: nothing changed, nothing is written
    assert not [r for r in github.writes() if "/labels" in r.url.path]


def test_a_label_changed_on_github_changes_the_step(github, project):
    mode(project, "automatic")
    update(project)
    github.edit_label(REPO, "Step: Review", new_name="Step: Peer review", color="bfdbfe")
    github.edit_label(REPO, "Step: Conflicts", color="ededed")
    update(project)
    conflicts, review = PullRequestStep.objects.order_by("position")
    assert (review.name, review.color) == ("Peer review", "#bfdbfe")
    assert conflicts.color == ""  # the gray of GitHub: no color
    github.requests.clear()
    update(project)
    assert not [r for r in github.writes() if "/labels" in r.url.path]  # it stays


def test_a_step_changed_on_the_site_changes_its_label(github, project, client, bob):
    mode(project, "automatic")
    update(project)
    review = PullRequestStep.objects.get(name="Review")
    client.force_login(bob)
    client.post(
        f"/projects/icalendar/steps/{review.pk}/edit/",
        {"name": "Peer review", "color": "#bbf7d0"},
        HTTP_ACCEPT="application/json",
    )
    update(project)
    label = repository_label(github, "Step: Peer review")
    assert label["color"] == "bbf7d0"
    assert labels_of(github, 2) == ["Step: Peer review", "needs review"]  # the same label


def test_a_person_chooses_the_step_with_a_label(github, project):
    """Automatic: the label a person adds wins; without labels the site takes over again."""
    mode(project, "automatic")
    update(project)
    conflicts, review = PullRequestStep.objects.order_by("position")
    github.label_issue(REPO, 2, "Step: Conflicts")  # Ready, in Review, goes back
    update(project)
    assert labels_of(github, 2) == ["Step: Conflicts", "needs review"]  # the older one removed
    assert (place(2).chosen, place(2).labeled) == (conflicts, None)
    ready = Issue.objects.get(number=2)
    assert PullRequestProgress(ready, project).current.step == conflicts
    github.unlabel_issue(REPO, 2, "Step: Conflicts")  # all removed: as usual
    update(project)
    assert labels_of(github, 2) == ["Step: Review", "needs review"]
    assert (place(2).chosen, place(2).labeled) == (None, review)
    assert PullRequestProgress(ready, project).current.step == review


def test_manual_leaves_the_labels_to_people(github, project):
    mode(project, "manual")
    update(project)
    conflicts, review = PullRequestStep.objects.order_by("position")
    assert labels_of(github, 1) == [] and repository_label(github, "Step: Review")
    github.label_issue(REPO, 1, "Step: Review")
    github.label_issue(REPO, 1, "Step: Conflicts")  # added last: it stays
    update(project)
    assert labels_of(github, 1) == ["Step: Conflicts"]
    assert place(1).chosen == conflicts
    github.unlabel_issue(REPO, 1, "Step: Conflicts")
    github.label_issue(REPO, 1, "Step: Review")
    update(project)
    assert place(1).chosen == review and labels_of(github, 1) == ["Step: Review"]


def test_the_mode_is_a_setting_of_writers(client, project, bob):
    client.force_login(bob)
    page = client.get("/projects/icalendar/settings/").content.decode()
    assert 'name="step_labels" value="off" checked' in page
    client.post(
        "/projects/icalendar/settings/",
        {"name": "iCalendar", "description": "", "step_labels": "automatic"},
    )
    project.refresh_from_db()
    assert project.step_labels == "automatic"
    client.post(
        "/projects/icalendar/settings/",
        {"name": "iCalendar", "description": "", "step_labels": "everything"},
    )
    project.refresh_from_db()
    assert project.step_labels == "automatic"  # unknown: kept
