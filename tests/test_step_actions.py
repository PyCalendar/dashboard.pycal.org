"""When a pull request completes a step, the actions of the step follow, such as a label."""

import pytest

from pycal_dashboard.models import (
    Issue,
    LogAction,
    PullRequestFilter,
    PullRequestPlace,
    PullRequestStep,
    Repository,
)
from pycal_dashboard.services.repository_update import RepositoryUpdate

from .test_steps import JSON, REPO

pytestmark = pytest.mark.django_db


@pytest.fixture
def project(github, bob):
    from pycal_dashboard.services.project_editor import ProjectEditor

    github.add_repository(REPO, installation=11)
    github.add_issue(REPO, "Conflict", pull_request=True, mergeable_state="dirty")
    github.add_issue(REPO, "Clean", pull_request=True)
    repository = Repository.objects.create(full_name=REPO)
    project = ProjectEditor.create(bob, "iCalendar", slug="icalendar")
    project.repositories.add(repository)
    return project


@pytest.fixture
def step(project):
    saved = PullRequestFilter.objects.create(
        project=project, name="Conflicts", columns=["branch~applies~conflict"]
    )
    return PullRequestStep.objects.create(
        project=project,
        filter=saved,
        name="Conflicts",
        actions=[{"kind": "add_label", "label": "conflict solved"}],
    )


def update(project):
    repository = project.repositories.get()
    assert RepositoryUpdate(repository).run()


def label_writes(github):
    return [r for r in github.writes() if r.url.path.endswith("/labels")]


def solve_the_conflict(github):
    pull = github.repositories[REPO]["issues"][0]
    pull["pull"].update(mergeable=True, mergeable_state="clean")
    pull["updated_at"] = "2026-11-03T10:00:00Z"


def test_the_first_update_only_records_the_places(github, project, step):
    update(project)
    places = {p.issue.title: p.step for p in PullRequestPlace.objects.select_related("issue")}
    assert places == {"Conflict": step, "Clean": None}
    assert label_writes(github) == []  # nothing for steps completed before


def test_a_completed_step_adds_its_label(github, project, step):
    update(project)
    solve_the_conflict(github)
    update(project)
    (write,) = label_writes(github)
    assert write.url.path == f"/repos/{REPO}/issues/1/labels"
    assert b"conflict solved" in write.content
    assert PullRequestPlace.objects.get(issue__title="Conflict").step is None
    assert LogAction.objects.filter(kind="label").get().text == (
        f"Label conflict solved added to {REPO}#1: it completed the step Conflicts"
    )
    update(project)  # once only
    assert len(label_writes(github)) == 1


def test_a_step_still_to_do_adds_nothing(github, project, step):
    update(project)
    update(project)
    assert label_writes(github) == []


def test_without_actions_or_steps_nothing_is_written(github, project, step):
    step.actions = []
    step.save()
    update(project)
    solve_the_conflict(github)
    update(project)
    assert label_writes(github) == []
    step.delete()
    update(project)
    assert label_writes(github) == []


def test_a_closed_pull_request_is_not_watched(github, project, step):
    update(project)
    pull = github.repositories[REPO]["issues"][0]
    pull.update(state="closed", closed_at="2026-11-03T09:00:00Z", updated_at="2026-11-03T10:00:00Z")
    update(project)
    assert label_writes(github) == []


def test_the_editor_keeps_the_labels(client, project, step, bob):
    client.force_login(bob)
    page = client.get(f"/projects/icalendar/steps/?step={step.pk}").content.decode()
    assert 'value="conflict solved" data-action-label' in page
    assert page.count("data-action-label") == 2  # and an empty one
    client.post(
        f"/projects/icalendar/steps/{step.pk}/edit/",
        {"name": "Conflicts", "actions_form": "1", "action_label": ["ready", " ", "ready", "x"]},
        **JSON,
    )
    step.refresh_from_db()
    assert step.actions == [
        {"kind": "add_label", "label": "ready"},
        {"kind": "add_label", "label": "x"},
    ]
    client.post(f"/projects/icalendar/steps/{step.pk}/edit/", {"name": "C"}, **JSON)
    step.refresh_from_db()
    assert len(step.actions) == 2  # a form without the actions keeps them


def test_the_issue_is_kept_once(project, step):
    update(project)
    assert Issue.objects.filter(places__project=project).count() == 2
