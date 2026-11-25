"""The snapshots of a project: backups kept on the site, taken, listed, restored and deleted."""

import pytest
import yaml

from pycal_dashboard.models import ProjectSnapshot, PullRequestFilter
from pycal_dashboard.services import snapshot_editor

from .test_steps import filters, project  # noqa: F401 (fixtures)

pytestmark = pytest.mark.django_db
SNAPSHOTS = "/projects/icalendar/settings/snapshots/"


def test_take_list_download_and_delete_a_snapshot(client, project, bob):  # noqa: F811
    client.force_login(bob)
    assert "data-no-snapshots" in client.get(SNAPSHOTS).content.decode()
    answer = client.post(SNAPSHOTS, {"take": "yes"})
    assert answer["Location"] == SNAPSHOTS
    snapshot = ProjectSnapshot.objects.get()
    assert snapshot.created_by == bob
    assert yaml.safe_load(snapshot.text)["project"]["name"] == "iCalendar"
    page = client.get(SNAPSHOTS).content.decode()
    row = page.split(f'data-snapshot="{snapshot.pk}"')[1].split("</tr>")[0]
    assert "bob" in row and "<time" in row  # who and when
    download = client.get(f"{SNAPSHOTS}{snapshot.pk}/download/")
    assert download.content.decode() == snapshot.text  # the file of a backup
    assert 'filename="icalendar-snapshot-' in download["Content-Disposition"]
    client.post(SNAPSHOTS, {"delete": snapshot.pk})
    assert not ProjectSnapshot.objects.exists()
    assert client.get(f"{SNAPSHOTS}{snapshot.pk}/download/").status_code == 404


def test_a_snapshot_restores_as_a_backup(client, project, filters, bob):  # noqa: F811
    client.force_login(bob)
    client.post(SNAPSHOTS, {"take": "yes"})
    snapshot = ProjectSnapshot.objects.get()
    PullRequestFilter.objects.filter(name="Review").delete()
    PullRequestFilter.objects.create(project=project, name="Later", columns=[])
    page = client.post("/projects/icalendar/settings/restore/", {"snapshot": snapshot.pk})
    text = page.content.decode()
    assert "Add the filter “Review”" in text and 'value="filter-delete:Later"' in text
    client.post(
        "/projects/icalendar/settings/restore/",
        {"backup_text": snapshot.text, "restore": "yes"},
    )
    assert sorted(project.filters.values_list("name", flat=True)) == [
        "Conflicts",
        "Later",
        "Review",
    ]
    from django.core.files.uploadedfile import SimpleUploadedFile

    download = client.get(f"{SNAPSHOTS}{snapshot.pk}/download/").content
    upload = SimpleUploadedFile("snapshot.yaml", download)
    answer = client.post("/projects/icalendar/settings/restore/", {"backup": upload})
    assert answer.status_code == 200 and "data-restore-plan" in answer.content.decode()


def test_a_project_keeps_the_newest_snapshots(client, project, bob, monkeypatch):  # noqa: F811
    monkeypatch.setattr(snapshot_editor, "MAX_SNAPSHOTS", 2)
    client.force_login(bob)
    for _number in range(3):
        client.post(SNAPSHOTS, {"take": "yes"})
    assert ProjectSnapshot.objects.count() == 2


def test_the_settings_have_their_tabs(client, project, bob):  # noqa: F811
    client.force_login(bob)
    for page, current in (
        ("settings/", "Display"),
        ("settings/repositories/", "Repositories"),
        ("settings/collaborators/", "Collaborators"),
        ("settings/snapshots/", "Snapshots"),
        ("settings/backup/", "Backup"),
        ("settings/danger/", "Danger zone"),
    ):
        html = client.get(f"/projects/icalendar/{page}").content.decode()
        tabs = html.split("data-settings-tabs")[1].split("</ul>")[0]
        assert f'aria-current="page">{current}<' in tabs or (
            f'aria-current="page" data-danger-tab>{current}<' in tabs
        ), page
