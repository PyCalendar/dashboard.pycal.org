"""Columns of conditions in the table of pull requests: added, changed, moved and filtering."""

from urllib.parse import parse_qs, urlparse

import pytest

from pycal_dashboard import errors
from pycal_dashboard.conditions.group.column import Column
from pycal_dashboard.models import Repository
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
    github.add_issue(REPO, "Behind", pull_request=True, mergeable_state="behind", auto_merge=True)
    github.add_issue(REPO, "Merged", pull_request=True, state="closed", merged=True)
    github.set_checks(REPO, 1, "SUCCESS")
    github.set_checks(REPO, 2, "FAILURE")
    repository = Repository.objects.create(full_name=REPO)
    project = ProjectEditor.create(bob, "iCalendar")
    project.repositories.add(repository)
    assert RepositoryUpdate(repository).run()
    return project


def columns_of(answer) -> list[str]:
    """The columns of the address of a redirect."""
    return parse_qs(urlparse(answer["Location"]).query).get("col", [])


def page_of(client, project, *columns: str) -> str:
    query = "&".join(f"col={c}" for c in columns)
    return client.get(f"{project.path('pull-requests/')}?{query}").content.decode()


def results(page: str) -> dict[str, list[str]]:
    """The result of each column of conditions, by the title of the pull request."""
    found = {}
    for row in page.split("<tr data-pull-request=")[1:]:
        title = row.split('class="col-title"><a href="')[1].split('">')[1].split("<")[0]
        found[title] = [part.split('"')[0] for part in row.split('data-result="')[1:]]
    return found


@pytest.mark.parametrize(
    ("form", "column"),
    [
        (
            {"group": "labels", "mode": "present", "label": "needs review"},
            "labels~all~present~needs review",
        ),
        (
            {"group": "labels", "mode": "absent", "label": "new one", "filter": "applies"},
            "labels~applies~absent~new one",
        ),
        ({"group": "branch", "branch": ["conflict", "outdated"]}, "branch~all~outdated~conflict"),
        ({"group": "ci", "ci": "failing", "filter": "not"}, "ci~not~failing"),
        ({"group": "status", "status": ["merged", "auto_merge"]}, "status~all~merged~auto_merge"),
    ],
)
def test_add_a_column(client, project, form, column):
    answer = client.get(project.path("pull-requests/"), {"add": "1", "per_page": "10", **form})
    assert answer.status_code == 302 and columns_of(answer) == [column]
    assert "per_page=10" in answer["Location"]


@pytest.mark.parametrize(
    ("form", "error"),
    [
        ({"group": "labels", "label": ""}, "An input of the condition is missing"),
        ({"group": "branch"}, "An input of the condition is missing"),
        ({"group": "status", "status": "sleeping"}, "Unknown input of the condition"),
        ({"group": "weather"}, "Unknown condition"),
        ({"group": "ci", "ci": "passing", "filter": "maybe"}, "Unknown input of the condition"),
    ],
)
def test_a_wrong_column_is_an_error(client, project, form, error):
    answer = client.get(project.path("pull-requests/"), {"add": "1", **form})
    assert answer.status_code == 400 and error in answer.content.decode()


def test_the_cells_show_whether_it_applies_and_why(client, project):
    page = page_of(
        client,
        project,
        "labels~all~present~needs%20review",
        "branch~all~up_to_date",
        "ci~all~passing",
        "status~all~open",
    )
    assert results(page) == {
        "Merged": ["no", "yes", "unknown", "no"],  # merged: up to date; no checks read
        "Behind": ["no", "no", "yes", "yes"],  # no checks: nothing failed
        "Conflict": ["no", "no", "no", "yes"],
        "Ready": ["yes", "yes", "yes", "yes"],
    }
    ready = page.split('data-pull-request="collective/icalendar#1"')[1].split("</tr>")[0]
    assert "label-chip" not in ready  # the label is in the header only
    assert 'role="img" aria-label="applies" title="applies">✓</span>' in ready
    assert '<span class="state state-up_to_date">up to date</span>' in ready
    assert '<span class="state state-passing">passing</span>' in ready
    conflict = page.split('data-pull-request="collective/icalendar#2"')[1].split("</tr>")[0]
    assert 'aria-label="does not apply" title="does not apply">✗</span>' in conflict
    assert '<span class="state state-conflict">conflict</span>' in conflict
    assert '<span class="state state-failing">failing</span>' in conflict
    behind = page.split('data-pull-request="collective/icalendar#3"')[1].split("</tr>")[0]
    assert 'state-open">open</span>, <span class="state state-auto_merge">auto-merging' in behind
    head = page.split("<thead>")[1].split("</thead>")[0]
    assert '<span class="label-chip" style="--label: #fbca04">needs review</span>' in head
    assert '<span class="state state-up_to_date">up to date</span>' in head
    assert 'title="Label needs review: present"' in head  # in words for screen readers


@pytest.mark.parametrize(
    ("column", "titles"),
    [
        ("branch~applies~outdated~conflict", ["Behind", "Conflict"]),
        ("branch~not~outdated~conflict", ["Merged", "Ready"]),
        ("status~applies~merged", ["Merged"]),
        ("labels~not~present~needs%20review", ["Merged", "Behind", "Conflict"]),
    ],
)
def test_the_filter_of_a_column(client, project, column, titles):
    page = page_of(client, project, column)
    assert list(results(page)) == titles


def test_nothing_matches(client, project):
    page = page_of(client, project, "status~applies~closed")
    assert "data-no-match" in page and "0 pull requests" in page


