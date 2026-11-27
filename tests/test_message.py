"""The tab PR Sync, Status Message: the message of a project as a comment on its pull requests."""

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


EDIT = "/projects/icalendar/message/edit/"


def save(client, template="Hi {author_handle}: {step_name}\n\n{tasks_all}", **fields):
    """Edit the message (saved as edited), choose the scope, then apply the message."""
    answer = client.post(EDIT, {"template": template})
    if answer.status_code != 302:
        return answer
    assert answer["Location"] == EDIT
    client.post("/projects/icalendar/message/scope/", {"listed": "", "save": "yes"} | fields)
    return client.post(EDIT, {"apply": "yes"})


def test_the_tab_is_public_and_off_by_default(client, project):
    page = client.get("/projects/icalendar/message/").content.decode()
    tabs = page.split('<ul class="tabs">')[1].split("</ul>")[0]
    assert tabs.index("Steps") < tabs.index("PR Sync")
    assert "data-no-message" in page and "data-edit-message" not in page  # visitors
    assert "data-message-flow" not in page
    assert not PullRequestMessage.objects.exists()
    assert client.get("/projects/icalendar/message/edit/").status_code in (302, 403, 404)


def test_the_tabs_of_editing(client, github, project, bob):
    """Current Message, Edit and Preview together, Status Label and Scope."""
    client.force_login(bob)
    page = client.get("/projects/icalendar/message/").content.decode()
    tabs = page.split("data-sync-tabs")[1].split("</ul>")[0]
    assert tabs.index("Current Message") < tabs.index("Edit") < tabs.index("Preview")
    assert tabs.index("Preview") < tabs.index("Status Label") < tabs.index("Synchronization")
    assert 'data-tab-group="edit"' in tabs  # Edit and Preview belong together
    assert "data-no-message" in page
    edit = client.get(EDIT).content.decode()
    assert "{tasks_all}" in edit and 'data-variable="{tasks_todo}"' in edit  # the default
    assert 'data-markdown-preview="/projects/icalendar/message/preview/"' in edit
    assert "message-edit.js" in edit and "data-apply" in edit and "data-save-draft" in edit
    assert (
        "data-to-preview" in edit
        and "Apply the edited message and synchronise it with 0 pull" in edit
    )
    review = client.get("/projects/icalendar/message/review/").content.decode()
    assert "data-to-edit" in review and "data-to-preview" not in review


def test_the_edited_message_is_saved_and_applied_later(client, github, project, bob, alice):
    """The edited message stays, also for the next visit, until Apply uses it."""
    client.force_login(bob)
    answer = client.post(
        EDIT, {"template": "**{pr_title}** {tasks_todo}"}, HTTP_ACCEPT="application/json"
    )
    assert answer.json() == {"saved": True, "applied": False}
    message = PullRequestMessage.objects.get()
    assert (message.template, message.draft) == ("", "**{pr_title}** {tasks_todo}")
    client.logout()
    client.force_login(bob)  # a new session: the edited message is still there
    edit = client.get(EDIT).content.decode()
    assert ">**{pr_title}** {tasks_todo}</textarea>" in edit
    review = client.get("/projects/icalendar/message/review/").content.decode()
    assert "<strong>" in review and "data-example-label" in review and "data-apply" in review
    scope = client.get("/projects/icalendar/message/scope/").content.decode()
    assert "data-not-applied" in scope and "Continue editing" in scope  # the notice
    assert (
        ">Keep 0 pull requests synchronized<" in scope
        and 'name="to_listed" value="on" checked' in scope
    )
    assert "data-no-message" in client.get("/projects/icalendar/message/").content.decode()
    client.post(
        "/projects/icalendar/message/scope/", {"listed": "", "to_open": "on", "save": "yes"}
    )
    assert github.comments == {} and PullRequestMessage.objects.get().template == ""
    answer = client.post(EDIT, {"apply": "yes"})
    assert answer["Location"] == "/projects/icalendar/message/"
    message.refresh_from_db()
    assert (message.template, message.draft) == ("**{pr_title}** {tasks_todo}", None)
    page = client.get("/projects/icalendar/message/").content.decode()
    assert (
        "<strong>" in page and "All open pull requests" in page and "data-not-applied" not in page
    )
    assert "2 pull requests with a status message." in page
    shown = page.split("data-message-preview")[1]
    assert shown.index("</div>") < shown.index("data-message-pull")  # below the message
    line = shown.split("data-message-pull>")[1].split("</p>")[0]
    assert line.startswith("This is the message as it would appear in pull request <a href=")
    assert f'href="https://github.com/{REPO}/pull/1" data-message-pull-link>{REPO}#1 <svg' in line
    assert "data-edit-message" in page.split("markdown-tabs")[1].split("</p>")[0]  # a tab
    edit = client.get(EDIT).content.decode()
    assert "data-applied data-apply-text" in edit and "✓ Applied" in edit  # nothing to apply
    answer = client.post(EDIT, {"template": "Changed"}, HTTP_ACCEPT="application/json")
    assert answer.json()["applied"] is False
    assert "data-applied data-apply-text" not in client.get(EDIT).content.decode()
    assert PullRequestMessage.objects.get().template == "**{pr_title}** {tasks_todo}"  # in use
    client.post(EDIT, {"template": "**{pr_title}** {tasks_todo}"})  # back as it was
    assert "data-not-applied" not in client.get("/projects/icalendar/message/").content.decode()


