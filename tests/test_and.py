"""Conditions joined by AND: one condition of a step, made on the page of saving a filter."""

from urllib.parse import parse_qs, urlparse

import pytest

from pycal_dashboard.conditions.group.column import Column
from pycal_dashboard.conditions.group.conjunction import Conjunction
from pycal_dashboard.models import CheckSkip, Issue, PullRequestFilter, PullRequestStep
from pycal_dashboard.services.column_results import ColumnResults
from pycal_dashboard.services.progress import PullRequestProgress
from pycal_dashboard.services.step_assignment import StepAssignment

from .test_steps import project  # noqa: F401 (fixture)

pytestmark = pytest.mark.django_db
LABEL = "labels~applies~present~needs review"
OPEN = "status~applies~open"
CONFLICT = "branch~applies~conflict"
SAVE = "/projects/icalendar/filters/save/"


def titles(project, values: list[str]) -> set[str]:  # noqa: F811
    results = ColumnResults(list(project.repositories.all()), project=project)
    found = results.matching([Column.decode(value) for value in values])
    return set(Issue.objects.filter(pk__in=found).values_list("title", flat=True))


def columns_of(answer) -> list[str]:
    """The columns of the address that a change redirects to."""
    assert answer.status_code == 302
    return parse_qs(urlparse(answer["Location"]).query)["col"]


def shown_columns(answer) -> list[str]:
    page = answer.content.decode().split("data-original-filter")[0]
    return [
        part.split('"')[0] for part in page.split('<input type="hidden" name="col" value="')[1:]
    ]


def test_columns_joined_by_and():
    values = [f"and1~{LABEL}", CONFLICT, f"and1~{OPEN}"]
    columns = [Column.decode(value) for value in values]
    assert [c.joined for c in columns] == [1, 0, 1]
    assert [c.encode() for c in columns] == values  # the address keeps them
    first, second = Conjunction.of(columns)
    assert first.encode() == f"{LABEL}&{OPEN}" and second.encode() == CONFLICT
    assert first.sentence == "PR has the label needs review and PR is open"
    assert first.checks and not first.skips and first.kind == "check"
    alone = Conjunction.normalized([Column.decode(f"and3~{LABEL}"), Column.decode(CONFLICT)])
    assert [c.encode() for c in alone] == [LABEL, CONFLICT]  # an AND of one is none
    # the types stay apart: a condition of Skip if is in no AND of the quality checks
    mixed = Conjunction.normalized(
        [Column.decode(f"and2~{LABEL}"), Column.decode("and2~status~skip~open")]
    )
    assert [c.joined for c in mixed] == [0, 0]
    assert Conjunction.combined([True, None]) is None
    assert Conjunction.combined([None, False]) is False


def test_the_filter_shows_those_that_all_conditions_of_an_and_hold_for(project):  # noqa: F811
    assert titles(project, [LABEL, CONFLICT]) == {"Ready", "Conflict"}  # an OR
    assert titles(project, [f"and1~{LABEL}", f"and1~{CONFLICT}"]) == set()
    assert titles(project, [f"and1~{LABEL}", f"and1~{OPEN}"]) == {"Ready"}
    # as each condition filters: those it does not apply to
    assert titles(project, [f"and1~{OPEN}", "and1~labels~not~present~needs review"]) == {"Conflict"}
    # a condition that is off is no part of it
    assert titles(project, [f"and1~{LABEL}", f"and1~{CONFLICT}".replace("applies", "all")]) == {
        "Ready"
    }
    # Skip if: the step is skipped when all of them apply
    skip = ["and1~status~skip~open", "and1~labels~skip~present~needs review"]
    assert titles(project, [OPEN, *skip]) == {"Conflict"}
    assert titles(project, [OPEN, "and1~status~skip~open", "and1~branch~skip~conflict"]) == {
        "Ready"
    }


