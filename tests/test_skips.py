"""Skipping the quality checks of steps, and the links that open the dialog to skip."""

from urllib.parse import parse_qs, urlparse

import pytest

from pycal_dashboard.models import CheckSkip, Issue, StepSkip
from pycal_dashboard.services.message_comments import MessageComments
from pycal_dashboard.services.progress import PullRequestProgress
from pycal_dashboard.services.project_access import ProjectAccess
from pycal_dashboard.services.project_editor import ProjectEditor
from pycal_dashboard.services.skip_link import SkipLink
from pycal_dashboard.services.step_assignment import StepAssignment
from tests.conftest import person
from tests.fakes.github import FakeGitHub

from .test_pull_request_page import number_of, open_step, steps  # noqa: F401 (fixtures)
from .test_steps import filters, project  # noqa: F401 (fixtures)

pytestmark = pytest.mark.django_db
REVIEW = "labels~applies~present~needs review"  # the quality check of the step Review


@pytest.fixture
def ready(project):  # noqa: F811
    """The pull request Ready of octocat, in the step Review, with its quality check to do."""
    return Issue.objects.select_related("author", "repository").get(title="Ready")


@pytest.fixture
def octocat(db):
    """The author of the pull requests, signed in."""
    return person(FakeGitHub.OCTOCAT["id"], "octocat")


def page_of(ready: Issue, **query) -> str:
    return f"/projects/icalendar/pull/{ready.number}/" + (
        "?" + "&".join(f"{key}={value}" for key, value in query.items()) if query else ""
    )


def skip_check(client, step, ready, reason="Reviewed at the meeting", **data):
    return client.post(
        f"/projects/icalendar/pull/{ready.number}/skip/",
        {"step": step.pk, "skip": REVIEW, "reason": reason, **data},
    )


def test_a_skipped_quality_check_completes_the_step(
    client,
    project,  # noqa: F811
    steps,  # noqa: F811
    open_step,  # noqa: F811
    ready,
    bob,
):
    """All quality checks done or skipped: the pull request goes on to the next step."""
    _first, review = steps
    assert StepAssignment(project).step_of(ready) == review
    client.force_login(bob)
    answer = skip_check(client, review, ready)
    assert answer.status_code == 302 and answer["Location"].endswith(f"?step={review.pk}")
    found = CheckSkip.objects.get()
    assert (found.step, found.issue, found.condition, found.user) == (review, ready, REVIEW, bob)
    progress = PullRequestProgress(ready, project)
    task = progress.steps[1].tasks[0]
    assert (task.state, task.todo, progress.steps[1].complete) == ("skipped", False, True)
    assert progress.current.step == open_step and not progress.steps[1].skip
    assert progress.badge_text() == ("Open", "0/1")
    assert StepAssignment(project).step_of(ready) == open_step
    from pycal_dashboard.services.column_results import ColumnResults

    results = ColumnResults(list(project.repositories.all()), project=project)
    assert StepAssignment(project).step_of_all(results)[ready.pk] == open_step
    page = client.get(page_of(ready, step=review.pk)).content.decode()
    shown = page.split("data-tasks")[1]
    assert 'data-task="skipped"' in shown and "⏩" in shown and "data-skipped-by" in shown
    assert "<p>Reviewed at the meeting</p>" in shown and "data-unskip-check" in shown
    data = client.get(f"/projects/icalendar/pull/{ready.number}.json").json()
    assert data["steps"][1]["tasks"][0]["state"] == "skipped"
    assert data["steps"][1]["tasks"][0]["skipped"] is True and data["steps"][1]["complete"]
    assert "Reviewed at the meeting" not in str(data)  # the reason is not public
    answer = skip_check(client, review, ready, remove="1")
    assert answer.status_code == 302 and not CheckSkip.objects.exists()
    assert StepAssignment(project).step_of(ready) == review