def test_the_review_steps_through_the_examples(client, project, bob):
    """From no task done to all of them; a pull request by its number; edit its step."""
    client.force_login(bob)
    client.post("/projects/icalendar/message/edit/", {"template": "{pr_title}: {tasks_todo}"})
    first = client.get("/projects/icalendar/message/review/").content.decode()
    assert "Example 1 of 2: Review, 0 of 1 quality checks done" in first  # Ready: to review
    assert "Ready: " in first and "data-edit-step-of-example" in first
    second = client.get("/projects/icalendar/message/review/?example=1").content.decode()
    assert "Example 2 of 2: outside of the steps, 1 of 1 quality checks done" in second
    assert "Nothing to do." in second
    assert 'href="?example=2" data-example-step="1" ' in second and 'aria-disabled="true"' in second
    chosen = client.get("/projects/icalendar/message/review/?pull=2").content.decode()
    assert "Conflict: " in chosen
    missing = client.get("/projects/icalendar/message/review/?pull=99").content.decode()
    assert "The project has no pull request 99." in missing
    markdown = client.get("/projects/icalendar/message/review/?view=markdown").content.decode()
    assert "data-message-markdown" in markdown
    step = PullRequestStep.objects.get()
    edit_step = first.split("data-edit-step-of-example")[0].rsplit('href="', 1)[1]
    assert edit_step.startswith(f"/projects/icalendar/steps/?step={step.pk}&amp;back=")
    page = client.get(edit_step.replace("&amp;", "&")).content.decode()
    assert "data-back-to-review" in page and 'href="/projects/icalendar/message/review/?' in page


def test_the_steps_go_back_to_this_site_only(client, project, bob):
    client.force_login(bob)
    step = PullRequestStep.objects.get()
    page = client.get(f"/projects/icalendar/steps/?step={step.pk}&back=https://evil.example/")
    assert "data-back-to-review" not in page.content.decode()


def test_save_writes_the_message_on_the_listed_pull_requests(client, github, project, bob):
    client.force_login(bob)
    answer = save(client, to_listed="on", listed="1, #2 x")
    assert answer["Location"] == "/projects/icalendar/message/"
    message = PullRequestMessage.objects.get()
    assert message.listed == ["1", "2"]
    update(project)  # the background: the update and its receivers
    bodies = {c["issue"]: c["body"] for c in github.comments.values()}
    assert set(bodies) == {f"{REPO}#1", f"{REPO}#2"}
    assert bodies[f"{REPO}#1"].startswith("Hi octocat: Review\n\n1. :x: A person reviews it")
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
    assert values["tasks_todo"] == "1. :x: A person reviews it"
    assert values["tasks_done"] == "Nothing is done yet."
    assert values["step_description"] == "Thanks, @octocat!"
    outside = comments.values(Issue.objects.get(title="Conflict"))
    assert outside["tasks_all"] == "" and outside["tasks_todo"] == "Nothing to do."
    assert outside["step_name"] == ""


