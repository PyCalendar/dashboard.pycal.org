"""The steps of pull requests: made of filters, ordered, explained, and where a pull request is."""

import pytest

from pycal_dashboard.models import Issue, PullRequestFilter, PullRequestStep, Repository
from pycal_dashboard.services.project_editor import ProjectEditor
from pycal_dashboard.services.repository_update import RepositoryUpdate
from pycal_dashboard.services.step_assignment import StepAssignment
from pycal_dashboard.step_template import escape, expand

pytestmark = pytest.mark.django_db
REPO = "collective/icalendar"
JSON = {"HTTP_ACCEPT": "application/json"}


@pytest.fixture
def project(github, bob):
    github.add_repository(REPO, installation=11)
    github.add_label(REPO, "needs review", "", "fbca04")
    github.add_issue(REPO, "Ready", pull_request=True, labels=("needs review",))
    github.add_issue(REPO, "Conflict", pull_request=True, mergeable_state="dirty")
    github.add_issue(REPO, "Merged", pull_request=True, state="closed", merged=True)
    repository = Repository.objects.create(full_name=REPO)
    project = ProjectEditor.create(bob, "iCalendar", slug="icalendar")
    project.repositories.add(repository)
    assert RepositoryUpdate(repository).run()
    return project


@pytest.fixture
def filters(project):
    conflict = PullRequestFilter.objects.create(
        project=project, name="Conflicts", columns=["branch~applies~conflict"]
    )
    review = PullRequestFilter.objects.create(
        project=project,
        name="Review",
        columns=["labels~applies~present~needs review", "status~all~open"],
    )
    return conflict, review


def make_step(client, saved):
    return client.post("/projects/icalendar/steps/add/", {"filter": saved.pk})


def test_no_steps_yet(client, project):
    page = client.get("/projects/icalendar/steps/").content.decode()
    assert "data-no-steps" in page and 'href="/projects/icalendar/filters/"' in page
    tabs = page.split('<ul class="tabs">')[1].split("</ul>")[0]
    assert tabs.index("Filters") < tabs.index("Steps")


def test_make_a_filter_a_step(client, project, filters, bob):
    conflict, review = filters
    client.force_login(bob)
    answer = make_step(client, conflict)
    step = PullRequestStep.objects.get()
    assert answer["Location"] == f"/projects/icalendar/steps/?step={step.pk}"
    assert (step.name, step.filter, step.position) == ("Conflicts", conflict, 0)
    answer = client.post("/projects/icalendar/steps/add/", {"filter": review.pk}, **JSON)
    assert answer.status_code == 201 and answer.json()["name"] == "Review"
    assert PullRequestStep.objects.get(filter=review).position == 1
    answer = make_step(client, conflict)
    assert answer.status_code == 409 and "The filter is a step already" in answer.content.decode()


def test_the_filters_page_makes_steps(client, project, filters, bob):
    conflict, review = filters
    client.force_login(bob)
    make_step(client, conflict)
    page = client.get("/projects/icalendar/filters/").content.decode()
    item = page.split('data-filter="Conflicts"')[1].split("</li>")[0]
    assert "data-step-link" in item and "Step: Conflicts" in item
    item = page.split('data-filter="Review"')[1].split("data-filter-details")[0]
    assert "data-make-step" in item and "Make it a step" in item


def test_only_writers_change_steps(client, project, filters, alice):
    conflict, _review = filters
    assert make_step(client, conflict).status_code == 302  # sign in first
    assert not PullRequestStep.objects.exists()
    client.force_login(alice)
    assert make_step(client, conflict).status_code == 403


def test_the_bar_and_moving_steps(client, project, filters, bob):
    conflict, review = filters
    client.force_login(bob)
    make_step(client, conflict)
    make_step(client, review)
    first, second = PullRequestStep.objects.all()
    page = client.get("/projects/icalendar/steps/").content.decode()
    bar = page.split("data-step-bar>")[1].split("</ol>")[0]
    assert bar.index("Conflicts") < bar.index("Review")
    assert "Step 1" in bar and "Step 2" in bar and 'draggable="true"' in bar
    client.post(f"/projects/icalendar/steps/{second.pk}/move/", {"direction": "left"})
    assert list(PullRequestStep.objects.values_list("name", flat=True)) == ["Review", "Conflicts"]
    answer = client.post(f"/projects/icalendar/steps/{second.pk}/move/", {"to": "1"}, **JSON)
    assert answer.status_code == 204
    assert list(PullRequestStep.objects.values_list("name", flat=True)) == ["Conflicts", "Review"]