def test_join_and_take_out_on_the_page_of_saving(client, project, bob):  # noqa: F811
    client.force_login(bob)
    data = {"name": "Review", "col": [LABEL, CONFLICT, OPEN], "on": ["0", "1", "2"]}
    page = client.get(SAVE + f"?col={LABEL}&col={CONFLICT}&col={OPEN}").content.decode()
    assert page.count("data-join hidden") == 1  # the first one has nothing above it
    assert "AND with the one above" in page and "data-and-head" not in page
    answer = client.post(SAVE, {**data, "join": "1"})  # with the one above
    assert shown_columns(answer) == [f"and1~{LABEL}", f"and1~{CONFLICT}", OPEN]
    page = answer.content.decode()
    head = page.split("data-and-head")[1].split("</tr>")[0]
    assert "All of these, as one condition:" in head
    assert "PR has the label needs review and PR branch is in conflict" in head
    assert "Invert" not in head and "Remove" not in head  # the AND is not inverted itself
    members = page.split('class="and-member')
    assert len(members) == 3 and "data-unjoin" in members[1] and "Invert" in members[1]
    assert 'value="Review"' in page  # what was typed stays
    # dragged onto the AND: the third one joins it, also from below another one
    joined = client.post(SAVE, {**data, "col": shown_columns(answer), "join": "2", "to": "0"})
    three = [f"and1~{LABEL}", f"and1~{CONFLICT}", f"and1~{OPEN}"]
    assert shown_columns(joined) == three
    out = client.post(SAVE, {**data, "col": three, "unjoin": "0"})
    assert shown_columns(out) == [LABEL, f"and1~{CONFLICT}", f"and1~{OPEN}"]
    alone = client.post(
        SAVE, {**data, "col": [LABEL, f"and1~{CONFLICT}", f"and1~{OPEN}"], "unjoin": "2"}
    )
    assert shown_columns(alone) == [LABEL, CONFLICT, OPEN]  # an AND of one is none
    # without the switches of a form: the address, as a link
    answer = client.get(SAVE + f"?col={LABEL}&col={CONFLICT}&join=1")
    assert columns_of(answer) == [f"and1~{LABEL}", f"and1~{CONFLICT}"]


def test_join_between_the_quality_checks_and_skip_if(client, project, bob):  # noqa: F811
    client.force_login(bob)
    data = {"name": "Review", "col": [LABEL, "status~skip~open"], "on": ["0", "1"]}
    answer = client.post(SAVE, {**data, "join": "1", "to": "0"})  # Skip if onto the check
    assert shown_columns(answer) == [f"and1~{LABEL}", f"and1~{OPEN}"]
    answer = client.post(SAVE, {**data, "join": "0", "to": "1"})  # the check onto Skip if
    assert shown_columns(answer) == [
        "and1~status~skip~open",
        "and1~labels~skip~present~needs review",
    ]
    # out to the other type: out of the AND
    both = [f"and1~{LABEL}", f"and1~{OPEN}", CONFLICT]
    answer = client.post(SAVE, {**data, "col": both, "on": ["0", "1", "2"], "skip": "1"})
    assert shown_columns(answer) == [LABEL, "status~skip~open", CONFLICT]
    # the one above: of its own type
    answer = client.post(
        SAVE,
        {**data, "col": [LABEL, "status~skip~open", CONFLICT], "on": ["0", "1", "2"], "join": "2"},
    )
    assert shown_columns(answer) == [f"and1~{LABEL}", f"and1~{CONFLICT}", "status~skip~open"]
    page = answer.content.decode()
    checks = page.split('data-section="checks"')[1].split("</tbody>")[0]
    assert "data-and-head" in checks and checks.count('class="and-member') == 2


def test_saving_keeps_the_and(client, project, bob):  # noqa: F811
    client.force_login(bob)
    three = [f"and1~{LABEL}", OPEN, f"and1~{CONFLICT}"]
    answer = client.post(SAVE, {"name": "Both", "col": three, "on": ["0", "1", "2"], "save": "new"})
    assert answer.status_code == 302
    saved = PullRequestFilter.objects.get(name="Both")
    assert saved.columns == three
    # off and on again, and saved while editing: still joined
    client.post(
        SAVE, {"name": "Both", "col": three, "on": ["1", "2"], "saved": saved.pk, "save": "this"}
    )
    saved.refresh_from_db()
    assert saved.columns == [f"and1~{LABEL}".replace("applies", "all"), OPEN, f"and1~{CONFLICT}"]
    page = client.get(SAVE + f"?saved={saved.pk}&" + "&".join(f"col={c}" for c in saved.columns))
    assert "data-and-head" in page.content.decode()
    listed = client.get("/projects/icalendar/filters/").content.decode()
    assert listed.count('<span class="and-chip">AND</span>') == 0  # one of them is off
    client.post(
        SAVE,
        {"name": "Both", "col": three, "on": ["0", "1", "2"], "saved": saved.pk, "save": "this"},
    )
    listed = client.get("/projects/icalendar/filters/").content.decode()
    assert listed.count('<span class="and-chip">AND</span>') == 1  # before the second of it


