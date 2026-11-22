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


RESTORE = "/projects/icalendar/settings/restore/"


def plan(client, text: str):
    """Upload a backup: the page of what it changes."""
    return client.post(RESTORE, {"backup": SimpleUploadedFile("backup.yaml", text.encode())})


def restore(client, text: str, confirm=()):
    """Upload a backup and restore it with the ticked changes."""
    page = plan(client, text)
    if page.status_code != 200:
        return page
    return client.post(RESTORE, {"backup_text": text, "confirm": list(confirm), "restore": "yes"})


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


def test_restore_adds_and_asks_before_it_deletes_or_replaces(client, project, step, bob):  # noqa: F811
    """A filter added after the backup stays unless its deletion is ticked."""
    client.force_login(bob)
    data = yaml.safe_load(download(client))
    data["project"]["name"] = "Calendar"
    data["filters"].append({"name": "New", "description": "", "columns": ["status~applies~open"]})
    data["steps"].append({"name": "Open", "filter": "New"})
    PullRequestFilter.objects.create(project=project, name="Gone", columns=[])
    issue = project.repositories.get().issues.first()
    PullRequestPlace.objects.create(project=project, issue=issue, step=step)
    text = yaml.safe_dump(data)
    page = plan(client, text).content.decode()
    adds = page.split("data-restore-adds")[1].split("</ul>")[0]
    assert "Add the filter “New”" in adds and "Add the step “Open”" in adds
    asks = page.split("data-restore-asks")[1].split("</ul>")[0]
    assert 'value="filter-delete:Gone"' in asks and 'value="name"' in asks
    assert "checked" not in asks  # nothing destructive is ticked
    assert project.filters.count() == 3  # the page changes nothing
    answer = client.post(RESTORE, {"backup_text": text, "restore": "yes"})
    assert answer["Location"] == "/projects/icalendar/settings/#backup"
    project.refresh_from_db()
    assert project.name == "iCalendar"  # not ticked
    names = sorted(project.filters.values_list("name", flat=True))
    assert names == ["Conflicts", "Gone", "New", "Review"]  # Gone stays
    steps = list(project.steps.select_related("filter"))
    assert [(s.name, s.filter.name, s.position) for s in steps] == [
        ("Review it", "Review", 0),
        ("Open", "New", 1),
    ]
    assert not PullRequestPlace.objects.exists()  # the next update only records
    client.post(RESTORE, {"backup_text": text, "confirm": ["name", "filter-delete:Gone"]})
    project.refresh_from_db()
    assert project.name == "Calendar" and not project.filters.filter(name="Gone").exists()
    assert "restoring it changes nothing" in plan(client, text).content.decode()


def test_a_changed_step_is_replaced_only_when_ticked(client, project, step, bob):  # noqa: F811
    client.force_login(bob)
    text = download(client)
    step.summary, step.color = "Changed after the backup", "#ffffff"
    step.save()
    later = PullRequestStep.objects.create(
        project=project,
        filter=PullRequestFilter.objects.get(name="Conflicts"),
        name="Added later",
        position=0,
    )
    asks = plan(client, text).content.decode().split("data-restore-asks")[1]
    assert 'value="step-replace:Review it"' in asks
    assert 'value="step-delete:Added later"' in asks
    assert 'value="step-order"' not in asks  # the steps of both are in the same order
    restore(client, text)
    step.refresh_from_db()
    assert step.summary == "Changed after the backup" and later.pk in project.steps.values_list(
        "pk", flat=True
    )
    restore(client, text, ["step-replace:Review it", "step-delete:Added later"])
    step.refresh_from_db()
    assert (step.summary, step.color) == ("Thanks, {author_mention}!", "#bfdbfe")
    assert list(project.steps.values_list("name", "position")) == [("Review it", 0)]


def test_the_order_of_the_steps_changes_only_when_ticked(client, project, step, bob):  # noqa: F811
    client.force_login(bob)
    other = PullRequestStep.objects.create(
        project=project,
        filter=PullRequestFilter.objects.get(name="Conflicts"),
        name="Conflicts",
        position=1,
    )
    text = download(client)
    PullRequestStep.objects.filter(pk=other.pk).update(position=0)  # moved before it
    PullRequestStep.objects.filter(pk=step.pk).update(position=1)
    restore(client, text)
    assert list(project.steps.values_list("name", flat=True)) == ["Conflicts", "Review it"]
    restore(client, text, ["step-order"])
    assert list(project.steps.values_list("name", flat=True)) == ["Review it", "Conflicts"]


