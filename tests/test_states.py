"""The states of people, shared with the conditions: reviews, pull requests opened and closed."""

import math
import re
from pathlib import Path

import pytest

from pycal_dashboard import errors
from pycal_dashboard.conditions import CONDITIONS, STATES
from pycal_dashboard.conditions.condition.base import Condition
from pycal_dashboard.conditions.input.number import NumberInput
from pycal_dashboard.conditions.state.base import State
from pycal_dashboard.conditions.state.scope import Scope
from pycal_dashboard.models import GitHubUser, Issue, Repository, Review
from pycal_dashboard.services.repository_update import RepositoryUpdate

pytestmark = pytest.mark.django_db
DOCS = Path(__file__).parent.parent / "docs" / "reference" / "states"
REPO = "collective/icalendar"
OTHER = "collective/other"
ANNA = {"id": 101, "login": "anna", "avatar_url": "https://avatars.example/a", "type": "User"}
BEN = {"id": 102, "login": "ben", "avatar_url": "https://avatars.example/b", "type": "User"}
BOT = {"id": 103, "login": "helper[bot]", "avatar_url": "https://avatars.example/c", "type": "Bot"}


@pytest.fixture
def repositories(github):
    """Anna opened three pull requests and withdrew one; Ben reviews in two repositories."""
    github.add_repository(REPO, installation=11)
    github.add_repository(OTHER, installation=11)
    github.add_issue(REPO, "Anna 1", pull_request=True, user=ANNA)
    github.add_issue(REPO, "Anna 2", pull_request=True, user=ANNA, state="closed", merged=True)
    github.add_issue(REPO, "Anna withdrawn", pull_request=True, user=ANNA, state="closed")
    github.add_issue(REPO, "Ben 1", pull_request=True, user=BEN)
    github.add_issue(
        REPO, "Ben closed by Anna", pull_request=True, user=BEN, state="closed", closed_by=ANNA
    )
    github.add_issue(OTHER, "Bot", pull_request=True, user=BOT)
    github.add_review(REPO, 1, BEN)  # approved
    github.add_review(REPO, 1, BEN, "CHANGES_REQUESTED")
    github.add_review(REPO, 1, ANNA, "COMMENTED")  # on her own: counts only with ``own``
    github.add_review(REPO, 4, ANNA)
    github.add_review(OTHER, 1, BEN, "DISMISSED")
    found = []
    for name in (REPO, OTHER):
        repository = Repository.objects.create(full_name=name)
        assert RepositoryUpdate(repository).run()
        repository.refresh_from_db()
        found.append(repository)
    return found


def pull(title):
    return Issue.objects.select_related("author", "repository").get(title=title)


def person(login):
    return GitHubUser.objects.get(login=login)


def test_the_states_have_their_ids():
    assert list(STATES) == [
        "pull_requests_opened",
        "own_pull_requests_closed",
        "reviews_given",
        "review_ratio",
    ]
    assert issubclass(Condition, State)  # a condition is a state that is true or false
    assert all(issubclass(state, State) for state in STATES.values())


@pytest.mark.parametrize("id", list(STATES))
def test_every_state_has_its_page_with_the_api_at_the_bottom(id, settings):
    state = STATES[id]
    page = (DOCS / f"{id}.rst").read_text()
    assert page.startswith("=") and f"``{id}``" in page.split("\n")[1]
    assert " ".join(state.description.split()) in " ".join(page.split())
    for spec in state.data:
        assert f"``{spec.id}``" in page
    api = page.rsplit("API reference\n=============", 1)
    assert f".. autoclass:: {state.__module__}.{state.__name__}" in api[1]
    assert not re.search(r"\n[^\n]+\n={3,}\n", api[1]), "no section after it"
    settings.DOCS_URL = "https://docs.example.org/"
    assert state.docs_url() == f"https://docs.example.org/reference/states/{id}.html"
    assert state.describe()["documentation"] == state.docs_url()  # shared with conditions
    index = (DOCS / "index.rst").read_text()
    assert f":doc:`{id}`" in index and f"   {id}\n" in index