def test_the_table_keeps_the_and(client, project):  # noqa: F811
    address = "/projects/icalendar/pull-requests/?per_page=25"
    cols = f"&col=and1~{LABEL}&col={CONFLICT}&col=and1~{OPEN}"
    page = client.get(address + cols).content.decode()
    assert page.count('data-and-column="1"') == 2
    # the toggle of the crosses, the menu of a column, moving: the AND stays
    toggled = client.get(address + cols + "&filter_of=0&filter=all")
    assert columns_of(toggled)[0] == f"and1~{LABEL}".replace("applies", "all")
    edited = client.get(address + cols + "&edit=2&group=status&status=closed&filter=applies")
    assert columns_of(edited)[2] == "and1~status~applies~closed"
    moved = client.get(address + cols + "&move=2&to=0")
    assert columns_of(moved) == [f"and1~{OPEN}", f"and1~{LABEL}", CONFLICT]
    removed = client.get(address + cols + "&remove=0")
    assert columns_of(removed) == [CONFLICT, OPEN]  # an AND of one is none


@pytest.fixture
def step(project):  # noqa: F811
    """The step Review: Ready has the label and is open; Conflict is open, without it."""
    saved = PullRequestFilter.objects.create(
        project=project, name="Review", columns=[f"and1~{LABEL}", f"and1~{OPEN}", CONFLICT]
    )
    return PullRequestStep.objects.create(
        project=project,
        filter=saved,
        name="Review",
        conditions={f"{LABEL}&{OPEN}": {"summary": "Review {pr_title}", "description": "Now."}},
    )


def test_an_and_is_one_quality_check_of_the_step(client, project, step, bob):  # noqa: F811
    ready = Issue.objects.select_related("author", "repository").get(title="Ready")
    progress = PullRequestProgress(ready, project)
    tasks = progress.steps[0].tasks
    assert [t.value for t in tasks] == [f"{LABEL}&{OPEN}", CONFLICT]
    first = tasks[0]
    assert (first.state, first.result, first.summary) == ("todo", True, "Review Ready")
    assert first.column.sentence == "PR has the label needs review and PR is open"
    columns = first.column.columns
    assert first.column.evidence(ready, project=project) == [
        found for column in columns for found in column.evidence(ready, project=project)
    ]
    assert StepAssignment(project).step_of(ready) == step
    conflict = Issue.objects.get(title="Conflict")
    found = PullRequestProgress(conflict, project).steps[0].tasks
    assert [(t.value, t.state) for t in found] == [(CONFLICT, "todo"), (f"{LABEL}&{OPEN}", "done")]
    page = client.get(f"/projects/icalendar/pull/{ready.number}/").content.decode()
    assert "PR has the label needs review and PR is open" in page and "Review Ready" in page
    data = client.get(f"/projects/icalendar/pull/{ready.number}.json").json()
    assert data["steps"][0]["tasks"][0]["condition"] == f"{LABEL}&{OPEN}"
    # the page of the step: one condition, its summary and description edited as one
    client.force_login(bob)
    steps = client.get(f"/projects/icalendar/steps/?step={step.pk}").content.decode()
    assert steps.count("data-step-condition=") == 2
    assert f'name="value-0" value="{LABEL}&amp;{OPEN}"' in steps
    client.post(
        f"/projects/icalendar/steps/{step.pk}/edit/",
        {
            "name": "Review",
            "value-0": f"{LABEL}&{OPEN}",
            "summary-0": "Look at it",
            "description-0": "Soon.",
            "value-1": CONFLICT,
            "summary-1": "Solve it",
        },
    )
    step.refresh_from_db()
    assert step.conditions[f"{LABEL}&{OPEN}"] == {"summary": "Look at it", "description": "Soon."}
    assert step.conditions[CONFLICT]["summary"] == "Solve it"