def test_writers_see_skip_on_the_quality_checks_to_do(
    client,
    project,  # noqa: F811
    steps,  # noqa: F811
    ready,
    bob,
    alice,
):
    _first, review = steps
    client.force_login(bob)
    page = client.get(page_of(ready, step=review.pk)).content.decode()
    shown = page.split("data-tasks")[1]
    assert "data-skip-check" in shown and "popover aria-labelledby" in shown
    assert 'Why can the quality check "Review Ready" be skipped?' in shown
    assert 'popovertargetaction="hide"' in shown and "✕" in shown  # closed with ✕
    assert 'name="skip" value="labels~applies~present~needs review"' in shown
    first = client.get(page_of(ready, step=_first.pk)).content.decode()
    assert "data-skip-check" not in first.split("data-tasks")[1]  # done: nothing to skip
    ProjectEditor(ProjectAccess(project, bob)).share("alice", "read")
    client.force_login(alice)
    shown = client.get(page_of(ready, step=review.pk)).content.decode().split("data-tasks")[1]
    assert "data-skip-check" not in shown  # readers skip nothing
    answer = skip_check(client, review, ready)
    assert answer.status_code == 403 and "You may not skip this" in answer.content.decode()
    assert not CheckSkip.objects.exists()


def test_the_message_marks_skipped_quality_checks(
    project,  # noqa: F811
    steps,  # noqa: F811
    ready,
    bob,
):
    """⏩ where a quality check done has a check mark and one to do a cross."""
    _first, review = steps
    review.filter.columns = [REVIEW, "status~applies~open"]  # a second quality check, to do
    review.filter.save()
    CheckSkip.objects.create(step=review, issue=ready, condition=REVIEW, user=bob, reason="x")
    values = MessageComments(project).values(ready)
    assert values["step_name"] == "Review"  # still in it: the other quality check is to do
    chat = "Ask in [the chat](https://chat.example.org)."  # its description, below it
    assert values["tasks_all"] == f"1. :x: It is open\n2. :fast_forward: Review Ready  \n   {chat}"
    assert values["tasks_done"] == f"1. :fast_forward: Review Ready  \n   {chat}"
    assert values["tasks_todo"] == "1. :x: It is open"
    from pycal_dashboard.markdown_text import render

    assert "⏩" in render(values["tasks_done"])  # as GitHub shows it


def test_the_reason_is_markdown_without_variables(
    client,
    project,  # noqa: F811
    steps,  # noqa: F811
    ready,
    bob,
):
    _first, review = steps
    client.force_login(bob)
    skip_check(client, review, ready, reason="**Met** for {pr_title} {author_mention}")
    skip = CheckSkip.objects.get()
    assert skip.reason == "**Met** for {pr_title} {author_mention}"
    shown = client.get(page_of(ready, step=review.pk)).content.decode().split("data-tasks")[1]
    assert "<strong>Met</strong> for {pr_title} {author_mention}" in shown
    StepSkip.objects.create(step=review, issue=ready, user=bob, reason="See {pr_url} *now*")
    box = client.get(page_of(ready)).content.decode().split(f'data-step="{review.pk}"')[1]
    assert "See {pr_url} <em>now</em>" in box.split("</li>")[0]
    preview = client.post("/markdown/preview/", {"text": "{pr_title}"}).content.decode()
    assert "{pr_title}" in preview  # the preview of the dialog replaces nothing


def test_the_variables_of_the_links(
    project,  # noqa: F811
    steps,  # noqa: F811
    ready,
):
    _first, review = steps
    review.summary = "[Skip it]({step_skip_url_author}) or ({step_skip_url})"
    review.conditions = {
        REVIEW: {"summary": "Review", "description": "[Skip]({quality_check_skip_url_author})"}
    }
    review.save()
    progress = PullRequestProgress(ready, project)
    values = progress.values(progress.steps[1])
    from django.conf import settings

    page = f"{settings.SITE_URL}/projects/icalendar/pull/{ready.number}/"
    link = SkipLink(project, ready, review)
    assert values["step_skip_url"] == (
        f"{page}?repository=collective%2Ficalendar&step={review.pk}&skip=step"
    )
    assert values["step_skip_url_author"].endswith(f"&skip=step&key={link.key('step')}")
    task = progress.steps[1].tasks[0]
    query = parse_qs(urlparse(task.skip_urls["author"]).query)
    assert query["skip"] == [REVIEW] and link.valid(REVIEW, query["key"][0])
    assert "key" not in parse_qs(urlparse(task.skip_urls["writers"]).query)
    assert link.key(REVIEW) in task.description.replace("\\", "")
    assert not link.valid(REVIEW, link.key("step")) and not link.valid(REVIEW, "")
    other = SkipLink(project, Issue.objects.get(title="Conflict"), review)
    assert other.key(REVIEW) != link.key(REVIEW)  # a key for each pull request
    message = MessageComments(project).values(ready)
    assert message["step_skip_url_author"] == values["step_skip_url_author"]


