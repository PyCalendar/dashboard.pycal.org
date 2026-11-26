"""The page of a pull request: the bar of the steps with their tasks, and the tasks of a step."""

import re

import pytest

from pycal_dashboard.models import (
    Issue,
    PullRequestFilter,
    PullRequestStep,
    Repository,
    StepSkip,
)
from pycal_dashboard.services.progress import PullRequestProgress
from pycal_dashboard.services.project_access import ProjectAccess
from pycal_dashboard.services.project_editor import ProjectEditor
from pycal_dashboard.services.step_assignment import StepAssignment

from .test_steps import filters, project  # noqa: F401 (fixtures)

pytestmark = pytest.mark.django_db
JSON = {"HTTP_ACCEPT": "application/json"}
URL = "https://github.com/collective/icalendar/pull"


@pytest.fixture
def steps(project, filters):  # noqa: F811
    conflict, review = filters
    first = PullRequestStep.objects.create(
        project=project,
        filter=conflict,
        name="Conflicts",
        position=0,
        conditions={"branch~applies~conflict": {"summary": "Solve the conflict"}},
    )
    second = PullRequestStep.objects.create(
        project=project,
        filter=review,
        name="Review",
        position=1,
        summary="Thanks, {author_mention}!",
        conditions={
            "labels~applies~present~needs review": {
                "summary": "Review {pr_title}",
                "description": "Ask in [the chat](https://chat.example.org).",
            }
        },
    )
    return first, second


def number_of(title: str) -> int:
    return Issue.objects.get(title=title).number


def test_the_progress_of_a_pull_request(project, steps):  # noqa: F811
    first, second = steps
    progress = PullRequestProgress(Issue.objects.get(title="Ready"), project)
    done, current = progress.steps
    assert (done.complete, done.done, len(done.tasks), done.squares) == (True, 1, 1, ["done"])
    assert current.current and progress.current is current
    assert [task.state for task in current.tasks] == ["todo"]  # the switch off is no task
    assert current.tasks[0].summary == "Review Ready"
    assert progress.chosen(None) is current and progress.chosen(str(first.pk)) is done
    assert progress.data()["step"] == second.pk


def test_the_page_shows_the_bar_and_the_tasks(client, project, steps):  # noqa: F811
    first, second = steps
    page = client.get(f"/projects/icalendar/pull/{number_of('Ready')}/").content.decode()
    assert f'data-step="{first.pk}" data-stage="past" data-complete="true"' in page
    assert (
        f'data-step="{second.pk}" data-stage="current" data-complete="false" data-current' in page
    )
    bar = page.split("data-progress>")[1].split("</ol>")[0]
    assert bar.count("square-done") == 1 and bar.count("square-todo") == 1
    assert ">0/1<" in bar and ">1/1<" in bar
    shown = page.split("data-shown-step")[1]
    assert "<h2>Review</h2>" in shown and "Thanks, @octocat!" in shown
    assert not re.search(r"Step \d", page)  # no number of a step for viewers
    assert 'data-task="todo" open>' in shown and ">TODO<" in shown
    assert 'href="https://chat.example.org"' in shown  # the description, expanded


def test_a_click_shows_another_step_with_its_tasks_done(client, project, steps):  # noqa: F811
    first, _second = steps
    number = number_of("Ready")
    page = client.get(f"/projects/icalendar/pull/{number}/?step={first.pk}").content.decode()
    assert f'href="?step={first.pk}" aria-current="step"' in page
    shown = page.split("data-shown-step")[1]
    assert 'data-task="done">' in shown and "Solve the conflict" in shown  # closed


def test_tasks_to_do_come_first(project, filters):  # noqa: F811
    _conflict, review = filters
    review.columns = ["status~applies~merged", "labels~applies~present~needs review"]
    review.save()
    PullRequestStep.objects.create(project=project, filter=review, name="Review")
    progress = PullRequestProgress(Issue.objects.get(title="Ready"), project)
    assert [task.state for task in progress.steps[0].tasks] == ["todo", "done"]
    assert progress.steps[0].squares == ["done", "todo"]  # green left, red right


