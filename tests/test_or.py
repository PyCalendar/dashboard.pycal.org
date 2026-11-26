"""Conditions joined by OR: one condition of a step that holds when one of them holds."""

import pytest

from pycal_dashboard.conditions.group.column import Column
from pycal_dashboard.conditions.group.conjunction import Conjunction
from pycal_dashboard.models import Issue, PullRequestFilter, PullRequestStep
from pycal_dashboard.services.progress import PullRequestProgress

from .test_and import CONFLICT, LABEL, OPEN, SAVE, shown_columns, titles
from .test_steps import project  # noqa: F401 (fixture)

pytestmark = pytest.mark.django_db


def test_columns_joined_by_or():
    values = [f"or1~{LABEL}", OPEN, f"or1~{CONFLICT}"]
    columns = [Column.decode(value) for value in values]
    assert [(c.joined, c.operator) for c in columns] == [(1, "or"), (0, "and"), (1, "or")]
    assert [c.encode() for c in columns] == values  # the address keeps them
    first, second = Conjunction.of(columns)
    assert first.operator == "or" and first.encode() == f"{LABEL}|{CONFLICT}"
    assert first.sentence == "PR has the label needs review or PR branch is in conflict"
    assert first.summary == "Label needs review: present or Branch: conflict"
    assert second.encode() == OPEN
    # the operator is that of the first column; an OR of one is none
    mixed = Conjunction.normalized([Column.decode(f"or2~{LABEL}"), Column.decode(f"and2~{OPEN}")])
    assert [c.encode() for c in mixed] == [f"or1~{LABEL}", f"or1~{OPEN}"]
    alone = Conjunction.normalized([Column.decode(f"or3~{LABEL}"), Column.decode(CONFLICT)])
    assert [c.encode() for c in alone] == [LABEL, CONFLICT]
    assert Conjunction.either([False, None]) is None and Conjunction.either([None, True])


def test_the_filter_shows_those_that_one_condition_of_an_or_holds_for(project):  # noqa: F811
    assert titles(project, [f"and1~{LABEL}", f"and1~{CONFLICT}"]) == set()
    assert titles(project, [f"or1~{LABEL}", f"or1~{CONFLICT}"]) == {"Ready", "Conflict"}
    # with another quality check: the OR and it
    assert titles(project, [f"or1~{LABEL}", f"or1~{CONFLICT}", OPEN]) == {"Ready", "Conflict"}
    # Skip if: the step is skipped when one of them applies
    skip = ["or1~labels~skip~present~needs review", "or1~branch~skip~conflict"]
    assert titles(project, [OPEN, *skip]) == set()


def test_the_radio_choice_turns_an_and_into_an_or_and_back(client, project, bob):  # noqa: F811
    client.force_login(bob)
    three = [f"and1~{LABEL}", f"and1~{CONFLICT}", OPEN]
    data = {"name": "Review", "col": three, "on": ["0", "1", "2"]}
    page = client.get(SAVE + "?" + "&".join(f"col={c}" for c in three)).content.decode()
    head = page.split("data-and-head")[1].split("</tr>")[0]
    assert 'name="operator0" value="and" checked' in head and "All of these" in head
    assert 'name="operator" value="0"' in head  # Change, without JavaScript
    answer = client.post(SAVE, {**data, "operator0": "or", "operator": "0"})
    assert shown_columns(answer) == [f"or1~{LABEL}", f"or1~{CONFLICT}", OPEN]
    head = answer.content.decode().split("data-and-head")[1].split("</tr>")[0]
    assert 'name="operator0" value="or" checked' in head and "Any of these" in head
    assert "PR has the label needs review or PR branch is in conflict" in head
    assert 'value="Review"' in answer.content.decode()  # what was typed stays
    back = client.post(
        SAVE, {**data, "col": shown_columns(answer), "operator0": "and", "operator": "0"}
    )
    assert shown_columns(back) == three
    # another button, or saving, applies the choice, too
    invert = client.post(SAVE, {**data, "operator0": "or", "invert": "2"})
    assert shown_columns(invert)[:2] == [f"or1~{LABEL}", f"or1~{CONFLICT}"]
    client.post(SAVE, {**data, "operator0": "or"})
    saved = PullRequestFilter.objects.get(name="Review")
    assert saved.columns == [f"or1~{LABEL}", f"or1~{CONFLICT}", OPEN]
    page = client.get("/projects/icalendar/filters/").content.decode()
    assert '<span class="and-chip">OR</span>' in page


def test_the_table_keeps_the_or(client, project):  # noqa: F811
    address = "/projects/icalendar/pull-requests/?per_page=25"
    cols = f"&col=or1~{LABEL}&col={OPEN}&col=or1~{CONFLICT}"
    page = client.get(address + cols).content.decode()
    assert page.count('data-and-column="1"') == 2 and "OR 1" in page
    edited = client.get(address + cols + "&edit=2&group=status&status=closed&filter=applies")
    assert edited.status_code == 302 and "or1~status~applies~closed" in edited["Location"]


def test_an_or_is_one_quality_check_of_the_step(project):  # noqa: F811
    saved = PullRequestFilter.objects.create(
        project=project, name="Review", columns=[f"or1~{LABEL}", f"or1~{CONFLICT}", OPEN]
    )
    PullRequestStep.objects.create(project=project, filter=saved, name="Review")
    ready = Issue.objects.select_related("author", "repository").get(title="Ready")
    tasks = PullRequestProgress(ready, project).steps[0].tasks
    assert [t.value for t in tasks] == [f"{LABEL}|{CONFLICT}", OPEN]
    first = tasks[0]
    assert first.result is True
    assert first.column.sentence == "PR has the label needs review or PR branch is in conflict"
    # the evidence of those that hold
    label = Column.decode(LABEL)
    assert first.column.evidence(ready, project=project) == label.evidence(ready, project=project)