def test_the_count_and_the_preview_of_the_editor(client, project, bob):
    client.force_login(bob)
    found = client.post(
        "/projects/icalendar/message/preview/", {"to_open": "on", "listed": ""}
    ).json()
    assert found == {"count": 2, "button": "Keep 2 pull requests synchronized"}
    html = client.post("/projects/icalendar/message/preview/", {"text": "**{pr_title}**"})
    assert html.content.decode().startswith("<p><strong>")
    counted = client.get("/projects/icalendar/message/scope/?count=1&to_open=on&listed=")
    assert ">Keep 2 pull requests synchronized<" in counted.content.decode()  # without JavaScript
    assert not PullRequestMessage.objects.exists()  # nothing is saved


def test_only_writers_save(client, project, alice):
    client.force_login(alice)
    assert save(client, to_open="on").status_code in (403, 404)
    assert client.post("/projects/icalendar/message/preview/", {}).status_code in (403, 404)


def test_each_example_is_in_another_state(project):
    """The same number of tasks done in other states: each is an example of its own."""
    from pycal_dashboard.services.column_results import ColumnResults
    from pycal_dashboard.services.example_pulls import ExamplePulls

    saved = PullRequestFilter.objects.get(name="Review")
    saved.columns = ["labels~applies~present~needs review", "branch~applies~conflict"]
    saved.save()
    results = ColumnResults(list(project.repositories.all()))
    examples = ExamplePulls(project, results).examples()
    titles = {
        pull.pk: pull.title for pull in project.repositories.get().issues.filter(pull_request=True)
    }
    found = [(titles[e["pk"]], e["done"], e["step"]) for e in examples]
    assert found == [  # the same tasks done, ordered by the state of each task
        ("Conflict", 1, "Review"),  # the label done, the conflict to do
        ("Ready", 1, "Review"),  # the label to do, no conflict: another state
        ("Merged", 2, ""),  # outside of the steps
    ]


def test_a_task_has_its_description_below_it(project):
    """The description of a task is on the lines below its item, indented to belong to it."""
    from pycal_dashboard.markdown_text import render
    from pycal_dashboard.models import Issue

    step = PullRequestStep.objects.get()
    step.conditions = {
        "labels~applies~present~needs review": {
            "summary": "A person reviews it",
            "description": "Ask {author_mention} in the chat.\n\n- the guide\n- the FAQ",
        }
    }
    step.save()
    values = MessageComments(project).values(Issue.objects.get(title="Ready"))
    assert values["tasks_todo"] == (
        "1. :x: A person reviews it  \n   Ask @octocat in the chat.\n\n   - the guide\n   - the FAQ"
    )
    html = render(values["tasks_all"])  # the description and its list are in the item
    assert html == (
        "<ol>\n<li>\n<p>❌ A person reviews it<br>\nAsk @octocat in the chat.</p>\n"
        "<ul>\n<li>the guide</li>\n<li>the FAQ</li>\n</ul>\n</li>\n</ol>"
    )


def test_visitors_step_through_the_stages(client, project):
    """Logged out, the saved message shows in every state of the steps, and for a number."""
    PullRequestMessage.objects.create(project=project, template="{pr_title}: {tasks_todo}")
    first = client.get("/projects/icalendar/message/").content.decode()
    assert (
        "Example 1 of 2: Review, 0 of 1 quality checks done" in first
        and "data-example-nav" in first
    )
    assert "Ready: " in first
    second = client.get("/projects/icalendar/message/?example=1").content.decode()
    assert "Example 2 of 2: outside of the steps, 1 of 1 quality checks done" in second
    chosen = client.get("/projects/icalendar/message/?pull=2").content.decode()
    assert "Conflict: " in chosen
    assert "data-edit-step-of-example" not in first  # editing the steps is for writers
    assert client.get("/projects/icalendar/message/review/").status_code == 302  # the draft


