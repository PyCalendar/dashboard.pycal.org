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


def test_the_save_page_sums_up_the_columns(client, project, bob):
    client.force_login(bob)
    page = save_page(client, *COLUMNS)
    assert "← Back to the pull requests" in page
    assert 'href="/projects/icalendar/pull-requests/?col=status~applies~open' in page
    assert "The filter shows 3 pull requests now:" in page  # open, or without the label
    applies = page.split('data-summary="applies"')[1].split("</div>")[0]
    not_ = page.split('data-summary="not"')[1].split("</div>")[0]
    both = page.split('data-summary="both"')[1].split("</div>")[0]
    assert "state-open" in applies and "needs review" in not_ and "state-conflict" in both
    assert "data-opposite" in not_ and "label-absent" in not_  # the same as label absent
    assert "&amp;swap=1" in not_
    assert page.count('<input type="hidden" name="col"') == 3


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
        "save": "new",
    }
    answer = client.post("/projects/icalendar/filters/save/", data)
    assert answer.status_code == 302 and answer["Location"] == "/projects/icalendar/filters/"
    saved = PullRequestFilter.objects.get()
    assert (saved.name, saved.columns, saved.created_by) == ("Ready to merge", COLUMNS, bob)
    client.logout()
    page = client.get("/projects/icalendar/filters/").content.decode()  # public
    item = page.split('data-filter="Ready to merge"')[1].split("</li>\n</ul>")[0]
    assert "<strong>Open</strong> ones" in item and "3 pull requests" in item
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
        {"col": ["status~applies~merged"], "saved": saved.pk, "name": "Merged", "save": "this"},
    )
    saved.refresh_from_db()
    assert (saved.name, saved.columns) == ("Merged", ["status~applies~merged"])
    client.post(
        "/projects/icalendar/filters/save/",
        {"col": ["status~applies~open"], "saved": saved.pk, "name": "Open", "save": "new"},
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
