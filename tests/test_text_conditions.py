"""The conditions of texts: the title or the description of a pull request matches."""

import pytest

from pycal_dashboard import errors
from pycal_dashboard.conditions import CONDITIONS
from pycal_dashboard.conditions.group.column import Column
from pycal_dashboard.models import Issue

from .test_steps import project  # noqa: F401 (fixtures)

pytestmark = pytest.mark.django_db


def pull(title):
    return Issue.objects.get(title=title)


@pytest.mark.parametrize(
    ("value", "ready", "conflict"),
    [
        ("text~applies~title~starts~rea", True, False),
        ("text~applies~title~starts~Rea~case", True, False),
        ("text~applies~title~starts~rea~case", False, False),  # the case matters
        ("text~applies~title~ends~DY", True, False),
        ("text~applies~title~contains~onfl", False, True),
        ("text~applies~title~regex~^(Ready|Merged)$", True, False),
        ("text~not~title~contains~ready", False, True),
    ],
)
def test_the_title_matches(project, value, ready, conflict):  # noqa: F811
    column = Column.decode(value)
    assert column.shows(column.applies(pull("Ready"))) is ready
    assert column.shows(column.applies(pull("Conflict"))) is conflict


def test_the_description_matches(project):  # noqa: F811
    issue = pull("Ready")
    issue.description = "Fixes #12: the calendar"
    issue.save()
    assert Column.decode(r"text~applies~description~regex~Fixes #\d+").applies(issue) is True
    assert Column.decode("text~applies~description~contains~nothing").applies(issue) is False


def test_the_sentences_of_a_column():
    column = Column.decode("text~applies~title~starts~fix~case")
    assert column.sentence == "its title starts with “fix”, case sensitive"
    assert (
        column.inverted().sentence == "its title does not match: starts with “fix”, case sensitive"
    )
    assert column.head[0]["text"] == "title starts with “fix”"
    assert column.group.summary(column.choices) == "Text: title starts with “fix”"


@pytest.mark.parametrize(
    "value",
    [
        "text~applies~title~regex~(a+)+b",  # nested repetition
        "text~applies~title~regex~(x*)*",
        r"text~applies~title~regex~(a)\1",  # a back-reference
        "text~applies~title~regex~([unclosed",
        "text~applies~title~contains~" + "x" * 101,
    ],
)
def test_slow_or_wrong_patterns_are_refused(value):
    with pytest.raises(errors.TextPatternInvalid):
        Column.decode(value)


def test_the_condition_and_its_inputs():
    condition = CONDITIONS["text_matches"]
    values = condition.configure({"field": "title", "mode": "contains", "text": "wip"})
    assert values["case_sensitive"] is False
    with pytest.raises(errors.ConditionInputUnknown):
        condition.configure({"field": "body", "mode": "contains", "text": "x"})
    with pytest.raises(errors.TextPatternInvalid):
        condition.configure({"field": "title", "mode": "regex", "text": "(a+)+"})
    with pytest.raises(errors.ConditionInputUnknown):
        Column.decode("text~applies~title~starts~fix~everything")


def test_the_menu_adds_a_column_of_text(client, project):  # noqa: F811
    from urllib.parse import urlencode

    query = urlencode(
        {
            "add": "1",
            "group": "text",
            "filter": "applies",
            "text_field": "title",
            "text_mode": "starts",
            "text_value": "Rea",
        }
    )
    answer = client.get(f"/projects/icalendar/pull-requests/?{query}")
    assert answer.status_code == 302 and "col=text~applies~title~starts~Rea" in answer["Location"]