def test_the_update_reads_the_reviews_and_who_closed(repositories, github):
    repository, _other = repositories
    assert repository.reviews_changed is not None
    reviews = Review.objects.filter(issue__repository=repository)
    assert sorted(reviews.values_list("author__login", "state")) == [
        ("anna", "APPROVED"),
        ("anna", "COMMENTED"),
        ("ben", "APPROVED"),
        ("ben", "CHANGES_REQUESTED"),
    ]
    assert pull("Anna withdrawn").closed_by.login == "anna"
    assert pull("Ben closed by Anna").closed_by.login == "anna"
    assert pull("Anna 1").closed_by is None  # open
    assert person("helper[bot]").type == "Bot"
    assert github.graphql_reviews_queries[0]["variables"]["first"] == 20


def test_the_next_update_reads_only_what_changed(repositories, github):
    repository, _other = repositories
    github.graphql_reviews_queries.clear()
    github.add_review(REPO, 4, BEN)  # changes Ben 1, the last changed now
    assert RepositoryUpdate(repository).run()
    assert Review.objects.filter(issue__title="Ben 1").count() == 2
    (query,) = github.graphql_reviews_queries  # stopped at what it had read


def test_the_states_of_a_person_in_a_project(repositories):
    scope = Scope(repositories)
    anna = pull("Anna 1")
    assert STATES["pull_requests_opened"].observe(anna, scope) == 3
    assert STATES["own_pull_requests_closed"].observe(anna, scope) == 1  # not the merged one
    # all kinds, but not her comment on her own pull request
    assert STATES["reviews_given"].observe(anna, scope) == 1
    assert STATES["review_ratio"].observe(anna, scope) == 0.5  # 1 / (3 - 1)
    own = {"kinds": ("approved", "changes_requested", "commented", "dismissed", "own")}
    assert STATES["reviews_given"].observe(anna, scope, own) == 2  # also the comment
    assert STATES["review_ratio"].observe(anna, scope, own) == 1  # 2 / (3 - 1)
    no_comments = {"kinds": ("approved", "changes_requested", "dismissed", "own")}
    assert STATES["reviews_given"].observe(anna, scope, no_comments) == 1
    ben = person("ben")
    assert STATES["reviews_given"].observe(ben, scope) == 3  # in both repositories
    assert STATES["own_pull_requests_closed"].observe(ben, scope) == 0  # Anna closed it
    assert STATES["review_ratio"].observe(ben, scope) == 1.5  # 3 / (2 - 0)
    assert STATES["reviews_given"].observe(pull("Ben 1")) == 2  # its repository only


def test_the_ratio_without_pull_requests(repositories):
    scope = Scope(repositories)
    reviewer = GitHubUser.objects.create(github_id=200, login="reviewer")
    Review.objects.create(github_id=1, issue=pull("Anna 1"), author=reviewer, state="APPROVED")
    assert STATES["review_ratio"].observe(reviewer, scope) == math.inf
    nobody = GitHubUser.objects.create(github_id=201, login="nobody")
    assert STATES["review_ratio"].observe(nobody, scope) == 0


def test_the_numbers_are_counted_once_for_everybody(repositories, django_assert_num_queries):
    scope = Scope(repositories)
    pulls = list(Issue.objects.filter(pull_request=True).select_related("author", "repository"))
    with django_assert_num_queries(3):  # opened, closed by themselves, reviews
        for issue in pulls:
            STATES["review_ratio"].observe(issue, scope)


