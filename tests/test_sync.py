"""Reading installations from GitHub: the sync, the page after an installation, the command."""

import pytest
from django.core.management import call_command

from pycal_dashboard.errors import InstallationNotAllowed
from pycal_dashboard.models import Item, Repository
from pycal_dashboard.services.repository_sync import RepositorySync
from tests.conftest import REPOSITORY


def test_sync_reads_and_labels(synced):
    assert Repository.objects.count() == 3
    assert not Item.objects.filter(repository__private=True).exists()
    assert Item.objects.filter(repository__full_name=REPOSITORY).count() == 5
    assert synced.labels_of(REPOSITORY, 3) == ["first contribution", "size: XS"]
    assert synced.labels_of(REPOSITORY, 4) == ["size: L"]
    pull = Item.objects.get(repository__full_name=REPOSITORY, number=4)
    assert pull.is_pull and pull.requested_reviewers == ["bob"]
    assert Item.objects.get(repository__full_name=REPOSITORY, number=5).merged


def test_sync_again_reads_what_changed(synced):
    synced.requests.clear()
    summary = RepositorySync(1).run()
    assert summary["labeled"] == 0
    issue_requests = [r for r in synced.requests if r.url.path.endswith("/issues")]
    assert all("since=" in str(r.url) for r in issue_requests)


def test_removed_repository_is_hidden(synced):
    synced.installation_repositories[1].remove(REPOSITORY)
    RepositorySync(1).run()
    assert Repository.objects.get(full_name=REPOSITORY).installation is None


def test_installation_of_another_account(github, db):
    github.install(2, "Elsewhere", ["Elsewhere/x"])
    with pytest.raises(InstallationNotAllowed):
        RepositorySync(2).run()
    assert RepositorySync.everything() == []


def test_errors_of_a_repository_are_collected(organization, db, monkeypatch):
    organization.repositories[REPOSITORY]["archived"] = False
    original = organization.list_issues

    def failing(request, repo):
        if repo == REPOSITORY:
            return __import__("httpx").Response(500, json={"message": "boom"})
        return original(request, repo)

    monkeypatch.setattr(organization, "list_issues", failing)
    summary = RepositorySync(1).run()
    assert summary["errors"] and "GitHubError" in summary["errors"][0]


def test_installed_page(client, organization):
    response = client.get("/setup/installed/?installation_id=1&setup_action=install")
    assert response.status_code == 200
    assert b"data-summary" in response.content
    again = client.get("/setup/installed/?installation_id=1")
    assert b"data-summary" not in again.content  # only administrators read it again


def test_installed_page_errors(client, organization):
    assert client.get("/setup/installed/?installation_id=x").status_code == 400
    response = client.get("/setup/installed/?installation_id=99")
    assert response.status_code == 404
    assert b"InstallationNotFound" in response.content


def test_command(organization, db, capsys):
    call_command("sync_repositories")
    assert "3 repositories" in capsys.readouterr().out


def test_command_without_app(settings, db, capsys):
    settings.GITHUB_APP_ID = ""
    call_command("sync_repositories")
    assert "No GitHub App" in capsys.readouterr().out