def test_outside_of_the_usual_steps(client, project, steps):  # noqa: F811
    """No task of any step applies: all steps are gray, with a note."""
    page = client.get(f"/projects/icalendar/pull/{number_of('Merged')}/").content.decode()
    assert "data-outside-note" in page and "data-progress data-outside>" in page
    assert "data-current" not in page and "progress-check" not in page
    data = client.get(f"/projects/icalendar/pull/{number_of('Merged')}.json").json()
    assert data["outside"] is True and data["step"] is None


def test_hidden_steps_show_only_with_the_pull_request(client, project, steps):  # noqa: F811
    first, second = steps
    first.hidden = second.hidden = True
    first.save()
    second.save()
    page = client.get(f"/projects/icalendar/pull/{number_of('Ready')}/").content.decode()
    assert f'data-step="{first.pk}"' not in page  # hidden
    assert (
        f'data-step="{second.pk}" data-stage="current" data-complete="false" data-current data-hidden'
        in page
    )
    shown = client.get(f"/projects/icalendar/pull/{number_of('Ready')}/?step={first.pk}")
    assert f'data-shown-step="{first.pk}"' in shown.content.decode()  # by its address
    progress = PullRequestProgress(Issue.objects.get(title="Ready"), project)
    assert [step.step for step in progress.visible] == [second]
    assert progress.data()["steps"][0]["hidden"] is True


def test_without_steps(client, project):  # noqa: F811
    page = client.get(f"/projects/icalendar/pull/{number_of('Ready')}/").content.decode()
    assert "data-no-steps" in page


def test_the_json(client, project, steps):  # noqa: F811
    _first, second = steps
    data = client.get(f"/projects/icalendar/pull/{number_of('Ready')}.json").json()
    assert data["title"] == "Ready" and data["step"] == second.pk
    assert data["steps"][1]["tasks"][0] == {
        "condition": "labels~applies~present~needs review",
        "sentence": "PR has the label needs review",
        "state": "todo",
        "skipped": False,
        "summary": "Review Ready",
        "evidence": [{"text": "Its labels on GitHub", "url": f"{URL}/1"}],
    }


def test_an_unknown_pull_request(client, project):  # noqa: F811
    answer = client.get("/projects/icalendar/pull/999/")
    assert answer.status_code == 404 and "Pull request not found" in answer.content.decode()
    issue = Issue.objects.filter(pull_request=False).first()
    if issue:  # an issue is no pull request
        assert client.get(f"/projects/icalendar/pull/{issue.number}/").status_code == 404


def test_private_repositories_are_hidden(client, project, alice):  # noqa: F811
    Repository.objects.update(private=True)
    assert client.get(f"/projects/icalendar/pull/{number_of('Ready')}/").status_code == 404


def test_the_same_number_in_two_repositories(client, github, project):  # noqa: F811
    from pycal_dashboard.services.repository_update import RepositoryUpdate

    github.add_repository("collective/other", installation=11)
    for _ in range(3):
        github.add_issue("collective/other", "Other", pull_request=True)
    other = Repository.objects.create(full_name="collective/other")
    project.repositories.add(other)
    assert RepositoryUpdate(other).run()
    number = number_of("Ready")
    page = client.get(f"/projects/icalendar/pull/{number}/").content.decode()
    assert "data-choose-repository" in page
    assert 'href="?repository=collective%2Fother"' in page
    page = client.get(f"/projects/icalendar/pull/{number}/?repository=collective/icalendar")
    assert "data-progress" not in page.content.decode()  # no steps, the pull request shown
    assert 'data-pull="collective/icalendar#' in page.content.decode()
    table = client.get("/projects/icalendar/pull-requests/").content.decode()
    assert f"/pull/{number}/?repository=collective%2Ficalendar" in table


def test_the_table_links_the_page(client, project):  # noqa: F811
    table = client.get("/projects/icalendar/pull-requests/").content.decode()
    assert f'href="/projects/icalendar/pull/{number_of("Ready")}/" data-pull-page>Ready<' in table