def test_skip_an_and(client, project, step, bob):  # noqa: F811
    ready = Issue.objects.get(title="Ready")
    client.force_login(bob)
    answer = client.post(
        f"/projects/icalendar/pull/{ready.number}/skip/",
        {"step": step.pk, "skip": f"{LABEL}&{OPEN}", "reason": "Reviewed at the meeting"},
    )
    assert answer.status_code == 302
    assert CheckSkip.objects.get().condition == f"{LABEL}&{OPEN}"
    progress = PullRequestProgress(Issue.objects.get(title="Ready"), project)
    assert progress.steps[0].tasks[0].state == "skipped" and progress.steps[0].complete
    assert StepAssignment(project).step_of(ready) is None
    # its link opens the dialog of the AND
    link = progress.steps[0].tasks[0].skip_urls["writers"]
    assert parse_qs(urlparse(link).query)["skip"] == [f"{LABEL}&{OPEN}"]
    dialog = client.get(urlparse(link).path + "?" + urlparse(link).query).content.decode()
    assert (
        "data-skip-link" in dialog or "Don&#x27;t skip" in dialog or "data-unskip-check" in dialog
    )
    # a single condition of the AND is no quality check of its own
    answer = client.post(
        f"/projects/icalendar/pull/{ready.number}/skip/",
        {"step": step.pk, "skip": LABEL, "reason": "No"},
    )
    assert answer.status_code == 404


def test_skip_if_an_and_applies(project):  # noqa: F811
    saved = PullRequestFilter.objects.create(
        project=project,
        name="Open",
        columns=[OPEN, "and1~status~skip~open", "and1~labels~skip~present~needs review"],
    )
    PullRequestStep.objects.create(project=project, filter=saved, name="Open")
    ready = Issue.objects.select_related("author", "repository").get(title="Ready")
    conflict = Issue.objects.select_related("author", "repository").get(title="Conflict")
    assert StepAssignment(project).step_of(ready) is None
    assert StepAssignment(project).step_of(conflict).name == "Open"
    skip = PullRequestProgress(ready, project).steps[0].skip
    assert skip.reason == "PR is open and PR has the label needs review"


def test_the_buttons_of_an_and_forward_what_was_typed(client, project, bob):  # noqa: F811
    """A drop presses a button that sends the form: the page comes again with all of it."""
    client.force_login(bob)
    saved = PullRequestFilter.objects.create(project=project, name="Review", columns=[LABEL])
    data = {
        "name": "Typed name",
        "description": "Typed *description*",
        "saved": saved.pk,
        "col": [LABEL, CONFLICT, OPEN],
        "on": ["0", "1"],  # the third one is switched off
        "join": "2",
        "to": "0",  # dropped onto the first one
    }
    answer = client.post(SAVE, data)
    assert answer.status_code == 200  # the page again, not saved
    assert shown_columns(answer) == [
        f"and1~{LABEL}",
        f"and1~{OPEN}".replace("applies", "all"),
        CONFLICT,
    ]
    page = answer.content.decode()
    assert 'value="Typed name"' in page and "Typed *description*</textarea>" in page
    assert f'<input type="hidden" name="saved" value="{saved.pk}">' in page
    assert 'data-state="unsaved"' in page  # nothing is saved by the button
    saved.refresh_from_db()
    assert (saved.name, saved.columns) == ("Review", [LABEL])
    # the switch that was off stays off in the AND, those that were on stay on
    rows = {row.split('"')[0]: row for row in page.split('data-condition-row="')[1:]}
    assert 'class="off and-member' in rows["1"] and "off" not in rows["0"].split(">")[0]
    taken = client.post(
        SAVE, {**data, "col": shown_columns(answer), "on": ["0", "2"], "join": [], "unjoin": "1"}
    )
    assert shown_columns(taken) == [LABEL, OPEN.replace("applies", "all"), CONFLICT]
    assert 'value="Typed name"' in taken.content.decode()


def test_the_links_of_an_and_forward_the_address(client, project, bob):  # noqa: F811
    """Without a form, a link changes the conditions: the size and the filter stay."""
    client.force_login(bob)
    saved = PullRequestFilter.objects.create(project=project, name="Review", columns=[LABEL])
    answer = client.get(
        SAVE + f"?col={LABEL}&col={CONFLICT}&per_page=50&saved={saved.pk}&join=1&to=0"
    )
    query = parse_qs(urlparse(answer["Location"]).query)
    assert query == {
        "col": [f"and1~{LABEL}", f"and1~{CONFLICT}"],
        "per_page": ["50"],
        "saved": [str(saved.pk)],
    }
    table = client.get(
        "/projects/icalendar/pull-requests/"
        f"?col=and1~{LABEL}&col=and1~{OPEN}&per_page=50&saved={saved.pk}&filter_of=1&filter=not"
    )
    query = parse_qs(urlparse(table["Location"]).query)
    assert query == {
        "col": [f"and1~{LABEL}", "and1~status~not~open"],
        "per_page": ["50"],
        "saved": [str(saved.pk)],
    }
    # the page of saving links back to the table with the AND
    page = client.get(SAVE + f"?col=and1~{LABEL}&col=and1~{OPEN}").content.decode()
    back = page.split("data-back")[0].rsplit('href="', 1)[1].split('"')[0].replace("&amp;", "&")
    assert parse_qs(urlparse(back).query)["col"] == [f"and1~{LABEL}", f"and1~{OPEN}"]


