"""The condition of the type of the author: owner, member, collaborator, contributor, ..."""

import pytest

from pycal_dashboard import errors
from pycal_dashboard.conditions import CONDITIONS
from pycal_dashboard.conditions.author_types import type_of
from pycal_dashboard.conditions.group.column import Column
from pycal_dashboard.models import Issue, Repository
from pycal_dashboard.services.repository_update import RepositoryUpdate

from .test_steps import REPO, project  # noqa: F401 (fixtures)

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("association", "found"),
    [
        ("OWNER", "owner"),
        ("MEMBER", "member"),
        ("COLLABORATOR", "collaborator"),
        ("CONTRIBUTOR", "contributor"),
        ("MANNEQUIN", "contributor"),
        ("FIRST_TIME_CONTRIBUTOR", "first_timer"),
        ("FIRST_TIMER", "first_timer"),
        ("NONE", "first_timer"),
        ("", ""),
        ("SOMETHING_NEW", ""),
    ],
)
def test_the_types_of_the_associations(association, found):
    assert type_of(association) == found


def test_the_update_keeps_the_association(github, bob):
    github.add_repository(REPO, installation=11)
    github.add_issue(REPO, "First", pull_request=True, association="FIRST_TIME_CONTRIBUTOR")
    github.add_issue(REPO, "Member", pull_request=True, association="MEMBER")
    repository = Repository.objects.create(full_name=REPO)
    assert RepositoryUpdate(repository).run()
    first, member = Issue.objects.order_by("number")
    assert (first.author_association, member.author_association) == (
        "FIRST_TIME_CONTRIBUTOR",
        "MEMBER",
    )
    condition = CONDITIONS["author_type"]
    values = condition.configure({"types": ["first_timer", "contributor"]})
    assert values["types"] == ("contributor", "first_timer")
    assert condition(values).check(first) is True
    assert condition(values).check(member) is False


def test_it_is_not_known_before_the_repository_was_read_again(project):  # noqa: F811
    issue = Issue.objects.get(title="Ready")
    Repository.objects.update(data_version=3)
    issue.refresh_from_db()
    assert CONDITIONS["author_type"]({"types": ("contributor",)}).check(issue) is None
    assert Column.decode("author_type~applies~contributor").applies(issue) is None


def test_the_inputs_are_checked():
    condition = CONDITIONS["author_type"]
    with pytest.raises(errors.ConditionInputUnknown):
        condition.configure({"types": ["bot"]})
    with pytest.raises(errors.ConditionInputMissing):
        condition.configure({"types": []})
    with pytest.raises(errors.ConditionInputUnknown):
        Column.decode("author_type~applies~bot")
    assert condition.describe()["inputs"][0]["choices"] == [
        "owner",
        "member",
        "collaborator",
        "contributor",
        "first_timer",
    ]


def test_the_column_of_the_types(project):  # noqa: F811
    Issue.objects.filter(title="Ready").update(author_association="MEMBER")
    ready, conflict = Issue.objects.get(title="Ready"), Issue.objects.get(title="Conflict")
    column = Column.decode("author_type~applies~owner~member")
    assert column.applies(ready) is True and column.applies(conflict) is False
    assert column.group.cell(ready, column.choices) == [{"text": "member", "kind": "member"}]
    assert column.group.cell(conflict, column.choices) == [
        {"text": "contributor", "kind": "contributor"}
    ]
    assert column.sentence == "PR author is an owner or a member"
    assert column.head == [
        {"text": "owner", "kind": "owner"},
        {"text": "member", "kind": "member"},
    ]
    assert column.group.summary(column.choices) == "Type of author: owner, member"
    # exclusive: the opposite is the other types
    inverted = column.inverted()
    assert inverted.choices == ("collaborator", "contributor", "first_timer")
    assert inverted.applies(conflict) is True
    evidence = column.evidence(ready)
    assert [found.url for found in evidence] == [ready.url]


def test_the_menu_has_the_switches_with_their_help(client, project):  # noqa: F811
    page = client.get("/projects/icalendar/pull-requests/").content.decode()
    fields = page.split('class="group-fields fields-author_type"')[1].split("</fieldset>")[0]
    for name in ("owner", "member", "collaborator", "contributor", "first_timer"):
        assert f'name="author_type" value="{name}"' in fields
    assert "They are exclusive" in fields
    assert "reference/conditions/author_type.html" in fields
    answer = client.get(
        "/projects/icalendar/pull-requests/?add=1&group=author_type&filter=applies"
        "&author_type=first_timer&author_type=owner"
    )
    assert answer.status_code == 302
    assert "col=author_type~applies~owner~first_timer" in answer["Location"]