def test_change_move_and_remove_columns(client, project):
    base = project.path("pull-requests/") + "?col=ci~all~passing&col=status~all~open"
    answer = client.get(base + "&edit=1&group=branch&branch=outdated&filter=applies")
    assert columns_of(answer) == ["ci~all~passing", "branch~applies~outdated"]
    answer = client.get(base + "&move=1&to=0")
    assert columns_of(answer) == ["status~all~open", "ci~all~passing"]
    answer = client.get(base + "&remove=0")
    assert columns_of(answer) == ["status~all~open"]
    assert client.get(base + "&remove=7").status_code == 400


def test_the_menus_work_without_javascript(client, project):
    """The menus are details and forms of GET; CSS shows the fields of the chosen group."""
    page = page_of(client, project, "branch~all~outdated")
    add = page.split("data-add-condition>")[1].split("</details>")[0]
    assert '<input type="hidden" name="add" value="1">' in add
    assert '<input type="hidden" name="col" value="branch~all~outdated">' in add
    assert 'aria-label="Add a condition"' in page and 'aria-label="Change the column"' in page
    assert '<option value="labels">Label</option>' in add
    assert '<input id="label-new" name="label" list="label-names"' in add
    assert '<datalist id="label-names"><option value="needs review"></datalist>' in page
    gear = page.split('data-condition-column="0"')[1].split("</th>")[0]
    assert '<input type="hidden" name="edit" value="0">' in gear
    assert '<option value="branch" selected>' in gear
    assert '<input type="checkbox" name="branch" value="outdated" checked>' in gear
    assert "remove=0" in gear and "pull-table.js" in page


def test_the_json_has_the_results(client, project):
    data = client.get(
        project.path("pull-requests/").rstrip("/") + ".json?col=status~all~merged"
    ).json()
    assert data["columns"] == ["status~all~merged"]
    assert {p["title"]: p["conditions"] for p in data["pull_requests"]} == {
        "Merged": [True],
        "Behind": [False],
        "Conflict": [False],
        "Ready": [False],
    }


def test_the_column_encodes_its_choices():
    column = Column.decode("labels~applies~absent~a%7Eb%20c")
    assert column.choices == ("absent", "a~b c") and Column.decode(column.encode()) == column
    with pytest.raises(errors.UnknownCondition):
        Column.decode("weather~all")


def test_the_header_is_short(client, project):
    """Only what was chosen: an absent label struck through, no group, no filter in words."""
    page = page_of(client, project, "labels~applies~absent~needs%20review", "branch~not~conflict")
    head = page.split("<thead>")[1].split("</thead>")[0]
    heads = [
        part.split('<span aria-hidden="true">')[1].split("</span></span>")[0]
        for part in head.split('class="condition-head">')[1:]
    ]
    assert heads[0] == (
        '<span class="label-chip label-absent" style="--label: #fbca04">needs review'
    )
    assert heads[1] == '<span class="state state-conflict">conflict'
    assert "only those" not in head and "Branch:" not in heads[1]
    assert 'class="icon gear"' in head


@pytest.mark.parametrize(
    ("filter", "applies", "not_", "after_applies", "after_not"),
    [
        ("all", "true", "true", "not", "applies"),  # switch one off
        ("applies", "true", "false", "not", "all"),  # the last one on: the other one instead
        ("not", "false", "true", "all", "applies"),
    ],
)
def test_the_toggles_filter_at_once(
    client, project, filter, applies, not_, after_applies, after_not
):
    """Check marks and crosses toggle the filter; never both are off."""
    page = page_of(client, project, f"status~{filter}~open")
    yes = page.split('class="toggle toggle-yes"')[1].split(">")[0]
    no = page.split('class="toggle toggle-no"')[1].split(">")[0]
    assert f'aria-pressed="{applies}"' in yes and f'aria-pressed="{not_}"' in no
    assert f"filter_of=0&amp;filter={after_applies}" in yes
    assert f"filter_of=0&amp;filter={after_not}" in no
    answer = client.get(
        project.path("pull-requests/")
        + f"?col=status~{filter}~open&filter_of=0&filter={after_applies}"
    )
    assert columns_of(answer) == [f"status~{after_applies}~open"]


def test_a_question_mark_says_why(client, project, github):
    """Unknown results say why: closed, the permissions of the app, or not read yet."""
    from pycal_dashboard.models import Installation

    page = page_of(client, project, "ci~all~passing", "branch~all~conflict")
    merged = page.split('data-pull-request="collective/icalendar#4"')[1].split("</tr>")[0]
    assert 'title="not known: the checks are read for open pull requests only"' in merged
    Installation.objects.update(permissions={"pull_requests": "write", "contents": "read"})
    from pycal_dashboard.models import PullRequestState

    PullRequestState.objects.update(checks_complete="")
    page = page_of(client, project, "ci~all~passing")
    ready = page.split('data-pull-request="collective/icalendar#1"')[1].split("</tr>")[0]
    assert "accept the permissions checks and statuses on GitHub" in ready


def test_ci_has_three_switches(client, project):
    page = page_of(client, project, "ci~all~unknown")
    assert results(page) == {
        "Merged": ["yes"],
        "Behind": ["no"],
        "Conflict": ["no"],
        "Ready": ["no"],
    }
    add = page.split("data-add-condition>")[1]
    for name in ("passing", "failing", "unknown"):
        assert f'name="ci" value="{name}"' in add


def test_the_filters_are_an_or(client, project):
    """A pull request is shown when any column that filters shows it."""
    page = page_of(client, project, "status~applies~merged", "branch~applies~conflict")
    assert sorted(results(page)) == ["Conflict", "Merged"]
    page = page_of(client, project, "status~applies~merged", "ci~all~passing")
    assert list(results(page)) == ["Merged"]  # a column that shows both does not filter
    page = page_of(client, project, "status~all~merged", "ci~all~passing")
    assert len(results(page)) == 4  # nothing filters
