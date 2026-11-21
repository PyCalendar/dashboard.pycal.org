"""The evidence of conditions: the least that shows why a condition holds for a pull request."""

import pytest

from pycal_dashboard.conditions.condition.reviews import Reviews
from pycal_dashboard.conditions.evidence import Evidence
from pycal_dashboard.conditions.group.column import Column
from pycal_dashboard.models import Issue, PullRequestFilter, PullRequestStep, Repository
from pycal_dashboard.services.project_editor import ProjectEditor
from pycal_dashboard.services.repository_update import RepositoryUpdate

pytestmark = pytest.mark.django_db
REPO = "collective/icalendar"
URL = f"https://github.com/{REPO}/pull"
ANNA = {"id": 101, "login": "anna", "avatar_url": "https://avatars.example/a", "type": "User"}
BEN = {"id": 102, "login": "ben", "avatar_url": "https://avatars.example/b", "type": "User"}


@pytest.fixture
def project(github, bob):
    github.add_repository(REPO, installation=11)
    github.add_label(REPO, "needs review", "", "fbca04")
    github.add_issue(REPO, "Reviewed", pull_request=True, user=ANNA)  # 1
    github.add_issue(REPO, "Conflict", pull_request=True, mergeable_state="dirty")  # 2
    github.add_issue(REPO, "Merged", pull_request=True, state="closed", merged=True)  # 3
    github.add_issue(REPO, "Closed", pull_request=True, state="closed")  # 4
    github.add_issue(REPO, "An issue", user=BEN)  # 5
    for state in ("APPROVED", "CHANGES_REQUESTED", "COMMENTED", "APPROVED"):
        github.add_review(REPO, 1, BEN, state)
    github.set_checks(REPO, 1, "FAILURE")
    repository = Repository.objects.create(full_name=REPO)
    project = ProjectEditor.create(bob, "iCalendar", slug="icalendar")
    project.repositories.add(repository)
    assert RepositoryUpdate(repository).run()
    return project


def evidence(value: str, number: int, project=None) -> list[tuple[str, str]]:
    issue = Issue.objects.get(number=number)
    return [(str(e.text), e.url) for e in Column.decode(value).evidence(issue, None, project)]


def test_the_data_specs_give_the_links(project):
    assert evidence("status~applies~open", 1) == [("The pull request on GitHub", f"{URL}/1")]
    assert evidence("labels~applies~present~needs review", 1) == [
        ("Its labels on GitHub", f"{URL}/1")
    ]
    merge_box = ("Where it is merged, on GitHub", f"{URL}/2#issue-comment-box")
    assert evidence("branch~applies~conflict", 2) == [merge_box]
    assert evidence("branch~applies~outdated~up_to_date", 2) == [merge_box]  # each link once
    assert evidence("status~applies~auto_merge", 2) == [merge_box]
    assert evidence("ci~applies~failing", 1) == [("Its checks on GitHub", f"{URL}/1/checks")]
    assert evidence("ci~applies~passing", 1) == [("Its checks on GitHub", f"{URL}/1/checks")]


def test_switches_show_those_that_hold(project):
    """Of open or merged, the one that holds; when none holds, all of them."""
    assert evidence("status~applies~open~auto_merge", 1) == [
        ("The pull request on GitHub", f"{URL}/1")
    ]
    assert evidence("ci~applies~unknown~failing", 1) == [
        ("Its checks on GitHub", f"{URL}/1/checks")
    ]


def test_ci_unknown_says_why(project):
    assert evidence("ci~applies~unknown", 3) == [
        ("Merged: the checks are read for open pull requests only", f"{URL}/3")
    ]
    assert evidence("ci~applies~unknown", 4) == [
        ("Closed: the checks are read for open pull requests only", f"{URL}/4")
    ]


@pytest.mark.parametrize(
    ("value", "shown"),
    [
        (
            "reviews~applies~at_least~4~approved~changes_requested~dismissed",
            3,
        ),  # 3 of 4 there: all of them
        ("reviews~applies~at_least~2~approved~changes_requested~dismissed", 2),  # 2 decide it
        (
            "reviews~applies~at_most~2~approved~changes_requested~dismissed",
            3,
        ),  # more than 2: 3 show it
        ("reviews~applies~at_most~5~approved~changes_requested~dismissed", 3),  # all
        ("reviews~applies~above~1~approved~changes_requested~dismissed", 2),
        ("reviews~applies~below~2~approved~changes_requested~dismissed", 2),
        ("reviews~applies~exactly~3~approved~changes_requested~dismissed", 3),
        ("reviews~applies~exactly~1~approved~changes_requested~dismissed", 2),
    ],
)
def test_reviews_show_as_many_as_decide(project, value, shown):
    found = evidence(value, 1)
    assert len(found) == shown
    assert found[0] == ("Review by ben: approved", f"{URL}/1#pullrequestreview-50001")
    assert found[1] == ("Review by ben: changes requested", f"{URL}/1#pullrequestreview-50002")
    assert all("50003" not in url for _text, url in found)  # comments are not chosen