def test_the_stages_of_the_steps(client, project, filters):  # noqa: F811
    """Past steps green with a check mark, the current one red or yellow, future ones gray."""
    conflict, review = filters
    PullRequestStep.objects.create(project=project, filter=conflict, name="Conflicts", position=0)
    PullRequestStep.objects.create(project=project, filter=review, name="Review", position=1)
    third = PullRequestFilter.objects.create(
        project=project, name="Later", columns=["status~applies~open"]
    )
    PullRequestStep.objects.create(project=project, filter=third, name="Later", position=2)
    progress = PullRequestProgress(Issue.objects.get(title="Conflict"), project)
    assert [step.stage for step in progress.steps] == ["current", "future", "future"]
    progress = PullRequestProgress(Issue.objects.get(title="Ready"), project)
    assert [step.stage for step in progress.steps] == ["past", "current", "future"]
    page = client.get(f"/projects/icalendar/pull/{number_of('Ready')}/").content.decode()
    bar = page.split("data-progress>")[1].split("</ol>")[0]
    future = bar.split('data-stage="future"')[1]
    assert "progress-count" not in future and "progress-check" not in future  # no status
    assert "progress-check" in bar.split('data-stage="past"')[1].split("</li>")[0]
    assert "Step 1" not in bar  # the names only
    assert PullRequestProgress(Issue.objects.get(title="Merged"), project).steps[0].stage == (
        "outside"
    )


@pytest.fixture
def open_step(project, steps):  # noqa: F811
    """A third step that every open pull request is in, after Review."""
    saved = PullRequestFilter.objects.create(
        project=project, name="Open", columns=["status~applies~open"]
    )
    return PullRequestStep.objects.create(project=project, filter=saved, name="Open", position=2)


def skip(client, step, reason="The maintainers met", number=None, **data):
    number = number or number_of("Ready")
    return client.post(
        f"/projects/icalendar/pull/{number}/skip/", {"step": step.pk, "reason": reason, **data}
    )


def test_a_skipped_step_moves_the_pull_request_to_the_next(client, project, steps, open_step, bob):  # noqa: F811
    _first, second = steps
    client.force_login(bob)
    answer = skip(client, second)
    assert answer.status_code == 302 and answer["Location"].endswith(f"?step={second.pk}")
    found = StepSkip.objects.get()
    assert (found.user, found.reason, found.automatic) == (bob, "The maintainers met", False)
    issue = Issue.objects.get(title="Ready")
    progress = PullRequestProgress(issue, project)
    assert progress.current.step == open_step and progress.steps[1].skip == found
    assert StepAssignment(project).step_of(issue) == open_step
    page = client.get(f"/projects/icalendar/pull/{issue.number}/").content.decode()
    box = page.split(f'data-step="{second.pk}"')[1].split("</li>")[0]
    assert "data-skipped" in box and "data-skip-mark" in box and ">0/1<" in box  # its tasks
    assert "The maintainers met" in box and "data-unskip" in box and ">Don't skip<" in box
    status = box.split('class="progress-status"')[1].split("</div>")[0]
    assert "Skipped by" in status and "data-skip-reason><p>The maintainers met</p>" in status
    assert "badge" not in status
    assert 'href="/projects/icalendar/contributors/bob/"' in box  # who, on the site
    assert "data-skip-step" not in box
    other = page.split(f'data-step="{open_step.pk}"')[1].split("</li>")[0]
    assert "The pull request is here" in other and "data-skip-step" in other
    assert 'popovertarget="skip-' in other and "popover aria-labelledby" in other
    assert "Why can the step Open be skipped?" in other and "see why" not in other
    assert client.get("/projects/icalendar/contributors/bob/").status_code == 200
    data = client.get(f"/projects/icalendar/pull/{issue.number}.json").json()
    assert data["step"] == open_step.pk and data["steps"][1]["skipped"] is True
    assert "The maintainers met" not in str(data)  # the reason is not public
    skip(client, second, remove="1")
    assert not StepSkip.objects.exists()
    assert PullRequestProgress(issue, project).current.step == second