def test_unknown_while_the_reviews_are_not_read(repositories):
    repository, other = repositories
    other.reviews_changed = None
    other.save()
    assert STATES["reviews_given"].observe(pull("Anna 1"), Scope([repository, other])) is None
    assert STATES["reviews_given"].observe(pull("Anna 1"), Scope([repository])) == 1
    assert STATES["pull_requests_opened"].observe(pull("Anna 1"), Scope([repository])) == 3
    assert (
        CONDITIONS["review_ratio"].check(
            pull("Anna 1"), {"comparison": "above", "ratio": 0.1}, Scope([repository, other])
        )
        is None
    )


def test_without_an_author_there_is_no_state(repositories):
    issue = pull("Anna 1")
    issue.author = None
    assert STATES["reviews_given"].observe(issue) is None


@pytest.mark.parametrize(
    ("comparison", "number", "anna", "ben"),
    [  # Anna 1 has 3 reviews (approved, changes, a comment), Ben 1 has 1
        ("at_least", 2, True, False),  # the number counts
        ("at_most", 1, False, True),
        ("above", 1, True, False),
        ("below", 2, False, True),
        ("exactly", 1, False, True),
    ],
)
def test_reviews(repositories, comparison, number, anna, ben):
    condition = CONDITIONS["reviews"]
    values = condition.configure({"comparison": comparison, "reviews": str(number)})
    assert condition.check(pull("Anna 1"), values) is anna
    assert condition.check(pull("Ben 1"), values) is ben


def test_reviews_at_least_by_default(repositories):
    condition = CONDITIONS["reviews"]
    assert condition.configure({"reviews": 0}) == {
        "comparison": "at_least",
        "reviews": 0,
        "kinds": ("approved", "changes_requested", "commented", "dismissed"),
    }
    with pytest.raises(errors.ConditionInputUnknown):
        condition.configure({"comparison": "around", "reviews": 1})
    with pytest.raises(errors.ConditionInputOutOfRange):
        condition.configure({"reviews": -1})


def test_the_kinds_of_reviews_count(repositories):
    """Anna 1 has an approval, a request for changes and her own comment: all kinds by default,
    but not the reviews of the author; ``own`` counts them, too."""
    condition = CONDITIONS["reviews"]
    every = condition.configure({"comparison": "exactly", "reviews": 2})
    own = condition.configure({"comparison": "exactly", "reviews": 3, "kinds": "commented, own"})
    assert own["kinds"] == ("commented", "own")
    assert condition.check(pull("Anna 1"), own) is False  # her comment alone
    kinds = "approved, changes_requested, commented, own"
    own = condition.configure({"comparison": "exactly", "reviews": 3, "kinds": kinds})
    assert condition.check(pull("Anna 1"), own) is True  # with her comment
    two = condition.configure(
        {"comparison": "exactly", "reviews": 2, "kinds": "approved, changes_requested"}
    )
    assert two["kinds"] == ("approved", "changes_requested")
    assert condition.check(pull("Anna 1"), every) is True
    assert condition.check(pull("Anna 1"), two) is True
    with pytest.raises(errors.ConditionInputUnknown):
        condition.configure({"reviews": 1, "kinds": "maybe"})
    with pytest.raises(errors.ConditionInputMissing):
        condition.configure({"reviews": 1, "kinds": []})


