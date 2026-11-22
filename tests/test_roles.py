"""Who may do what in a project, for every role and every action of a project.

- A visitor, signed in or not, only sees a public project.
- ``read`` changes nothing, but updates the project from GitHub.
- ``write`` sees the collaborators and the settings and changes the project, but invites
  nobody, changes no role, does nothing destructive (delete it, restore a backup) and does not
  change who sees it or its address.
- ``owner`` does everything.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from django.utils import timezone

from pycal_dashboard.models import (
    Issue,
    Project,
    ProjectMember,
    ProjectSnapshot,
    PullRequestFilter,
    PullRequestStep,
    Repository,
    StepSkip,
    UpdateJob,
)
from pycal_dashboard.services.project_access import ProjectAccess
from pycal_dashboard.services.project_backup import ProjectBackup
from pycal_dashboard.services.project_editor import ProjectEditor
from tests.conftest import person

pytestmark = pytest.mark.django_db
ROLES = ("anonymous", "visitor", "read", "write", "owner")
RANK = {role: rank for rank, role in enumerate(ROLES)}


@dataclass
class World:
    """A public project of Bob with Carol as a reader, a repository, a filter and a step."""

    project: Project
    repository: Repository
    saved: PullRequestFilter
    step: PullRequestStep
    carol: object
    pull: Issue
    backup: str = ""
    snapshot: object = None
    path: str = field(init=False)

    def __post_init__(self):
        self.path = self.project.path()


@pytest.fixture
def world(bob):
    project = ProjectEditor.create(bob, "iCalendar", slug="icalendar")
    now = timezone.now()  # up to date: the overview starts no update of its own
    repository = Repository.objects.create(full_name="collective/icalendar", updated=now)
    project.repositories.add(repository)
    Project.objects.filter(pk=project.pk).update(updated=now)
    saved = PullRequestFilter.objects.create(
        project=project, name="Open", columns=["status~applies~open"]
    )
    step = PullRequestStep.objects.create(project=project, filter=saved, name="Open")
    carol = person(3, "carol")
    ProjectEditor(ProjectAccess(project, bob)).share("carol", "read")
    pull = Issue.objects.create(
        repository=repository,
        github_id=1,
        number=7,
        title="A pull request",
        pull_request=True,
        created=now,
    )
    StepSkip.objects.create(step=step, issue=pull, user=bob, reason="Before")  # to remove
    found = World(project, repository, saved, step, carol, pull)
    found.backup = ProjectBackup(project).export()
    found.snapshot = ProjectSnapshot.objects.create(
        project=project, text=found.backup, created_by=bob
    )
    return found


@pytest.fixture
def signed_in(client, bob, alice, world, request):
    """The client as the role of the test; Alice is the visitor or the collaborator."""
    role = request.param
    if role in ("read", "write"):
        ProjectEditor(ProjectAccess(world.project, bob)).share("alice", role)
    if role == "owner":
        client.force_login(bob)
    elif role != "anonymous":
        client.force_login(alice)
    return role


def allowed(answer) -> bool:
    """Whether the site did what was asked, and did not refuse or ask to sign in."""
    if answer.status_code in (403, 404):
        return False
    return not (answer.status_code == 302 and "/accounts/" in answer["Location"])


def project_exists() -> bool:
    return Project.objects.filter(slug="icalendar").exists()


# each action: the least role that may do it, what it asks for, and whether it happened
ACTIONS = {
    "see the project": (
        "anonymous",
        lambda c, w: c.get(w.path),
        lambda w: True,
    ),
    "update it from GitHub": (
        "read",
        lambda c, w: c.post(w.path + "update/"),
        lambda w: UpdateJob.objects.filter(project=w.project).exists(),
    ),
    "take a snapshot": (
        "write",
        lambda c, w: c.post(w.path + "settings/snapshots/", {"take": "yes"}),
        lambda w: ProjectSnapshot.objects.filter(project=w.project).count() == 2,
    ),
    "download a snapshot": (
        "write",
        lambda c, w: c.get(w.path + f"settings/snapshots/{w.snapshot.pk}/download/"),
        lambda w: True,
    ),
    "delete a snapshot": (
        "owner",
        lambda c, w: c.post(w.path + "settings/snapshots/", {"delete": w.snapshot.pk}),
        lambda w: not ProjectSnapshot.objects.filter(pk=w.snapshot.pk).exists(),
    ),
    "restore a snapshot": (
        "owner",
        lambda c, w: c.post(w.path + "settings/restore/", {"snapshot": w.snapshot.pk}),
        lambda w: True,  # the page of what it changes
    ),
    "see the settings": (
        "write",
        lambda c, w: c.get(w.path + "settings/"),
        lambda w: True,
    ),
    "change the name and description": (
        "write",
        lambda c, w: c.post(
            w.path + "settings/", {"name": "Changed", "description": "", "visibility": "public"}
        ),
        lambda w: Project.objects.get(pk=w.project.pk).name == "Changed",
    ),
    "make it private": (
        "owner",
        lambda c, w: c.post(
            w.path + "settings/", {"name": "iCalendar", "description": "", "visibility": "private"}
        ),
        lambda w: not Project.objects.get(pk=w.project.pk).public,
    ),
    "change the address": (
        "owner",
        lambda c, w: c.post(w.path + "address/", {"slug": "calendars"}),
        lambda w: Project.objects.get(pk=w.project.pk).slug == "calendars",
    ),
    "delete it": (
        "owner",
        lambda c, w: c.post(w.path + "settings/", {"delete": "yes", "confirm": "yes"}),
        lambda w: not Project.objects.filter(pk=w.project.pk).exists(),
    ),
    "see the collaborators": (
        "write",
        lambda c, w: c.get(w.path + "collaborators/"),
        lambda w: True,
    ),
    "invite a collaborator": (
        "owner",
        lambda c, w: c.post(w.path + "collaborators/", {"github_name": "dave", "role": "read"}),
        lambda w: ProjectMember.objects.filter(user__username="dave").exists(),
    ),
    "change a role": (
        "owner",
        lambda c, w: c.post(w.path + "collaborators/", {"github_name": "carol", "role": "write"}),
        lambda w: ProjectMember.objects.get(user=w.carol).role == "write",
    ),
    "remove a collaborator": (
        "owner",
        lambda c, w: c.post(
            w.path + "collaborators/",
            {"remove": ProjectMember.objects.get(user=w.carol).pk},
        ),
        lambda w: not ProjectMember.objects.filter(user=w.carol).exists(),
    ),
    "see the repositories": (
        "write",
        lambda c, w: c.get(w.path + "repositories/"),
        lambda w: True,
    ),
    "remove a repository": (
        "write",
        lambda c, w: c.post(w.path + "repositories/", {"remove": w.repository.pk}),
        lambda w: not w.project.repositories.exists(),
    ),
    "download a backup": (
        "write",
        lambda c, w: c.get(w.path + "settings/backup/"),
        lambda w: True,
    ),
    "restore a backup": (
        "owner",
        lambda c, w: c.post(
            w.path + "settings/restore/",
            {"backup_text": backup_file(w).read().decode(), "confirm": "name"},
        ),
        lambda w: Project.objects.get(pk=w.project.pk).name == "Restored",
    ),
    "save a filter": (
        "write",
        lambda c, w: c.post(
            w.path + "filters/save/",
            {"col": ["status~applies~merged"], "on": "0", "name": "Merged", "save": "new"},
        ),
        lambda w: w.project.filters.filter(name="Merged").exists(),
    ),
    "edit a step": (
        "write",
        lambda c, w: c.post(w.path + f"steps/{w.step.pk}/edit/", {"name": "Renamed"}),
        lambda w: PullRequestStep.objects.get(pk=w.step.pk).name == "Renamed",
    ),
    "remove a step": (
        "write",
        lambda c, w: c.post(w.path + f"steps/{w.step.pk}/remove/"),
        lambda w: not PullRequestStep.objects.filter(pk=w.step.pk).exists(),
    ),
    "skip a step of a pull request": (
        "write",
        lambda c, w: c.post(
            w.path + f"pull/{w.pull.number}/skip/", {"step": w.step.pk, "reason": "Met"}
        ),
        lambda w: StepSkip.objects.filter(step=w.step, issue=w.pull).exists(),
    ),
    "remove the skip of a step": (
        "write",
        lambda c, w: c.post(
            w.path + f"pull/{w.pull.number}/skip/", {"step": w.step.pk, "remove": "1"}
        ),
        lambda w: not StepSkip.objects.filter(step=w.step, issue=w.pull).exists(),
    ),
    "switch the step labels on": (
        "write",
        lambda c, w: c.post(w.path + "sync/labels/", {"step_labels": "sync"}),
        lambda w: Project.objects.get(pk=w.project.pk).step_labels == "sync",
    ),
    "switch the step labels off, which deletes them": (
        "owner",
        lambda c, w: (
            Project.objects.filter(pk=w.project.pk).update(step_labels="sync"),
            c.post(w.path + "sync/labels/", {"step_labels": "off"}),
        )[1],
        lambda w: Project.objects.get(pk=w.project.pk).step_labels == "off",
    ),
    "edit the message": (
        "write",
        lambda c, w: c.get(w.path + "message/edit/"),
        lambda w: True,
    ),
}


def backup_file(world: World):
    from django.core.files.uploadedfile import SimpleUploadedFile

    text = world.backup.replace("name: iCalendar", "name: Restored", 1)
    return SimpleUploadedFile("backup.yaml", text.encode(), content_type="application/yaml")


@pytest.mark.parametrize("signed_in", ROLES, indirect=True)
@pytest.mark.parametrize("action", list(ACTIONS))
def test_who_may_do_what(client, world, signed_in, action):
    least, act, happened = ACTIONS[action]
    if action == "invite a collaborator":
        person(4, "dave")
    answer = act(client, world)
    may = RANK[signed_in] >= RANK[least]
    assert allowed(answer) is may, (signed_in, action, answer.status_code)
    if may:
        assert happened(world), (signed_in, action)
    else:  # refused: nothing changed
        assert project_exists()
        project = Project.objects.get(pk=world.project.pk)
        assert (project.name, project.slug, project.public) == ("iCalendar", "icalendar", True)
        assert ProjectMember.objects.get(user=world.carol).role == "read"
        assert world.project.repositories.exists()
        assert PullRequestStep.objects.filter(pk=world.step.pk, name="Open").exists()
        assert not world.project.filters.filter(name="Merged").exists()
        assert StepSkip.objects.get(step=world.step, issue=world.pull).reason == "Before"


@pytest.mark.parametrize("signed_in", ROLES, indirect=True)
def test_the_tabs_and_buttons_of_each_role(client, world, signed_in):
    """Each role sees the tabs and buttons of what it may do, and no others."""
    rank = RANK[signed_in]
    overview = client.get(world.path).content.decode()
    settings = client.get(world.path + "settings/").content.decode()
    assert ("data-update" in overview) is (rank >= RANK["read"])
    assert (f"{world.path}settings/" in overview) is (rank >= RANK["write"])
    assert (f"{world.path}repositories/" in overview) is (rank >= RANK["write"])
    if rank >= RANK["write"]:
        assert f"{world.path}collaborators/" in settings  # a tab of the settings
        backup = client.get(world.path + "settings/backup/").content.decode()
        assert "data-download-backup" in backup
        assert ("data-restore>" in backup) is (rank >= RANK["owner"])
        assert ("data-restore-owners" in backup) is (rank < RANK["owner"])
        danger = client.get(world.path + "settings/danger/").content.decode()
        assert ("data-delete-project" in danger) is (rank >= RANK["owner"])
        assert ("data-delete-owners" in danger) is (rank < RANK["owner"])
        client.post(world.path + "settings/snapshots/", {"take": "yes"})
        snapshots = client.get(world.path + "settings/snapshots/").content.decode()
        assert "data-take-snapshot" in snapshots and "/download/" in snapshots
        assert ('name="delete"' in snapshots) is (rank >= RANK["owner"])
        assert ('name="snapshot"' in snapshots) is (rank >= RANK["owner"])
        assert ('class="visibility" disabled' in settings) is (rank < RANK["owner"])
        assert ("data-address" in settings) is (rank >= RANK["owner"])
        collaborators = client.get(world.path + "collaborators/").content.decode()
        assert ("data-share" in collaborators) is (rank >= RANK["owner"])
        assert ('name="remove"' in collaborators) is (rank >= RANK["owner"])