def test_everybody_sees_the_skip_but_only_writers_the_reason(
    client,
    project,  # noqa: F811
    steps,
    open_step,
    bob,
    alice,
):
    _first, second = steps
    StepSkip.objects.create(
        step=second, issue=Issue.objects.get(title="Ready"), user=bob, reason="Secret"
    )
    for viewer in (None, alice):  # a visitor, a reader
        if viewer:
            ProjectEditor(ProjectAccess(project, bob)).share("alice", "read")
            client.force_login(alice)
        page = client.get(f"/projects/icalendar/pull/{number_of('Ready')}/").content.decode()
        box = page.split(f'data-step="{second.pk}"')[1].split("</li>")[0]
        assert "data-skip-mark" in box and "data-skipped-by" in box
        assert "Secret" not in page and "data-unskip" not in page and "data-skip-step" not in page
        assert skip(client, second).status_code in (307, 403)  # anonymous: to sign in
    assert StepSkip.objects.get().reason == "Secret"  # readers change nothing
    assert skip(client, second).status_code == 403


def test_a_skip_needs_a_reason_and_a_step(client, project, steps, bob):  # noqa: F811
    _first, second = steps
    client.force_login(bob)
    answer = skip(client, second, reason="  ")
    assert answer.status_code == 400 and "The reason to skip is missing" in (
        answer.content.decode()
    )
    answer = client.post(
        f"/projects/icalendar/pull/{number_of('Ready')}/skip/", {"step": "999", "reason": "x"}
    )
    assert answer.status_code == 404 and not StepSkip.objects.exists()


def test_a_step_skips_itself_for_its_authors(client, project, steps, open_step, bob):  # noqa: F811
    """The author octocat is in skip_authors: Skipped, without a reason or a person."""
    _first, second = steps
    client.force_login(bob)
    edit = f"/projects/icalendar/steps/{second.pk}/edit/"
    client.post(edit, {"name": "Review", "skip_form": "1", "skip_authors": "@octocat, x/y"}, **JSON)
    second.refresh_from_db()
    assert second.skip_authors == ["octocat"]
    issue = Issue.objects.get(title="Ready")
    progress = PullRequestProgress(issue, project)
    assert progress.steps[1].skip.automatic and progress.current.step == open_step
    page = client.get(f"/projects/icalendar/pull/{issue.number}/").content.decode()
    box = page.split(f'data-step="{second.pk}"')[1].split("</li>")[0]
    assert "data-skip-mark" in box and ">Skipped</div>" in box
    assert "data-skipped-by" not in box and "data-unskip" not in box and "data-skip-step" not in box
    steps_page = client.get(f"/projects/icalendar/steps/?step_id={second.pk}").content.decode()
    assert 'value="octocat"' in steps_page and "data-complete-list" in steps_page
    client.post(edit, {"name": "Review"}, **JSON)  # a form without the field keeps it
    second.refresh_from_db()
    assert second.skip_authors == ["octocat"]


def test_skipping_every_open_step_is_not_outside(project, steps, bob):  # noqa: F811
    _first, second = steps
    issue = Issue.objects.get(title="Ready")
    StepSkip.objects.create(step=second, issue=issue, user=bob, reason="Done elsewhere")
    progress = PullRequestProgress(issue, project)
    assert progress.current is None and not progress.outside
    assert [step.stage for step in progress.steps] == ["past", "past"]


def test_a_condition_of_skip_if_skips_the_step(client, project, steps, open_step):  # noqa: F811
    """Review waits for the label needs review; it is skipped when the pull request is open."""
    _first, second = steps
    second.filter.columns = ["labels~applies~present~needs review", "status~skip~open"]
    second.filter.save()
    issue = Issue.objects.get(title="Ready")
    progress = PullRequestProgress(issue, project)
    review = progress.steps[1]
    assert review.skip.automatic and review.skip.reason == "PR is open"
    assert [task.value for task in review.tasks] == ["labels~applies~present~needs review"]
    assert progress.current.step == open_step
    assert StepAssignment(project).step_of(issue) == open_step
    page = client.get(f"/projects/icalendar/pull/{issue.number}/").content.decode()
    box = page.split(f'data-step="{second.pk}"')[1].split("</li>")[0]
    assert "Skipped: <span data-skip-condition>PR is open</span>" in box
    from pycal_dashboard.services.column_results import ColumnResults

    results = ColumnResults(list(project.repositories.all()), project=project)
    assert StepAssignment(project).step_of_all(results)[issue.pk] == open_step