def test_the_skip_of_an_and_is_forwarded_through_the_sign_in(
    client,
    project,  # noqa: F811
    step,
    settings,
):
    """Its value has ``&``: the link, the dialog, the sign in and the resume keep it whole."""
    from pycal_dashboard.services.skip_link import SkipLink
    from tests.conftest import person
    from tests.fakes.github import FakeGitHub

    value = f"{LABEL}&{OPEN}"
    ready = Issue.objects.select_related("author", "repository").get(title="Ready")
    link = SkipLink(project, ready, step).url(value, author=True)
    query = parse_qs(urlparse(link).query)
    assert query["skip"] == [value] and query["key"] == [SkipLink(project, ready, step).key(value)]
    dialog = client.get(urlparse(link).path + "?" + urlparse(link).query).content.decode()
    form = dialog.split("<dialog open")[1].split("</dialog>")[0]
    assert f'name="skip" value="{LABEL}&amp;{OPEN}"' in form and "data-skip-sign-in" in form
    assert "Why can the quality check" in form
    settings.SIGN_IN = type("SignIn", (), {"configured": True})()
    answer = client.post(
        f"/projects/icalendar/pull/{ready.number}/skip/",
        {
            "step": step.pk,
            "skip": value,
            "key": query["key"][0],
            "reason": "Seen",
            "repository": "collective/icalendar",
        },
    )
    assert answer.status_code == 307
    assert client.session["skip_draft"]["target"] == value
    octocat = person(FakeGitHub.OCTOCAT["id"], "octocat")  # the author
    client.force_login(octocat)
    answer = client.get(f"/projects/icalendar/pull/{ready.number}/skip/resume/")
    assert answer.status_code == 302
    skip = CheckSkip.objects.get()
    assert (skip.condition, skip.reason, skip.user) == (value, "Seen", octocat)


def test_place_a_condition_between_others(client, project, bob):  # noqa: F811
    """A drop between two conditions moves it there, also out of its AND and into Skip if."""
    client.force_login(bob)
    data = {"name": "Review", "col": [LABEL, CONFLICT, OPEN], "on": ["0", "1", "2"]}
    moved = client.post(SAVE, {**data, "place": "2", "to": "0", "section": "checks"})
    assert shown_columns(moved) == [OPEN, LABEL, CONFLICT]
    # where it was picked up, before or after itself: nothing changes
    for to in ("1", "2"):
        same = client.post(SAVE, {**data, "place": "1", "to": to, "section": "checks"})
        assert shown_columns(same) == [LABEL, CONFLICT, OPEN], to
    end = client.post(SAVE, {**data, "place": "0", "to": "", "section": "checks"})
    assert shown_columns(end) == [CONFLICT, OPEN, LABEL]  # the end of the section
    skip = client.post(SAVE, {**data, "place": "0", "to": "", "section": "skip"})
    assert shown_columns(skip) == [CONFLICT, OPEN, "labels~skip~present~needs review"]
    # out of its AND, between two conditions
    three = [f"and1~{LABEL}", f"and1~{CONFLICT}", OPEN]
    out = client.post(SAVE, {**data, "col": three, "place": "0", "to": "2", "section": "checks"})
    assert shown_columns(out) == [CONFLICT, LABEL, OPEN]  # the AND of one is none
    page = out.content.decode()
    checks = page.split('data-section="checks"')[1].split("</tbody>")[0]
    # a gap before each condition, and the end of the section
    assert checks.count("data-gap") == 4 and 'data-gap data-before=""' in checks
    joined = client.get(SAVE + "?" + "&".join(f"col={c}" for c in three)).content.decode()
    gaps = joined.split('data-section="checks"')[1].split("</tbody>")[0].count("data-gap")
    assert gaps == 3  # none inside the AND