def test_a_link_opens_the_dialog(
    client,
    project,  # noqa: F811
    steps,  # noqa: F811
    ready,
    bob,
    alice,
):
    """Open at once, with ✕ that goes back to the step; for each person what they may do."""
    _first, review = steps
    key = SkipLink(project, ready, review).key(REVIEW)
    address = page_of(ready, step=review.pk, skip=REVIEW, key=key)
    client.force_login(bob)
    page = client.get(address).content.decode()
    dialog = page.split("<dialog open")[1].split("</dialog>")[0]
    assert "data-skip-link" in dialog and "data-skip-submit" in dialog
    assert f'href="?step={review.pk}" aria-label="Close"' in dialog
    assert f'name="key" value="{key}"' in dialog
    assert "Why can the quality check &quot;Review Ready&quot; be skipped?" in dialog
    client.logout()
    dialog = client.get(address).content.decode().split("<dialog open")[1]
    assert "data-skip-sign-in" in dialog and "Sign in with GitHub" in dialog
    assert "data-skip-submit" not in dialog.split("</dialog>")[0]
    client.force_login(alice)  # neither a writer nor the author
    dialog = client.get(address).content.decode().split("<dialog open")[1]
    dialog = dialog.split("</dialog>")[0]
    assert "data-skip-error" in dialog and "You signed in as @alice." in dialog
    assert "data-skip-submit" not in dialog and "SkipNotAllowed" in dialog
    for wrong in ("nothing~applies~x", "step"):  # no such quality check; the step is fine
        page = client.get(page_of(ready, step=review.pk, skip=wrong)).content.decode()
        assert ("<dialog open" in page) is (wrong == "step")
    done = client.get(page_of(ready, step=_first.pk, skip="branch~applies~conflict"))
    assert "<dialog open" not in done.content.decode()  # done: nothing to skip


def test_the_author_skips_with_the_link_of_the_author(
    client,
    project,  # noqa: F811
    steps,  # noqa: F811
    open_step,  # noqa: F811
    ready,
    octocat,
):
    _first, review = steps
    link = SkipLink(project, ready, review)
    client.force_login(octocat)
    assert skip_check(client, review, ready).status_code == 403  # without the key
    assert skip_check(client, review, ready, key=link.key("step")).status_code == 403
    answer = skip_check(client, review, ready, key=link.key(REVIEW))
    assert answer.status_code == 302 and CheckSkip.objects.get().user == octocat
    answer = client.post(
        f"/projects/icalendar/pull/{ready.number}/skip/",
        {
            "step": open_step.pk,
            "reason": "Not mine",
            "key": SkipLink(project, ready, open_step).key("step"),
        },
    )
    assert answer.status_code == 302 and StepSkip.objects.get().user == octocat
    assert skip_check(client, review, ready, remove="1").status_code == 403  # writers only


def test_a_visitor_signs_in_and_the_skip_is_made(
    client,
    project,  # noqa: F811
    steps,  # noqa: F811
    ready,
    octocat,
    settings,
):
    """The reason is kept in the session while the visitor signs in with GitHub."""
    _first, review = steps
    key = SkipLink(project, ready, review).key(REVIEW)
    settings.SIGN_IN = type("SignIn", (), {"configured": True})()
    answer = skip_check(client, review, ready, reason="A typo", key=key)
    resume = f"/projects/icalendar/pull/{ready.number}/skip/resume/"
    assert answer.status_code == 307  # the form goes on to the sign in, as its button does
    assert answer["Location"] == "/accounts/github/login/?next=" + resume.replace("/", "%2F")
    assert not CheckSkip.objects.exists()
    assert client.session["skip_draft"]["reason"] == "A typo"
    client.force_login(octocat)
    answer = client.get(resume)
    assert answer.status_code == 302 and answer["Location"].endswith(f"?step={review.pk}")
    skip = CheckSkip.objects.get()
    assert (skip.user, skip.reason, skip.condition) == (octocat, "A typo", REVIEW)
    assert "skip_draft" not in client.session
    assert client.get(resume)["Location"] == page_of(ready)  # nothing asked for any more