def test_the_tasks_are_numbered_with_the_emoji_of_their_state():
    """As GitHub shows them: :x: to do, :grey_question: not known, :heavy_check_mark: done."""
    from types import SimpleNamespace

    from pycal_dashboard.markdown_text import render
    from pycal_dashboard.services.message_comments import MessageComments

    def task(state, summary, description=""):
        return SimpleNamespace(state=state, summary=summary, description=description)

    tasks = [task("todo", "Ask for a review", "Assign the label."), task("done", "CI passes")]
    tasks += [task("unknown", f"Task {n}") for n in range(3, 11)]
    text = MessageComments.task_list(tasks)
    lines = text.splitlines()
    assert lines[:3] == [
        "1. :x: Ask for a review  ",
        "   Assign the label.",
        "2. :heavy_check_mark: CI passes",
    ]
    assert lines[-1] == "10. :grey_question: Task 10"
    html = render(text)
    assert html.startswith("<ol>\n<li>❌ Ask for a review<br>\nAssign the label.</li>\n<li>✔️ CI")
    assert html.count("<li>") == 10 and "❔ Task 10" in html
    assert MessageComments.task_list([]) == ""


def test_the_address_of_the_badge_changes_with_the_badge(project):
    """GitHub keeps images by their address: the message names the badge with what it shows."""
    from pycal_dashboard.models import Issue, PullRequestStep
    from pycal_dashboard.services.message_comments import MessageComments

    ready = Issue.objects.get(title="Ready")
    values = MessageComments(project).values(ready)
    first = values["pr_badge_url"]
    assert "badge.svg?repository=collective%2Ficalendar&_v=" in first
    assert values["pr_badge"].startswith(f"[![View progress]({first})](")  # stays: no state
    assert values == MessageComments(project).values(ready)  # the same: the same address
    step = PullRequestStep.objects.get()
    step.name = "Peer review"
    step.save()
    assert MessageComments(project).values(ready)["pr_badge_url"] != first


MONALISA = {"id": 777, "login": "monalisa", "avatar_url": "", "type": "User", "name": "Mona"}


def test_the_open_pull_requests_of_authors(client, github, project, bob):
    """The pull requests of people by their GitHub handles: the open ones, old and new."""
    client.force_login(bob)
    github.add_issue(REPO, "Hers", pull_request=True, user=MONALISA)  # #4, open
    github.add_issue(REPO, "Done", pull_request=True, user=MONALISA, state="closed")  # #5
    update(project)
    save(client, to_authors="on", authors="@Monalisa, not/valid")
    message = PullRequestMessage.objects.get()
    assert message.authors == ["Monalisa"] and message.to_authors
    update(project)
    assert {c["issue"] for c in github.comments.values()} == {f"{REPO}#4"}  # not the closed
    github.add_issue(REPO, "Later", pull_request=True, user=MONALISA)  # #6, opened later
    update(project)
    assert {c["issue"] for c in github.comments.values()} == {f"{REPO}#4", f"{REPO}#6"}
    page = client.get("/projects/icalendar/message/").content.decode()
    summary = page.split("data-scope-authors>")[1].split("</li>")[0]
    assert "The open pull requests of" in summary and 'data-github-user="Monalisa"' in summary
    scope = client.get("/projects/icalendar/message/scope/").content.decode()
    assert 'name="authors" value="Monalisa"' in scope
    assert 'data-complete-people="/complete/people/?project=icalendar"' in scope


@pytest.mark.parametrize(
    ("fields", "count"),
    [
        ({"to_authors": "on", "authors": "octocat"}, 2),  # #1 and #2; #3 is closed
        ({"to_authors": "on", "authors": "OCTOCAT octocat"}, 2),  # whatever the case, once
        ({"authors": "octocat"}, 0),  # the switch is off
        ({"to_authors": "on", "authors": ""}, 0),  # nobody
        ({"to_authors": "on", "authors": "octocat", "to_closed": "on"}, 3),
    ],
)
def test_the_count_of_authors(client, project, bob, fields, count):
    client.force_login(bob)
    found = client.post("/projects/icalendar/message/preview/", {"listed": ""} | fields).json()
    assert found["count"] == count


