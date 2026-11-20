"""The tab PR Message: the message of a project as a comment on its pull requests."""

import pytest

from pycal_dashboard.models import (
    LogAction,
    PullRequestComment,
    PullRequestFilter,
    PullRequestMessage,
    PullRequestStep,
    Repository,
)
from pycal_dashboard.services.message_comments import MessageComments
from pycal_dashboard.services.project_editor import ProjectEditor
from pycal_dashboard.services.repository_update import RepositoryUpdate

pytestmark = pytest.mark.django_db
REPO = "collective/icalendar"


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
    saved = PullRequestFilter.objects.create(
        project=project, name="Review", columns=["labels~applies~present~needs review"]
    )
    PullRequestStep.objects.create(
        project=project,
        filter=saved,
        name="Review",
        summary="Thanks, {author_mention}!",
        conditions={"labels~applies~present~needs review": {"summary": "A person reviews it"}},
    )
    return project


def update(project):
    assert RepositoryUpdate(project.repositories.get()).run()


def save(client, **fields):
    data = {"template": "Hi {author_handle}: {step_name}\n\n{tasks_all}", "listed": ""} | fields
    return client.post("/projects/icalendar/message/", data)


def test_the_tab_is_public_and_off_by_default(client, project):
    page = client.get("/projects/icalendar/message/").content.decode()
    tabs = page.split('<ul class="tabs">')[1].split("</ul>")[0]
    assert tabs.index("Steps") < tabs.index("PR Message")
    assert "data-message-form" not in page  # visitors do not edit
    assert "data-message-rendered" in page
    assert not PullRequestMessage.objects.exists()


def test_the_page_of_a_writer(client, project, bob):
    client.force_login(bob)
    page = client.get("/projects/icalendar/message/").content.decode()
    assert "data-message-form" in page and ">Update 0 pull requests<" in page  # no scope yet
    assert 'name="to_listed" value="on" checked' in page  # on by default, without numbers
    assert 'name="to_open" value="on">' in page and 'name="to_closed" value="on">' in page
    assert 'data-variable="{tasks_todo}"' in page and "Cancel" in page


def test_save_writes_the_message_on_the_listed_pull_requests(client, github, project, bob):
    client.force_login(bob)
    answer = save(client, to_listed="on", listed="1, #2 x")
    assert answer["Location"] == "/projects/icalendar/message/"
    message = PullRequestMessage.objects.get()
    assert message.listed == ["1", "2"]
    update(project)  # the background: the update and its receivers
    bodies = {c["issue"]: c["body"] for c in github.comments.values()}
    assert set(bodies) == {f"{REPO}#1", f"{REPO}#2"}
    assert bodies[f"{REPO}#1"].startswith("Hi octocat: Review\n\n- [ ] A person reviews it")
    assert (
        "<!-- dashboard.pycal.org: the message of the project icalendar -->" in bodies[f"{REPO}#1"]
    )
    assert PullRequestComment.objects.count() == 2
    assert LogAction.objects.filter(kind="message").count() == 2
    update(project)  # nothing changed: nothing written
    assert len(github.comments) == 2 and LogAction.objects.filter(kind="message").count() == 2


def test_a_change_updates_the_comments(client, github, project, bob):
    client.force_login(bob)
    save(client, to_listed="on", listed="1")
    update(project)
    (comment,) = github.comments.values()
    save(client, to_listed="on", listed="1", template="Now: {pr_title}")
    update(project)
    assert len(github.comments) == 1 and comment["body"].startswith("Now: Ready")
    github.comments.clear()  # deleted on GitHub: written again
    save(client, to_listed="on", listed="1", template="Again")
    update(project)
    assert [c["body"].split("\n")[0] for c in github.comments.values()] == ["Again"]


@pytest.mark.parametrize(
    ("fields", "issues"),
    [
        ({"to_open": "on"}, {"#1", "#2"}),
        ({"to_closed": "on"}, {"#3"}),
        ({"to_open": "on", "to_closed": "on"}, {"#1", "#2", "#3"}),
        ({"listed": "3"}, set()),  # the switch is off
        ({}, set()),
    ],
)
def test_the_scope(client, github, project, bob, fields, issues):
    client.force_login(bob)
    save(client, **fields)
    update(project)
    assert {c["issue"].removeprefix(REPO) for c in github.comments.values()} == issues


def test_new_pull_requests(client, github, project, bob):
    client.force_login(bob)
    save(client, to_new="on")
    message = PullRequestMessage.objects.get()
    assert message.new_since is not None
    update(project)
    assert github.comments == {}  # those before are not new
    new = github.add_issue(REPO, "New", pull_request=True, updated="2099-01-01T10:00:00Z")
    new["created_at"] = "2099-01-01T09:00:00Z"  # opened after the switch
    update(project)
    assert [c["issue"] for c in github.comments.values()] == [f"{REPO}#4"]


def test_the_tasks_of_the_message(project):
    from pycal_dashboard.models import Issue

    comments = MessageComments(project)
    values = comments.values(Issue.objects.get(title="Ready"))
    assert values["tasks_todo"] == "- [ ] A person reviews it"
    assert values["tasks_done"] == "Nothing is done yet."
    assert values["step_description"] == "Thanks, @octocat!"
    outside = comments.values(Issue.objects.get(title="Conflict"))
    assert outside["tasks_all"] == "" and outside["tasks_todo"] == "Nothing to do."
    assert outside["step_name"] == ""


def test_the_live_preview(client, project, bob):
    client.force_login(bob)
    data = {"template": "**{pr_title}** {tasks_todo}", "to_open": "on", "listed": ""}
    found = client.post("/projects/icalendar/message/preview/", data).json()
    assert found["count"] == 2 and found["button"] == "Update 2 pull requests"
    assert found["pull"].startswith(f"{REPO}#")
    assert found["html"].startswith("<p><strong>")
    assert not PullRequestMessage.objects.exists()  # nothing is saved


def test_only_writers_save(client, project, alice):
    client.force_login(alice)
    assert save(client, to_open="on").status_code in (403, 404)
    assert client.post("/projects/icalendar/message/preview/", {}).status_code in (403, 404)