def test_edit_a_step_and_its_conditions(client, project, filters, bob):
    _conflict, review = filters
    client.force_login(bob)
    make_step(client, review)
    step = PullRequestStep.objects.get()
    page = client.get(f"/projects/icalendar/steps/?step={step.pk}").content.decode()
    detail = page.split("data-step-detail")[1]
    assert "It has the label needs review" in detail
    assert "It is open" not in detail  # off: no part of the filter
    assert "✎" in detail and detail.count("data-variables-menu") == 2  # summary, condition
    assert 'role="menuitem" data-variable="{author}"' in detail and "Insert</button>" not in detail
    assert '<textarea id="description-0" name="description-0"' in detail  # the editor
    client.post(
        f"/projects/icalendar/steps/{step.pk}/edit/",
        {
            "name": "Waiting for a review",
            "summary": "Thanks, @{author}! Waiting for {project}.",
            "value-0": "labels~applies~present~needs review",
            "summary-0": "A person reviews it",
            "description-0": "See [the guide](https://docs.example.org/) for {full_name}.",
        },
    )
    step.refresh_from_db()
    assert step.name == "Waiting for a review"
    notes = step.conditions["labels~applies~present~needs review"]
    assert notes["summary"] == "A person reviews it"
    page = client.get(f"/projects/icalendar/steps/?step={step.pk}").content.decode()
    assert "Thanks, @octocat! Waiting for iCalendar." in page  # the preview with an example
    assert 'href="https://docs.example.org/"' in page and "collective/icalendar" in page
    client.logout()
    page = client.get(f"/projects/icalendar/steps/?step={step.pk}").content.decode()
    assert "data-edit-step" not in page and "A person reviews it" in page  # public, read only


def test_remove_a_step_keeps_its_filter(client, project, filters, bob):
    conflict, _review = filters
    client.force_login(bob)
    make_step(client, conflict)
    step = PullRequestStep.objects.get()
    client.post(f"/projects/icalendar/steps/{step.pk}/remove/")
    assert not PullRequestStep.objects.exists() and PullRequestFilter.objects.filter(pk=conflict.pk)
    assert client.get("/projects/icalendar/steps/?step=99").status_code == 404


def test_a_pull_request_is_in_the_left_most_step_that_applies(project, filters):
    conflict, review = filters
    PullRequestStep.objects.create(project=project, filter=review, name="Review", position=0)
    PullRequestStep.objects.create(project=project, filter=conflict, name="Conflicts", position=1)
    steps = StepAssignment(project)
    pulls = {i.title: i for i in Issue.objects.select_related("pull_state", "repository")}
    assert steps.step_of(pulls["Ready"]).name == "Review"  # has the label
    assert steps.step_of(pulls["Conflict"]).name == "Conflicts"
    assert steps.step_of(pulls["Merged"]) is None  # no condition applies
    PullRequestStep.objects.filter(name="Conflicts").update(position=0)
    PullRequestStep.objects.filter(name="Review").update(position=1)
    assert StepAssignment(project).step_of(pulls["Ready"]).name == "Review"


def test_templates_are_safe_for_the_input_of_others():
    """A title of anybody stays text: no links, images or HTML of its own."""
    from pycal_dashboard.markdown_text import render

    values = {"title": "[click](https://evil.example) ![x](https://evil.example/x.png) <b>"}
    html = render(expand("Title: {title} {unknown} {title.upper}", values))
    assert "<a " not in html and "<img" not in html and "<b>" not in html
    assert "{unknown}" in html and "{title.upper}" in html  # nothing else is evaluated
    assert escape("a\nb") == "a b"
