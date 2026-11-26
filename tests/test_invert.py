"""Every condition can be inverted: on the page of saving a filter, in every group and type."""

import pytest

from pycal_dashboard.conditions.condition.negation import Not
from pycal_dashboard.conditions.group.column import FILTERS, GROUPS, Column
from pycal_dashboard.models import Issue

from .test_steps import project  # noqa: F401 (fixture)

pytestmark = pytest.mark.django_db
# a column of each group, as the table keeps it after <group>~<filter>~
EXAMPLES = [
    "labels~{}~present~needs review",
    "labels~{}~absent~needs review",
    "branch~{}~conflict",
    "branch~{}~outdated~conflict",
    "ci~{}~failing",
    "status~{}~open",
    "status~{}~auto_merge",
    "reviews~{}~at_least~1",
    "author~{}~reviews_given~below~2",
    "author_type~{}~contributor",
    "text~{}~title~contains~Ready",
    "text~{}~description~contains~## Checklist",
    "dashboard~{}~sync",
]
COLUMNS = [example.format(filter) for example in EXAMPLES for filter in FILTERS]


def test_every_group_has_an_example():
    assert {example.split("~")[0] for example in EXAMPLES} == set(GROUPS)


@pytest.mark.parametrize("value", COLUMNS)
def test_every_column_can_be_inverted(project, value):  # noqa: F811
    """The inverted column holds exactly where it does not; inverted again, it is the same."""
    column = Column.decode(value)
    inverted = column.inverted()
    assert inverted is not None and inverted != column
    assert inverted.inverted() == column
    assert Column.decode(inverted.encode()) == inverted  # the address keeps it
    assert inverted.kind == column.kind and inverted.active == column.active  # its type stays
    for issue in Issue.objects.filter(pull_request=True):
        holds = column.holds(column.applies(issue))
        assert inverted.holds(inverted.applies(issue)) == Not.result(holds), (value, issue)
    assert inverted.sentence != column.sentence


def test_every_condition_on_the_page_of_saving_has_invert(client, project, bob):  # noqa: F811
    """Also those that are off, and those of Skip if, as on the page of a filter of icalendar."""
    client.force_login(bob)
    address = "/projects/icalendar/filters/save/?" + "&".join(
        f"col={value.replace(' ', '+').replace('#', '%23')}" for value in COLUMNS
    )
    page = client.get(address).content.decode()
    rows = page.split('data-condition-row="')[1:]
    assert len(rows) == len(COLUMNS)
    for row in rows:
        assert 'name="invert"' in row and 'name="remove"' in row, row.split('"')[0]


def test_invert_a_condition_that_is_off_or_of_skip_if(client, project, bob):  # noqa: F811
    """The NOT of the condition: it stays off, or in Skip if, and is inverted back."""
    client.force_login(bob)
    data = {"name": "Review", "col": ["text~skip~title~contains~WIP", "ci~all~failing"]}
    answer = client.post("/projects/icalendar/filters/save/", {**data, "on": ["0"], "invert": "0"})
    page = answer.content.decode()
    assert 'value="not~text~skip~title~contains~WIP"' in page
    assert "PR title does not match: contains “WIP”" in page
    answer = client.post("/projects/icalendar/filters/save/", {**data, "on": ["0"], "invert": "1"})
    assert 'value="not~ci~all~failing"' in answer.content.decode()
    table = client.get(
        "/projects/icalendar/pull-requests/?col=not~ci~applies~failing&per_page=25"
    ).content.decode()
    assert "state-not" in table  # the header says NOT