def test_a_column_of_kinds_of_reviews(repositories):
    from django.http import QueryDict

    from pycal_dashboard.conditions.group.column import Column
    from pycal_dashboard.conditions.group.reviews import ReviewsGroup

    old = Column.decode("reviews~applies~at_least~2~comments")  # saved before: all kinds
    assert old.encode() == "reviews~applies~at_least~2" and old.applies(pull("Anna 1")) is True
    own = Column.decode("reviews~applies~at_least~1~own~commented")  # her own comment
    assert own.encode() == "reviews~applies~at_least~1~commented~own"
    assert own.applies(pull("Anna 1")) is True
    assert (
        own.sentence
        == "it has at least 1 review: commented, also by the author of the pull request"
    )
    assert Column.decode("reviews~applies~at_least~1~commented").applies(pull("Anna 1")) is False
    column = Column.decode("reviews~applies~at_least~2~changes_requested~approved")
    assert column.encode() == "reviews~applies~at_least~2~approved~changes_requested"
    assert column.applies(pull("Anna 1")) is True and column.kinds == column.choices[2:]
    assert Column.decode("reviews~applies~at_least~2~commented").applies(pull("Anna 1")) is False
    assert column.sentence == "it has at least 2 reviews: approved or changes requested"
    assert column.inverted().encode() == "reviews~applies~below~2~approved~changes_requested"
    assert [part["text"] for part in column.head] == [
        "reviews ≥ 2",
        "approved, changes requested",
    ]
    assert column.group.summary(column.choices) == (
        "Reviews: at least 2 (approved or changes requested)"
    )
    assert column.group.cell(pull("Anna 1"), column.choices)[0]["text"] == "2 reviews"
    assert [e.text for e in column.evidence(pull("Anna 1"))] == [
        "Review by ben: approved",
        "Review by ben: changes requested",
    ]
    form = QueryDict(
        "reviews_comparison=below&reviews=2&reviews_kinds_form=1&reviews_kinds=commented"
    )
    assert ReviewsGroup.parse(form) == ("below", "2", "commented")
    every = "&".join(
        f"reviews_kinds={k}" for k in ("approved", "changes_requested", "commented", "dismissed")
    )
    assert ReviewsGroup.parse(QueryDict(f"reviews=2&reviews_kinds_form=1&{every}")) == (
        "at_least",
        "2",
    )  # all of them: no choice
    assert ReviewsGroup.parse(QueryDict("reviews=2")) == ("at_least", "2")
    with pytest.raises(errors.ConditionInputMissing):
        ReviewsGroup.parse(QueryDict("reviews=2&reviews_kinds_form=1"))
    with pytest.raises(errors.ConditionInputUnknown):
        Column.decode("reviews~all~at_least~1~everything")


def test_the_inputs_of_states_travel(repositories):
    """A state made of others, and a condition of a state, have all their inputs."""
    from pycal_dashboard.conditions.state.base import State

    for state in STATES.values():
        names = {spec.name for spec in state.inputs}
        for part in state.parts:
            assert {spec.name for spec in part.inputs} <= names, (state.id, part.id)
    assert {spec.name for spec in STATES["review_ratio"].inputs} == {"kinds"}
    ratio = {spec.name for spec in CONDITIONS["review_ratio"].inputs}
    assert {spec.name for spec in STATES["review_ratio"].inputs} <= ratio
    assert {spec.name for spec in CONDITIONS["reviews"].inputs} >= {"kinds"}
    kinds = [spec for state in STATES.values() for spec in state.inputs if spec.name == "kinds"]
    kinds += [spec for c in CONDITIONS.values() for spec in c.inputs if spec.name == "kinds"]
    assert len({(spec.type, spec.default) for spec in kinds}) == 1  # the same everywhere
    assert State.inputs_of() == ()


def test_review_ratio(repositories):
    condition = CONDITIONS["review_ratio"]
    scope = Scope(repositories)
    above = {"comparison": "above"}
    assert condition.check(pull("Ben 1"), condition.configure({"ratio": "1.4"}), scope) is True
    assert condition.check(pull("Ben 1"), condition.configure({"ratio": 1.5}), scope) is False
    assert condition.check(pull("Ben 1"), {"comparison": "at_least", "ratio": 1.5}, scope)
    assert condition.check(pull("Anna 1"), {**above, "ratio": 0.4}, scope) is True
    assert condition.check(pull("Anna 1"), {"comparison": "below", "ratio": 1.5}) is True
    assert [i["type"] for i in condition.describe()["inputs"]] == [
        "comparison",
        "number",
        "review-kinds",
    ]
    no_comments = {"comparison": "below", "ratio": 0.6, "kinds": ("approved",)}
    assert condition.check(pull("Anna 1"), no_comments, scope) is True  # 1 / 2


