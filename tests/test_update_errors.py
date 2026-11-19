"""Updates that fail: GitHub busy or slow, missing permissions, and the notice of the overview."""

import pytest

from pycal_dashboard import errors
from pycal_dashboard.github.client import GitHubClient
from pycal_dashboard.models import Installation, PullRequestState, Repository
from pycal_dashboard.services.project_editor import ProjectEditor
from pycal_dashboard.services.repository_update import RepositoryUpdate

pytestmark = pytest.mark.django_db
REPO = "collective/icalendar"


def test_a_busy_github_is_asked_again(github):
    github.fail_with = 502
    github.fail_html = "<html><head><title>502 Bad Gateway</title></head><body>nginx</body></html>"
    with pytest.raises(errors.GitHubUnavailable) as raised:
        GitHubClient().request("GET", "/repos/o/r")
    assert len(github.requests) == 3  # the request and two more
    assert str(raised.value) == (
        "GET /repos/o/r: 502 502 Bad Gateway (GitHub request C0DE:1234:5678)"
    )


def test_an_answer_of_html_is_shown_as_text():
    import httpx

    page = httpx.Response(500, text="<html><body><h1>Oops</h1>\n<p>broken</p></body></html>")
    assert GitHubClient.message(page) == "Oops broken"


def test_github_recovers_while_asked_again(github, monkeypatch):
    answers = iter([502, 200])
    original = github.handle

    def flaky(request):
        status = next(answers, 200)
        if status != 200:
            import httpx

            return httpx.Response(status, text="busy")
        return original(request)

    monkeypatch.setattr(github, "handle", flaky)
    github.add_repository("o/r")
    assert GitHubClient().request("GET", "/repos/o/r").json()["full_name"] == "o/r"


def test_a_slow_page_of_graphql_is_asked_again_smaller(github):
    """GitHub gives up on pages of many pull requests: the same page, half as large."""
    github.graphql_max_first = 10
    github.add_repository(REPO, installation=11, pulls=12)
    repository = Repository.objects.create(full_name=REPO)
    assert RepositoryUpdate(repository).run()
    firsts = [q["variables"]["first"] for q in github.graphql_queries]
    assert firsts == [20, 10, 10]  # refused, then two pages of ten
    assert PullRequestState.objects.count() == 12


def test_github_that_gives_up_on_every_page_is_an_error(github):
    github.graphql_max_first = 2
    github.add_repository(REPO, installation=11, pulls=3)
    repository = Repository.objects.create(full_name=REPO)
    assert not RepositoryUpdate(repository).run()
    repository.refresh_from_db()
    assert repository.error_code == "GitHubUnavailable" and repository.error_at is not None
    assert "502 Bad Gateway" in repository.error_detail


def test_only_the_fields_the_installation_accepted_are_asked(github):
    """An installation that has not accepted checks and statuses yet: no checks are asked."""
    github.add_repository(REPO, installation=11, pulls=1)
    github.installations[0]["permissions"] = {
        "metadata": "read",
        "issues": "read",
        "pull_requests": "write",
        "contents": "read",
    }
    repository = Repository.objects.create(full_name=REPO)
    assert RepositoryUpdate(repository).run()
    (query,) = github.graphql_queries
    assert "mergeStateStatus" in query["query"] and "statusCheckRollup" not in query["query"]
    assert PullRequestState.objects.get().checks == ""
    assert Installation.objects.get().permissions["contents"] == "read"


@pytest.fixture
def failed(github, bob):
    github.add_repository(REPO, installation=11)
    repository = Repository.objects.create(full_name=REPO)
    project = ProjectEditor.create(bob, "iCalendar")
    project.repositories.add(repository)
    github.fail_with = 502
    github.fail_html = "<html><head><title>502 Bad Gateway</title></head></html>"
    RepositoryUpdate(repository).run()
    github.fail_with = None
    return project


def test_the_overview_shows_the_failures_at_the_top(client, failed):
    page = client.get(failed.path()).content.decode()
    notice = page.split("data-update-errors")[1].split("</section>")[0]
    assert page.index("data-update-errors") < page.index("data-totals")  # at the top
    assert "1 repository could not be updated" in notice
    assert "GitHub did not answer in time" in notice
    assert "reference/errors.html#pycal_dashboard.errors.github.GitHubUnavailable" in notice
    assert 'data-dismiss aria-label="Hide this notice"' in notice and "hidden" in notice
    assert f'data-dismissable="update-errors:{failed.slug}:' in page
    details = notice.split("<textarea")[1].split("</textarea>")[0]
    for line in (
        f"Project: {failed.slug}",
        f"Repository: {REPO}",
        "Error: GitHubUnavailable (GitHub did not answer in time)",
        ": 502 502 Bad Gateway (GitHub request C0DE:1234:5678)",
        "Failed at: 20",
        "Last updated: never",
        "Documentation: https://docs.example.org/reference/errors.html#",
    ):
        assert line in details, line
    assert "token" not in details.lower().replace("no tokens", "")
    assert "dismiss.js" in page


def test_a_private_repository_is_not_shown_to_visitors(client, failed, bob):
    Repository.objects.update(private=True)
    assert "data-update-errors" not in client.get(failed.path()).content.decode()
    client.force_login(bob)
    page = client.get(failed.path()).content.decode()
    assert f"Repository: {REPO} (private)" in page


def test_no_notice_without_failures(client, github, bob):
    project = ProjectEditor.create(bob, "Fine")
    assert "data-update-errors" not in client.get(project.path()).content.decode()
