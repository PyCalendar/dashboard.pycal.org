"""The backup of a project as YAML: download it, restore it, and refuse wrong files."""

import pytest
import yaml
from django.core.files.uploadedfile import SimpleUploadedFile

from pycal_dashboard.models import PullRequestFilter, PullRequestPlace, PullRequestStep

from .test_steps import filters, project  # noqa: F401 (fixtures)

pytestmark = pytest.mark.django_db


@pytest.fixture
def step(project, filters):  # noqa: F811
    _conflict, review = filters
    return PullRequestStep.objects.create(
        project=project,
        filter=review,
        name="Review it",
        summary="Thanks, {author_mention}!",
        color="#bfdbfe",
        conditions={"labels~applies~present~needs review": {"summary": "Review"}},
        actions={"enter": {"add": ["needs review"], "remove": []}},
    )


def download(client) -> str:
    answer = client.get("/projects/icalendar/settings/backup/")
    assert answer.status_code == 200, answer.status_code
    assert answer["Content-Type"] == "application/yaml; charset=utf-8"
    assert 'filename="icalendar-backup-' in answer["Content-Disposition"]
    return answer.content.decode()


def restore(client, text: str, confirm: bool = True):
    data = {"backup": SimpleUploadedFile("backup.yaml", text.encode())}
    if confirm:
        data["confirm"] = "yes"
    return client.post("/projects/icalendar/settings/restore/", data)


def test_the_backup_has_the_project(client, project, step, bob, settings):  # noqa: F811
    settings.DOCS_URL = "https://docs.example.org/"
    client.force_login(bob)
    text = download(client)
    assert text.startswith("# A backup of the project iCalendar of ")
    assert "https://docs.example.org/reference/backup.html" in text.split("\n")[1]
    data = yaml.safe_load(text)
    assert data["dashboard_backup"] == 1
    assert data["documentation"] == "https://docs.example.org/reference/backup.html"
    assert data["project"]["name"] == "iCalendar" and data["repositories"] == [
        "collective/icalendar"
    ]
    assert [f["name"] for f in data["filters"]] == ["Conflicts", "Review"]
    (saved,) = data["steps"]
    assert saved["filter"] == "Review" and saved["color"] == "#bfdbfe"
    assert saved["actions"]["enter"]["add"] == ["needs review"]
    page = client.get("/projects/icalendar/settings/").content.decode()
    assert "data-backup" in page and "reference/backup.html" in page


def test_restore_replaces_filters_and_steps(client, project, step, bob):  # noqa: F811
    client.force_login(bob)
    data = yaml.safe_load(download(client))
    data["project"]["name"] = "Calendar"
    data["filters"].append({"name": "New", "description": "", "columns": ["status~applies~open"]})
    data["steps"].append({"name": "Open", "filter": "New"})
    PullRequestFilter.objects.create(project=project, name="Gone", columns=[])
    issue = project.repositories.get().issues.first()
    PullRequestPlace.objects.create(project=project, issue=issue, step=step)
    answer = restore(client, yaml.safe_dump(data))
    assert answer["Location"] == "/projects/icalendar/settings/#backup"
    project.refresh_from_db()
    assert project.name == "Calendar"
    assert sorted(project.filters.values_list("name", flat=True)) == ["Conflicts", "New", "Review"]
    steps = list(project.steps.select_related("filter"))
    assert [(s.name, s.filter.name, s.position) for s in steps] == [
        ("Review it", "Review", 0),
        ("Open", "New", 1),
    ]
    assert steps[0].actions["enter"]["add"] == ["needs review"]
    assert not PullRequestPlace.objects.exists()  # the next update only records


@pytest.mark.parametrize(
    ("text", "title"),
    [
        ("not: [yaml", "The backup cannot be restored"),
        ("just: a mapping", "The backup cannot be restored"),
        ("dashboard_backup: 99\nproject: {name: X}", "The backup has an unknown version"),
        (
            "dashboard_backup: 1\nproject: {name: X}\nfilters: [{name: F, columns: [nothing~x]}]",
            "The backup cannot be restored",
        ),
        (
            "dashboard_backup: 1\nproject: {name: X}\nsteps: [{name: S, filter: Missing}]",
            "The backup cannot be restored",
        ),
    ],
)
def test_a_wrong_file_changes_nothing(client, project, step, bob, text, title):  # noqa: F811
    client.force_login(bob)
    answer = restore(client, text)
    assert answer.status_code == 400 and title in answer.content.decode()
    assert project.steps.count() == 1 and project.filters.count() == 2


def test_restore_needs_the_box_and_the_rights(client, project, step, bob, alice):  # noqa: F811
    client.force_login(bob)
    text = download(client)
    answer = restore(client, text, confirm=False)
    assert answer["Location"].endswith("#backup") and project.steps.count() == 1
    client.force_login(alice)  # no collaborator
    assert client.get("/projects/icalendar/settings/backup/").status_code in (403, 404)
    assert restore(client, text).status_code in (403, 404)


def test_restore_adds_the_repositories_the_project_lacks(
    client,
    project,  # noqa: F811
    step,
    bob,
    monkeypatch,
):
    added = []
    monkeypatch.setattr(
        "pycal_dashboard.views.projects.add_repositories",
        lambda request, editor, names: added.extend(names),
    )
    client.force_login(bob)
    data = yaml.safe_load(download(client))
    data["repositories"].append("collective/other")
    restore(client, yaml.safe_dump(data))
    assert added == ["collective/other"]


def test_the_backup_has_the_message(client, project, step, bob):  # noqa: F811
    from pycal_dashboard.models import PullRequestMessage

    PullRequestMessage.objects.create(
        project=project, template="Hi {author_handle}", listed=["1"], to_open=True
    )
    client.force_login(bob)
    data = yaml.safe_load(download(client))
    assert data["message"] == {
        "template": "Hi {author_handle}",
        "listed": ["1"],
        "to_listed": True,
        "to_new": False,
        "to_open": True,
        "to_closed": False,
    }
    data["message"].update(template="Changed", to_new=True)
    restore(client, yaml.safe_dump(data))
    message = PullRequestMessage.objects.get()
    assert message.template == "Changed" and message.new_since is not None
