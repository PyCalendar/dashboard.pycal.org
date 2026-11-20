"""The page of a pull request: the bar of the steps with their tasks, and the tasks of a step."""

import pytest

from pycal_dashboard.models import Issue, PullRequestStep, Repository
from pycal_dashboard.services.progress import PullRequestProgress

from .test_steps import filters, project  # noqa: F401 (fixtures)

pytestmark = pytest.mark.django_db


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
    assert f'data-step="{first.pk}" data-complete="true"' in page
    assert f'data-step="{second.pk}" data-complete="false" data-current' in page
    bar = page.split("data-progress>")[1].split("</ol>")[0]
    assert bar.count("square-done") == 1 and bar.count("square-todo") == 1
    assert ">0/1<" in bar and ">1/1<" in bar
    shown = page.split("data-shown-step")[1]
    assert "Step 2: Review" in shown and "Thanks, @octocat!" in shown
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


def test_all_steps_complete(client, project, steps):  # noqa: F811
    page = client.get(f"/projects/icalendar/pull/{number_of('Merged')}/").content.decode()
    assert "data-all-done" in page and "data-current" not in page


def test_without_steps(client, project):  # noqa: F811
    page = client.get(f"/projects/icalendar/pull/{number_of('Ready')}/").content.decode()
    assert "data-no-steps" in page


def test_the_json(client, project, steps):  # noqa: F811
    _first, second = steps
    data = client.get(f"/projects/icalendar/pull/{number_of('Ready')}.json").json()
    assert data["title"] == "Ready" and data["step"] == second.pk
    assert data["steps"][1]["tasks"][0] == {
        "condition": "labels~applies~present~needs review",
        "sentence": "It has the label needs review",
        "state": "todo",
        "summary": "Review Ready",
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