def test_who_may_not_skip_sees_the_error_and_their_reason(
    client,
    project,  # noqa: F811
    steps,  # noqa: F811
    ready,
    alice,
    settings,
):
    _first, review = steps
    key = SkipLink(project, ready, review).key(REVIEW)
    settings.SIGN_IN = type("SignIn", (), {"configured": False})()
    answer = skip_check(client, review, ready, reason="Mine *really*", key=key)
    assert answer.status_code == 302 and answer["Location"].startswith("/accounts/login/")
    client.force_login(alice)
    answer = client.get(f"/projects/icalendar/pull/{ready.number}/skip/resume/")
    query = parse_qs(urlparse(answer["Location"]).query)
    assert query == {"step": [str(review.pk)], "skip": [REVIEW], "key": [key]}
    dialog = client.get(answer["Location"]).content.decode().split("<dialog open")[1]
    assert "data-skip-error" in dialog and "Mine *really*</textarea>" in dialog
    assert not CheckSkip.objects.exists()
    again = client.get(answer["Location"]).content.decode().split("<dialog open")[1]
    assert "Mine *really*</textarea>" not in again  # shown once


def test_a_skip_of_a_quality_check_the_step_lacks(
    client,
    project,  # noqa: F811
    steps,  # noqa: F811
    ready,
    bob,
):
    _first, review = steps
    client.force_login(bob)
    answer = client.post(
        f"/projects/icalendar/pull/{ready.number}/skip/",
        {"step": review.pk, "skip": "branch~applies~conflict", "reason": "x"},
    )
    assert answer.status_code == 404 and "Quality check not found" in answer.content.decode()
    assert skip_check(client, review, ready, reason=" ").status_code == 400
    assert not CheckSkip.objects.exists()


def test_the_old_names_of_the_links_are_changed_over(
    project,  # noqa: F811
    steps,  # noqa: F811
    ready,
):
    """{step_check_skip_url} and {step_check_skip_url_author} are now {step_skip_url} and
    {step_skip_url_author}: saved texts are changed over, and the old names still work."""
    import importlib

    from django.apps import apps

    from pycal_dashboard.models import PullRequestMessage
    from pycal_dashboard.services.restore_plan import message_fields, step_fields
    from pycal_dashboard.step_template import VARIABLES, expand

    old = "[Skip]({step_check_skip_url}) [Mine]({step_check_skip_url_author}) {pr_title}"
    new = "[Skip]({step_skip_url}) [Mine]({step_skip_url_author}) {pr_title}"
    assert "step_check_skip_url" not in VARIABLES  # not documented any more
    _first, review = steps
    review.summary = old
    review.conditions = {REVIEW: {"summary": "Review", "description": old}}
    review.save()
    message = PullRequestMessage.objects.create(project=project, template=old, draft=old)
    migration = importlib.import_module("pycal_dashboard.migrations.0038_rename_step_skip_url")
    migration.change_over(apps, None)
    review.refresh_from_db()
    message.refresh_from_db()
    assert review.summary == new and review.conditions[REVIEW]["description"] == new
    assert message.template == new and message.draft == new
    values = PullRequestProgress(ready, project).values(
        PullRequestProgress(ready, project).steps[1]
    )
    assert expand(old, values) == expand(new, values)  # the old names still work
    assert "{step_check_skip_url}" not in expand(old, values)
    restored = step_fields({"summary": old, "tasks": {REVIEW: {"description": old}}})
    assert restored["summary"] == new and restored["conditions"][REVIEW]["description"] == new
    assert message_fields({"template": old, "draft": old})["template"] == new