def test_all_kinds_of_reviews_count_by_default(project):
    found = evidence("reviews~applies~at_least~4", 1)
    assert [text for text, _url in found][2] == "Review by ben: commented"
    assert len(found) == 4


def test_no_reviews_link_the_pull_request(project):
    assert evidence("reviews~applies~at_least~1~approved~changes_requested~dismissed", 2) == [
        ("Its reviews on GitHub", f"{URL}/2")
    ]
    assert Reviews.deciding(0, "at_least", 0) == 0


def test_the_author_links_the_page_in_the_project(project):
    value = "author~applies~review_ratio~below~1"
    assert evidence(value, 1, project) == [
        ("anna in the project", "/projects/icalendar/contributors/anna/")
    ]
    assert evidence(value, 1) == []  # no project, no page


def test_evidence_once_per_link():
    a = Evidence("A", "https://a")
    assert Evidence.unique([a, Evidence("B", "https://a")]) == [a]
    assert a.data() == {"text": "A", "url": "https://a"}


def test_the_page_of_a_pull_request_shows_the_evidence(client, project):
    saved = PullRequestFilter.objects.create(
        project=project, name="Checks", columns=["ci~applies~failing", "reviews~not~at_least~1"]
    )
    PullRequestStep.objects.create(project=project, filter=saved, name="Checks")
    page = client.get("/projects/icalendar/pull/1/").content.decode()
    assert f'<a href="{URL}/1/checks">Its checks on GitHub</a>' in page
    assert f'href="{URL}/1#pullrequestreview-50001">Review by ben: approved</a>' in page
    assert "pullrequestreview-50002" not in page  # one review shows at least one
    data = client.get("/projects/icalendar/pull/1.json").json()
    tasks = data["steps"][0]["tasks"]
    assert {"text": "Its checks on GitHub", "url": f"{URL}/1/checks"} in tasks[0]["evidence"]


def test_the_page_of_a_contributor(client, project):
    page = client.get("/projects/icalendar/contributors/ben/").content.decode()
    assert 'data-contributor="ben"' in page and "data-contributor-states" in page
    assert "Review to pull request ratio" in page and "∞" in page  # 3 reviews, no pull requests
    assert '<span class="tab-count">4</span>' in page  # reviews, of all kinds
    reviews = client.get("/projects/icalendar/contributors/BEN/?tab=reviews").content.decode()
    assert f'href="{URL}/1#pullrequestreview-50001"' in reviews and "50003" in reviews  # all kinds
    issues = client.get("/projects/icalendar/contributors/ben/?tab=issues").content.decode()
    assert "#5 An issue" in issues
    pulls = client.get("/projects/icalendar/contributors/ben/?tab=pull-requests")
    assert "data-contributor-none" in pulls.content.decode()
    anna = client.get("/projects/icalendar/contributors/anna/?tab=pull-requests")
    assert 'href="/projects/icalendar/pull/1/">#1 Reviewed' in anna.content.decode()


def test_a_contributor_not_in_the_project(client, project):
    answer = client.get("/projects/icalendar/contributors/nobody/")
    assert answer.status_code == 404
    assert "Person not found in the project" in answer.content.decode()


def test_the_page_of_a_contributor_chooses_the_kinds_of_reviews(client, project):
    """All kinds count by default; the gear chooses some, which the tabs and counts keep."""
    page = client.get("/projects/icalendar/contributors/ben/").content.decode()
    assert '<span class="tab-count">4</span>' in page  # with the comment
    assert "data-kinds-menu" in page and 'name="kinds" value="commented" checked' in page
    assert "Dismissed: an approval or a request for changes" in page
    chosen = client.get(
        "/projects/icalendar/contributors/ben/?kinds=approved&kinds=changes_requested"
    ).content.decode()
    assert '<span class="tab-count">3</span>' in chosen
    assert 'name="kinds" value="commented" checked' not in chosen
    assert 'href="?tab=reviews&amp;kinds=approved&amp;kinds=changes_requested"' in chosen
    reviews = client.get(
        "/projects/icalendar/contributors/ben/?tab=reviews&kinds=commented"
    ).content.decode()
    assert "pullrequestreview-50003" in reviews and "pullrequestreview-50001" not in reviews