@pytest.mark.parametrize(
    ("value", "error"),
    [
        ("many", errors.ConditionInputNotNumber),
        (True, errors.ConditionInputNotNumber),
        ("inf", errors.ConditionInputNotNumber),
        (-1, errors.ConditionInputOutOfRange),
    ],
)
def test_a_number_input_refuses_wrong_values(value, error):
    with pytest.raises(error):
        NumberInput("ratio", "Ratio", minimum=0).parse(value)


def test_a_number_input_makes_its_field():
    assert NumberInput("ratio", "Ratio", minimum=0).widget() == {
        "kind": "number",
        "attributes": {"step": "any", "min": 0},
    }
    assert NumberInput("ratio", "Ratio", maximum=3).describe()["maximum"] == 3


def test_without_the_app_reviews_are_not_read(github):
    github.add_repository(REPO, pulls=1)
    repository = Repository.objects.create(full_name=REPO)
    assert RepositoryUpdate(repository).run()
    repository.refresh_from_db()
    assert repository.reviews_changed is None and github.graphql_reviews_queries == []
    assert CONDITIONS["reviews"].check(Issue.objects.get(), {"reviews": 1}) is None


# the columns of the table: the groups Reviews and Author


@pytest.fixture
def project(repositories, bob):
    from pycal_dashboard.services.project_editor import ProjectEditor

    project = ProjectEditor.create(bob, "iCalendar", slug="icalendar")
    project.repositories.add(*repositories)
    return project


def test_a_column_of_reviews(repositories):
    from pycal_dashboard.conditions.group.column import Column

    column = Column.decode("reviews~applies~2")  # as saved before: at least
    assert column.encode() == "reviews~applies~at_least~2"
    assert column.applies(pull("Anna 1")) is True and column.applies(pull("Ben 1")) is False
    assert column.sentence == "it has at least 2 reviews"
    assert column.head[0]["text"] == "reviews ≥ 2"
    assert column.opposite() is None
    assert column.inverted().encode() == "reviews~applies~below~2"
    assert Column.decode("reviews~not~at_least~1").sentence == "it has fewer than 1 review"
    assert Column.decode("reviews~all~exactly~0").sentence == "it has exactly 0 reviews"
    exactly = Column.decode("reviews~applies~exactly~1")
    assert exactly.inverted().encode() == "reviews~not~exactly~1"  # no opposite comparison
    assert exactly.inverted().sentence == "it has not exactly 1 review"
    assert column.group.cell(pull("Anna 1"), column.choices) == [
        {"text": "2 reviews", "kind": "number"}
    ]  # all kinds count, but not the comment of its author
    with pytest.raises(errors.ConditionInputOutOfRange):
        Column.decode("reviews~all~at_least~-1")