def test_the_authors_are_proposed(client, github, project, bob):
    """Typing a GitHub handle proposes the authors of the pull requests of the project first."""
    github.add_issue(REPO, "An issue", user={**MONALISA, "id": 778, "login": "monaissue"})
    github.add_issue(REPO, "Hers", pull_request=True, user=MONALISA)
    update(project)
    address = "/complete/people/?project=icalendar"
    client.force_login(bob)
    found = client.get(address + "&q=mon").json()["people"]
    assert found[0] == {
        "login": "monalisa",
        "name": "Mona",
        "avatar": "https://avatars.githubusercontent.com/monalisa?s=40",
    }
    assert [p["login"] for p in found] == ["monalisa", "monaissue"]  # the author of a PR first
    assert [p["login"] for p in client.get(address + "&q=@Oct").json()["people"]] == ["octocat"]


def test_the_preview_links_the_message_on_github(client, github, project, bob):
    """Below the message: the pull request it is of, linked to its message on GitHub."""
    client.force_login(bob)
    save(client, to_listed="on", listed="1")
    update(project)
    comment = PullRequestComment.objects.get()
    page = client.get("/projects/icalendar/message/?pull=1").content.decode()
    line = page.split("data-message-pull>")[1].split("</p>")[0]
    url = f"https://github.com/{REPO}/pull/1#issuecomment-{comment.github_id}"
    assert f'<a href="{url}" data-message-pull-link>{REPO}#1 <svg' in line


def test_the_fixed_address_of_the_message(client, github, project, bob, settings):
    """{pr_message_url}: the message on GitHub, else the pull request; the address stays."""
    from pycal_dashboard.models import Issue
    from pycal_dashboard.step_template import values_of

    settings.SITE_URL = "https://dashboard.example.org"
    pull = Issue.objects.select_related("author", "repository").get(number=1)
    url = values_of(pull, project)["pr_message_url"]
    assert url == (
        "https://dashboard.example.org/projects/icalendar/pull/1/message/"
        "?repository=collective%2Ficalendar"
    )
    address = url.removeprefix(settings.SITE_URL)
    answer = client.get(address)  # public, like the project; no message yet: the pull request
    assert answer.status_code == 302 and answer["Location"] == f"https://github.com/{REPO}/pull/1"
    client.force_login(bob)
    save(client, to_listed="on", listed="1", template="[The status]({pr_message_url})")
    update(project)
    comment = PullRequestComment.objects.get()
    (written,) = github.comments.values()
    from pycal_dashboard.markdown_text import render

    assert f'href="{url.replace("&", "&amp;")}"' in render(written["body"])  # a link to it
    client.logout()
    answer = client.get(address)
    assert (
        answer["Location"] == f"https://github.com/{REPO}/pull/1#issuecomment-{comment.github_id}"
    )
    assert client.get("/projects/icalendar/pull/1/message/")["Location"] == answer["Location"]
    assert client.get("/projects/icalendar/pull/99/message/").status_code == 404


def test_an_autosave_at_the_same_time_as_apply_keeps_the_applied_message(
    client, project, bob, monkeypatch
):
    """The click on Apply leaves the field, which saves it: the two requests come together.

    The autosave loaded the message before Apply saved it; it writes the draft alone, so the
    applied message stays, and the scope saved meanwhile, too.
    """
    from pycal_dashboard.views import message as views

    client.force_login(bob)
    client.post(EDIT, {"template": "Old"}, HTTP_ACCEPT="application/json")
    client.post(EDIT, {"apply": "yes"})
    stale = PullRequestMessage.objects.get()  # what the autosave loaded, before Apply
    client.post(EDIT, {"template": "New", "apply": "yes"})  # Apply, with the latest text
    PullRequestMessage.objects.update(to_open=True)  # the scope, saved meanwhile
    monkeypatch.setattr(views, "saved_message", lambda project: stale)
    answer = client.post(EDIT, {"template": "New"}, HTTP_ACCEPT="application/json")
    assert answer.json()["saved"]
    message = PullRequestMessage.objects.get()
    assert (message.template, message.draft, message.to_open) == ("New", "New", True)


def test_preview_or_edit_comes_before_apply(client, project, bob):
    """Apply is the last button at the bottom of Edit and of the review."""
    client.force_login(bob)
    edit = client.get(EDIT).content.decode().split("data-apply-form")[1]
    assert edit.index("data-to-preview") < edit.index("data-apply ")
    review = client.get("/projects/icalendar/message/review/").content.decode()
    review = review.split("data-apply-form")[1]
    assert review.index("data-to-edit") < review.index("data-apply ")
