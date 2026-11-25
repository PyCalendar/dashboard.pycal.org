"""People delete their account in the red area of the page Account."""

import pytest
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount, SocialToken
from django.contrib.auth import get_user_model

from pycal_dashboard.models import (
    GitHubUser,
    LogTrigger,
    Preferences,
    Profile,
    Project,
    ProjectMember,
)
from pycal_dashboard.services.project_access import ProjectAccess
from pycal_dashboard.services.project_editor import ProjectEditor

pytestmark = pytest.mark.django_db


def test_the_page_account_has_the_red_area(client, bob):
    client.force_login(bob)
    page = client.get("/account/?tab=delete").content.decode()
    area = page.split("data-delete-account")[1]
    assert 'class="card danger-zone"' in page and 'action="/account/delete/"' in area
    assert "Type your GitHub handle, bob, to confirm" in area
    assert 'class="button button-danger"' in area
    assert "tutorial/account.html#delete-account" in area


def test_delete_the_account(client, bob):
    EmailAddress.objects.create(user=bob, email="bob@example.org", verified=True, primary=True)
    Preferences.objects.create(user=bob, theme="dark")
    alone = ProjectEditor.create(bob, "Alone")
    client.force_login(bob)
    page = client.get("/account/?tab=delete").content.decode()
    assert "data-own-projects" in page and "Alone" in page.split("data-own-projects")[1]
    answer = client.post("/account/delete/", {"confirm": "@Bob"}, follow=True)
    assert answer.redirect_chain[-1][0] == "/"
    assert "Your account is deleted, with the projects Alone." in answer.content.decode()
    assert not get_user_model().objects.filter(username="bob").exists()
    for model in (SocialAccount, SocialToken, EmailAddress, Profile, Preferences, ProjectMember):
        assert not model.objects.exists(), model
    assert not Project.objects.filter(pk=alone.pk).exists()
    assert GitHubUser.objects.get(login="bob").user is None  # GitHub data stays
    assert LogTrigger.objects.filter(kind="account", actor_login="bob").exists()
    assert client.get("/account/").status_code == 302  # signed out


def test_the_name_must_be_typed(client, bob):
    client.force_login(bob)
    answer = client.post("/account/delete/", {"confirm": "alice"})
    assert answer.status_code == 400
    assert "Type your GitHub handle to delete the account" in answer.content.decode()
    assert get_user_model().objects.filter(username="bob").exists()


def test_projects_of_others_stay(client, bob, alice):
    project = ProjectEditor.create(alice, "Shared")
    ProjectEditor(ProjectAccess(project, alice)).share("bob", "write")
    client.force_login(bob)
    client.post("/account/delete/", {"confirm": "bob"})
    assert Project.objects.filter(pk=project.pk).exists()
    assert list(project.members.values_list("user__username", flat=True)) == ["alice"]


def test_the_only_owner_of_a_shared_project_hands_it_over_first(client, bob, alice):
    project = ProjectEditor.create(bob, "Shared")
    ProjectEditor(ProjectAccess(project, bob)).share("alice", "read")
    client.force_login(bob)
    page = client.get("/account/?tab=delete").content.decode()
    assert "data-shared-projects" in page and 'action="/account/delete/"' not in page
    assert f"/projects/{project.slug}/settings/collaborators/" in page
    answer = client.post("/account/delete/", {"confirm": "bob"})
    assert answer.status_code == 409 and "You are the only owner of shared projects" in (
        answer.content.decode()
    )
    ProjectEditor(ProjectAccess(project, bob)).share("alice", "owner")
    client.post("/account/delete/", {"confirm": "bob"})
    assert not get_user_model().objects.filter(username="bob").exists()
    assert Project.objects.filter(pk=project.pk).exists()


def test_only_a_post_deletes(client, bob):
    client.force_login(bob)
    assert client.get("/account/delete/").status_code == 405