def test_a_column_of_the_author(repositories):
    from pycal_dashboard.conditions.group.column import Column

    scope = Scope(repositories)
    column = Column.decode("author~applies~review_ratio~1.40")  # as saved before: above
    assert column.encode() == "author~applies~review_ratio~above~1.4"
    assert column.head[0]["text"] == "Review to pull request ratio > 1.4"
    assert column.inverted().sentence == (
        "its author has a review to pull request ratio at most 1.4"
    )
    assert column.applies(pull("Ben 1"), scope) is True  # 1.5 in the project
    assert column.applies(pull("Ben 1")) is False  # 2 reviews / 2 in its repository only
    assert column.applies(pull("Anna 1"), scope) is False  # 0.5: not her own comment
    assert column.sentence == "its author has a review to pull request ratio above 1.4"
    assert column.group.cell(pull("Ben 1"), column.choices, scope)[0]["text"] == "1.5"
    assert column.group.summary(column.choices) == (
        "Author: review to pull request ratio above 1.4"
    )
    given = Column.decode("author~not~reviews_given~above~2")
    assert given.sentence == "its author gave at most 2 reviews"
    below = Column.decode("author~applies~reviews_given~below~2")
    assert below.sentence == "its author gave fewer than 2 reviews"
    assert below.applies(pull("Anna 1"), scope) is True  # 1 review: not her own comment
    with_own = Column.decode(f"{below.encode()}~approved~changes_requested~commented~dismissed~own")
    assert with_own.applies(pull("Anna 1"), scope) is False  # 2 reviews, with the comment
    approvals = Column.decode("author~applies~reviews_given~below~2~approved")
    assert approvals.applies(pull("Anna 1"), scope) is True  # 1 approval
    assert approvals.sentence == "its author gave fewer than 2 reviews (reviews: approved)"
    assert [part["text"] for part in approvals.head] == ["Reviews given < 2", "approved"]
    assert Column.decode("author~all~pull_requests_opened~below~2~approved").encode() == (
        "author~all~pull_requests_opened~below~2"
    )  # opened pull requests have no kinds of reviews
    assert given.shows(given.applies(pull("Anna 1"), scope)) is True
    with pytest.raises(errors.ConditionInputUnknown):
        Column.decode("author~all~nothing~1")
    with pytest.raises(errors.ConditionInputNotNumber):
        Column.decode("author~all~review_ratio~above~many")
    with pytest.raises(errors.ConditionInputUnknown):
        Column.decode("author~all~review_ratio~around~1")


def test_the_author_is_unknown_without_the_reviews(repositories):
    from pycal_dashboard.conditions.group.column import Column

    _repository, other = repositories
    other.reviews_changed = None
    other.save()
    column = Column.decode("author~applies~reviews_given~0")
    assert column.applies(pull("Anna 1"), Scope(repositories)) is None
    assert "need the GitHub App" in column.group.unknown(pull("Anna 1"), column.choices)


def test_the_table_counts_in_the_project(client, project):
    page = client.get(
        "/projects/icalendar/pull-requests/?col=author~applies~review_ratio~1.4"
    ).content.decode()
    assert page.count("<tr data-pull-request=") == 2  # the two of Ben: 1.5 in the project
    assert "Review to pull request ratio &gt; 1.4" in page
    menu = client.get("/projects/icalendar/pull-requests/").content.decode()
    assert 'class="group-fields fields-author"' in menu and 'value="review_ratio"' in menu
    assert 'name="reviews" type="number"' in menu


def test_a_column_from_the_menu(client, project):
    answer = client.get(
        "/projects/icalendar/pull-requests/?add=1&group=author&state=reviews_given&number=2"
    )
    location = answer["Location"].replace("~", "%7E")
    assert "col=author%7Eall%7Ereviews_given%7Ebelow%7E2" in location  # below by default
    answer = client.get(
        "/projects/icalendar/pull-requests/?add=1&group=reviews&reviews_comparison=at_most"
        "&reviews=2"
    )
    assert "reviews%7Eall%7Eat_most%7E2" in answer["Location"].replace("~", "%7E")
    menu = client.get("/projects/icalendar/pull-requests/").content.decode()
    assert '<option value="below" selected>below &lt;<' in menu
    assert '<option value="at_least" selected>at least ≥' in menu


def test_a_step_counts_in_the_project(project):
    from pycal_dashboard.models import PullRequestFilter, PullRequestStep
    from pycal_dashboard.services.progress import PullRequestProgress
    from pycal_dashboard.services.step_assignment import StepAssignment

    saved = PullRequestFilter.objects.create(
        project=project, name="Review more", columns=["author~not~review_ratio~1"]
    )
    step = PullRequestStep.objects.create(project=project, filter=saved, name="Review more")
    assignment = StepAssignment(project)
    assert assignment.step_of(pull("Anna 1")) == step  # 0.5: to review more
    assert assignment.step_of(pull("Ben 1")) is None  # 1.5
    progress = PullRequestProgress(pull("Anna 1"), project)
    assert progress.current.tasks[0].todo