def test_the_backup_keeps_the_skips_the_roles_and_the_settings(client, project, step, bob):  # noqa: F811
    from pycal_dashboard.models import Project, ProjectMember, StepSkip
    from pycal_dashboard.services.project_access import ProjectAccess
    from pycal_dashboard.services.project_editor import ProjectEditor
    from tests.conftest import person

    carol = person(44, "carol")
    ProjectEditor(ProjectAccess(project, bob)).share("carol", "write")
    Project.objects.filter(pk=project.pk).update(step_labels=Project.LABELS_SYNC)
    issue = project.repositories.get().issues.get(number=1)
    StepSkip.objects.create(step=step, issue=issue, user=bob, reason="Reviewed in the chat")
    client.force_login(bob)
    data = yaml.safe_load(download(client))
    assert data["project"]["step_labels"] == "sync"
    assert {"handle": "carol", "role": "write"} in data["members"]
    (skip,) = data["steps"][0]["skips"]
    assert (skip["repository"], skip["number"], skip["by"]) == ("collective/icalendar", 1, "bob")
    assert skip["reason"] == "Reviewed in the chat" and skip["created"]
    StepSkip.objects.all().delete()
    ProjectMember.objects.filter(user=carol).delete()
    Project.objects.filter(pk=project.pk).update(step_labels=Project.LABELS_OFF)
    text = yaml.safe_dump(data)
    page = plan(client, text).content.decode()
    assert "Add 1 skip of a step for a pull request" in page
    assert 'value="member:carol:write"' in page and 'value="step_labels"' in page
    restore(client, text)  # the skip is added; the role and the labels wait for a tick
    restored = StepSkip.objects.get()
    assert (restored.user, restored.reason) == (bob, "Reviewed in the chat")
    assert restored.created.isoformat(timespec="seconds") == skip["created"]
    assert not ProjectMember.objects.filter(user=carol).exists()
    restore(client, text, ["member:carol:write", "step_labels"])
    assert ProjectMember.objects.get(user=carol).role == "write"
    project.refresh_from_db()
    assert project.step_labels == Project.LABELS_SYNC


def test_who_never_signed_in_gets_no_role(client, project, step, bob):  # noqa: F811
    client.force_login(bob)
    data = yaml.safe_load(download(client))
    data["members"].append({"handle": "nobody", "role": "owner"})
    page = plan(client, yaml.safe_dump(data)).content.decode()
    assert "@nobody never signed in: no role" in page.split("data-restore-notes")[1]


# every field of what a project keeps: in the backup, or left out with the reason
KEPT = {
    "Project": {"name", "description", "public", "slug", "step_labels", "repositories"},
    "PullRequestFilter": {"name", "description", "columns"},
    "PullRequestStep": {
        "filter",
        "name",
        "summary",
        "conditions",
        "position",  # the order of the list
        "hidden",
        "color",
        "actions",
        "skip_authors",
    },
    "PullRequestMessage": {
        "template",
        "draft",
        "listed",
        "to_listed",
        "to_new",
        "to_open",
        "to_closed",
    },
    "StepSkip": {"step", "issue", "user", "reason", "created"},
    "ProjectMember": {"user", "role"},
}
LEFT_OUT = {
    "id": "the ids of the database of a site",
    "project": "the project that is restored",
    "created": "when it was made on the site",
    "updated": "when it was changed on the site",
    "added": "when the role was given on the site",
    "created_by": "who made it: the site keeps it, restoring is done by one person",
    "updated_by": "who changed it last on the site",
    "new_since": "the new pull requests are those from restoring on",
}


def test_every_field_that_people_decide_is_in_the_backup():
    """A new field goes into the backup, or into LEFT_OUT with the reason."""
    from django.apps import apps

    for name, kept in KEPT.items():
        model = apps.get_model("pycal_dashboard", name)
        fields = {field.name for field in model._meta.get_fields() if field.concrete}
        missing = fields - kept - set(LEFT_OUT)
        assert not missing, (name, missing)
    # and all models of a project that people decide are listed; what GitHub tells is read again
    derived = {"PullRequestPlace", "PullRequestComment", "StepLabel", "UpdateJob", "ProjectSlug"}
    for model in apps.get_app_config("pycal_dashboard").get_models():
        related = {
            field.related_model.__name__
            for field in model._meta.get_fields()
            if field.concrete and field.is_relation and field.related_model
        }
        if related & {"Project", "PullRequestStep"} and model.__name__ not in derived:
            assert model.__name__ in KEPT, model.__name__


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


def test_restore_needs_the_rights(client, project, step, bob, alice):  # noqa: F811
    client.force_login(bob)
    text = download(client)
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
        "draft": None,
        "listed": ["1"],
        "to_listed": True,
        "to_new": False,
        "to_open": True,
        "to_closed": False,
    }
    data["message"].update(template="Changed", to_new=True)
    restore(client, yaml.safe_dump(data))
    assert PullRequestMessage.objects.get().template == "Hi {author_handle}"  # not ticked
    restore(client, yaml.safe_dump(data), ["message"])
    message = PullRequestMessage.objects.get()
    assert message.template == "Changed" and message.new_since is not None
