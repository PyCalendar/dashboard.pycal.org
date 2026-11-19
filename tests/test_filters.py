"""Saved filters of pull requests: saved from the table, listed on the tab Filters, opened again."""

import pytest

from pycal_dashboard.models import PullRequestFilter, Repository
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
    return project


COLUMNS = ["status~applies~open", "labels~not~present~needs review", "branch~all~conflict"]


def save_page(client, *columns: str, saved: int | None = None) -> str:
    query = "&".join(f"col={c}" for c in columns) + (f"&saved={saved}" if saved else "")
    return client.get(f"/projects/icalendar/filters/save/?{query}").content.decode()


def test_the_table_has_save(client, project, bob):
    page = client.get("/projects/icalendar/pull-requests/?col=status~applies~open").content
    assert b"data-save" not in page  # visitors do not save
    assert b"data-json" not in page  # the JSON is in the reference, not a button
    client.force_login(bob)
    page = client.get("/projects/icalendar/pull-requests/?col=status~applies~open").content.decode()
    assert (
        'href="/projects/icalendar/filters/save/?col=status~applies~open&amp;per_page=25" data-save'
        in page
    )


def test_the_save_page_shows_the_conditions_in_one_table(client, project, bob):
    client.force_login(bob)
    page = save_page(client, *COLUMNS)
    assert "← Back to the pull requests" in page
    assert 'href="/projects/icalendar/pull-requests/?col=status~applies~open' in page
    assert "The filter shows 3 pull requests now:" in page  # open, or without the label
    table = page.split("data-filter-summary>")[1].split("</table>")[0]
    rows = table.split("<tr data-condition-row=")[1:]
    assert len(rows) == 3 and "data-summary" not in page  # one table, not three
    assert "Status: open" in rows[0] and "Label needs review: present" in rows[1]
    assert 'name="on" value="0" checked' in rows[0] and 'name="on" value="1" checked' in rows[1]
    assert 'name="on" value="2">' in rows[2] and 'class="off"' in rows[2]  # shows both: off
    assert "those it does not apply to" in rows[1] and "data-opposite" in rows[1]
    assert "Label needs review: absent" in rows[1] and "&amp;swap=1" in rows[1]
    assert page.count('<input type="hidden" name="col"') == 3


def test_a_condition_switched_off_does_not_filter(client, project, bob):
    client.force_login(bob)
    data = {"col": COLUMNS, "name": "Open", "on": ["0", "2"], "save": "new"}
    client.post("/projects/icalendar/filters/save/", data)
    assert PullRequestFilter.objects.get().columns == [
        "status~applies~open",
        "labels~all~present~needs review",  # off: a column that shows all
        "branch~applies~conflict",  # on: those it applies to
    ]


def test_use_the_opposite(client, project, bob):
    client.force_login(bob)
    answer = client.get(
        "/projects/icalendar/filters/save/?" + "&".join(f"col={c}" for c in COLUMNS) + "&swap=1"
    )
    assert answer.status_code == 302
    assert "col=labels~applies~absent~needs+review" in answer["Location"]


def test_save_a_filter_and_open_it(client, project, bob):
    client.force_login(bob)
    data = {
        "col": COLUMNS,
        "name": " Ready  to merge ",
        "description": "**Open** ones",
        "on": ["0", "1"],
        "save": "new",
    }
    answer = client.post("/projects/icalendar/filters/save/", data)
    assert answer.status_code == 302 and answer["Location"] == "/projects/icalendar/filters/"
    saved = PullRequestFilter.objects.get()
    assert (saved.name, saved.columns, saved.created_by) == ("Ready to merge", COLUMNS, bob)
    client.logout()
    page = client.get("/projects/icalendar/filters/").content.decode()  # public
    item = page.split('data-filter="Ready to merge"')[1].split("</li>\n</ul>")[0]
    assert "<strong>Open</strong> ones" in item and "3 conditions" in item
    counts = client.get(f"/projects/icalendar/filters/{saved.pk}/?fragment=1").content.decode()
    assert "The filter shows 3 pull requests." in counts  # counted when opened
    assert "<!doctype" not in counts  # the part alone
    assert f'data-counts="/projects/icalendar/filters/{saved.pk}/?fragment=1"' in item
    link = item.split("data-filter-pull-requests")[0].rsplit('href="', 1)[1].split('"')[0]
    assert f"saved={saved.pk}" in link
    table = client.get(f"/projects/icalendar/pull-requests/?saved={saved.pk}").content.decode()
    assert "Ready to merge: 3 pull requests" in table  # the columns of the filter
    data = client.get("/projects/icalendar/filters.json").json()["filters"]
    assert data[0]["name"] == "Ready to merge" and data[0]["count"] == 3


def test_save_it_again_or_as_a_new_one(client, project, bob):
    client.force_login(bob)
    saved = PullRequestFilter.objects.create(
        project=project, name="Open", columns=["status~applies~open"]
    )
    page = save_page(client, "status~applies~merged", saved=saved.pk)
    assert "Save Open" in page and "Save as a new filter" in page and 'value="Open"' in page
    client.post(
        "/projects/icalendar/filters/save/",
        {
            "col": ["status~applies~merged"],
            "saved": saved.pk,
            "name": "Merged",
            "on": "0",
            "save": "this",
        },
    )
    saved.refresh_from_db()
    assert (saved.name, saved.columns) == ("Merged", ["status~applies~merged"])
    client.post(
        "/projects/icalendar/filters/save/",
        {
            "col": ["status~applies~open"],
            "saved": saved.pk,
            "name": "Open",
            "on": "0",
            "save": "new",
        },
    )
    assert sorted(PullRequestFilter.objects.values_list("name", flat=True)) == ["Merged", "Open"]


def test_names_are_unique_in_a_project(client, project, bob):
    client.force_login(bob)
    PullRequestFilter.objects.create(project=project, name="Open")
    answer = client.post("/projects/icalendar/filters/save/", {"name": "Open", "save": "new"})
    assert (
        answer.status_code == 409
        and "The project has a filter of this name" in answer.content.decode()
    )
    answer = client.post("/projects/icalendar/filters/save/", {"name": "  ", "save": "new"})
    assert answer.status_code == 400 and "The filter needs a name" in answer.content.decode()


def test_only_writers_save(client, project, alice):
    client.force_login(alice)
    assert client.get("/projects/icalendar/filters/save/").status_code == 403


def test_no_filters_yet(client, project):
    page = client.get("/projects/icalendar/filters/").content.decode()
    assert "data-no-filters" in page and 'href="/projects/icalendar/pull-requests/"' in page


def test_an_unknown_filter(client, project):
    assert client.get("/projects/icalendar/pull-requests/?saved=99").status_code == 404


def test_the_tabs_have_filters_after_the_pull_requests(client, project, bob):
    client.force_login(bob)
    page = client.get("/projects/icalendar/filters/").content.decode()
    tabs = page.split('<ul class="tabs">')[1].split("</ul>")[0]
    assert tabs.index("Pull requests") < tabs.index("Filters") < tabs.index("Repositories")


def test_a_renamed_label_keeps_the_filters_working(client, project, github):
    """GitHub keeps the id of a renamed label: the site renames it, also in the filters."""
    from pycal_dashboard.models import Label

    saved = PullRequestFilter.objects.create(
        project=project,
        name="Waiting",
        columns=["labels~applies~present~needs review", "status~all~open"],
    )
    label = Label.objects.get(name="needs review")
    for item in github.repositories[REPO]["labels"]:
        if item["name"] == "needs review":
            item["name"] = "review wanted"  # the same id, as GitHub renames
    for issue in github.repositories[REPO]["issues"]:
        for item in issue["labels"]:
            if item["name"] == "needs review":
                item["name"] = "review wanted"
    repository = Repository.objects.get()
    Repository.objects.update(data_version=0)  # read completely again
    repository.refresh_from_db()
    assert RepositoryUpdate(repository).run()
    label.refresh_from_db()
    assert label.name == "review wanted" and Label.objects.filter(name="needs review").count() == 0
    saved.refresh_from_db()
    assert saved.columns == ["labels~applies~present~review wanted", "status~all~open"]
    page = client.get(f"/projects/icalendar/pull-requests/?saved={saved.pk}").content.decode()
    assert "Waiting: 1 pull request" in page  # Ready still has it


def test_the_numbers_of_each_condition_come_when_opened(client, project):
    saved = PullRequestFilter.objects.create(project=project, name="Open", columns=COLUMNS)
    page = client.get("/projects/icalendar/filters/").content.decode()
    assert "data-condition-count" not in page  # not counted with the list
    counts = client.get(f"/projects/icalendar/filters/{saved.pk}/").content.decode()
    rows = counts.split('data-condition-count="')[1:]
    assert [row.split('numeric">')[1].split("<")[0] for row in rows] == ["2", "1", "1"]
    assert "← Back to the filters" in counts  # a page of its own without JavaScript
    assert "font-weight" not in counts


def test_edit_a_filter(client, project, bob):
    saved = PullRequestFilter.objects.create(project=project, name="Open", columns=COLUMNS)
    assert b"data-edit-filter" not in client.get("/projects/icalendar/filters/").content
    client.force_login(bob)
    page = client.get("/projects/icalendar/filters/").content.decode()
    edit = page.split("data-edit-filter")[0].rsplit('href="', 1)[1].split('"')[0]
    assert edit.startswith("/projects/icalendar/filters/save/?col=status~applies~open")
    assert f"saved={saved.pk}" in edit
    assert "Save Open" in client.get(edit.replace("&amp;", "&")).content.decode()
