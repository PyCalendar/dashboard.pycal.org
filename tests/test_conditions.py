"""The conditions of pull requests: their ids, inputs, data, documentation and assessment."""

import re
from pathlib import Path

import pytest
from django.template.loader import render_to_string

from pycal_dashboard import errors
from pycal_dashboard.conditions import CONDITIONS, DATA_SPECS, ChecksData, find
from pycal_dashboard.conditions.input.integer import IntegerInput
from pycal_dashboard.conditions.input.label import LabelInput
from pycal_dashboard.conditions.input.positive_integer import PositiveIntegerInput
from pycal_dashboard.conditions.input.range import RangeInput
from pycal_dashboard.conditions.input.text import TextInput
from pycal_dashboard.models import Issue, Label, PullRequestState, Repository
from pycal_dashboard.services.repository_update import RepositoryUpdate

DOCS = Path(__file__).parent.parent / "docs" / "reference" / "conditions"
IDS = [
    "label_exists",
    "label_absent",
    "ci_passes",
    "ci_fails",
    "merge_conflict",
    "branch_outdated",
    "auto_merge_enabled",
    "open",
    "merged",
    "closed",
]
REPO = "collective/icalendar"


def test_the_conditions_have_their_ids():
    assert list(CONDITIONS) == IDS
    assert all(find(id).id == id for id in IDS)
    with pytest.raises(errors.UnknownCondition):
        find("nothing")


@pytest.mark.parametrize("id", IDS)
def test_every_condition_has_its_page_with_the_api_at_the_bottom(id, settings):
    """Its page describes it, its inputs and data, and ends with its API reference."""
    condition = CONDITIONS[id]
    page = (DOCS / f"{id}.rst").read_text()
    assert page.startswith("=") and f"``{id}``" in page.split("\n")[1]
    assert condition.description in page
    for spec in condition.inputs:
        assert f"``{spec.name}``" in page and f"``{spec.type}``" in page
    for spec in condition.data:
        assert f"``{spec.id}``" in page
        for permission in spec.permissions:
            assert f"``{permission}``" in page
        if not spec.enabled():
            assert "does not ask for these permissions yet" in page
    api = page.rsplit("API reference\n=============", 1)
    assert len(api) == 2, "the API reference is the last section"
    assert f".. autoclass:: {condition.__module__}.{condition.__name__}" in api[1]
    assert not re.search(r"\n[^\n]+\n={3,}\n", api[1]), "no section after it"
    settings.DOCS_URL = "https://docs.example.org/"
    assert condition.docs_url() == f"https://docs.example.org/reference/conditions/{id}.html"
    index = (DOCS / "index.rst").read_text()
    assert f":doc:`{id}`" in index and f"   {id}\n" in index


def test_every_condition_and_data_is_in_the_api_reference():
    api = (DOCS / "api.rst").read_text()
    for condition in CONDITIONS.values():
        assert f".. automodule:: {condition.__module__}" in api
    for spec in DATA_SPECS:
        assert f".. automodule:: {type(spec).__module__}" in api


# the inputs


@pytest.mark.parametrize(
    ("spec", "value", "parsed"),
    [
        (TextInput("t", "T"), " hello ", "hello"),
        (IntegerInput("i", "I"), "-3", -3),
        (IntegerInput("i", "I", minimum=0, maximum=9), 9, 9),
        (PositiveIntegerInput("p", "P"), "1", 1),
        (RangeInput("r", "R"), [2, 5], (2, 5)),
        (RangeInput("r", "R"), "2-5", (2, 5)),
        (LabelInput("l", "L"), "anything", "anything"),  # without a repository
    ],
)
def test_inputs_parse_their_values(spec, value, parsed):
    assert spec.parse(value) == parsed


@pytest.mark.parametrize(
    ("spec", "value", "error"),
    [
        (TextInput("t", "T"), "", errors.ConditionInputNotText),
        (TextInput("t", "T"), 3, errors.ConditionInputNotText),
        (TextInput("t", "T", max_length=2), "abc", errors.ConditionInputNotText),
        (IntegerInput("i", "I"), "x", errors.ConditionInputNotInteger),
        (IntegerInput("i", "I"), 1.5, errors.ConditionInputNotInteger),
        (IntegerInput("i", "I"), True, errors.ConditionInputNotInteger),
        (IntegerInput("i", "I", maximum=9), 10, errors.ConditionInputOutOfRange),
        (PositiveIntegerInput("p", "P"), 0, errors.ConditionInputOutOfRange),
        (RangeInput("r", "R"), [5, 2], errors.ConditionRangeInvalid),
        (RangeInput("r", "R"), [1], errors.ConditionRangeInvalid),
        (RangeInput("r", "R"), ["a", 2], errors.ConditionRangeInvalid),
        (RangeInput("r", "R", minimum=0), [-1, 2], errors.ConditionInputOutOfRange),
    ],
)
def test_inputs_refuse_wrong_values(spec, value, error):
    with pytest.raises(error):
        spec.parse(value)


@pytest.mark.django_db
def test_a_label_input_is_restricted_to_the_labels_of_the_repository():
    repository = Repository.objects.create(full_name=REPO)
    Label.objects.create(repository=repository, name="Needs Review", color="fbca04")
    spec = LabelInput("label", "Label")
    assert spec.parse("needs review", {"repository": repository}) == "Needs Review"
    with pytest.raises(errors.ConditionLabelUnknown):
        spec.parse("bug", {"repository": repository})
    widget = spec.widget({"repository": repository})
    assert widget["kind"] == "choice" and widget["choices"][0]["value"] == "Needs Review"


def test_inputs_describe_themselves():
    described = IntegerInput("days", "Days", "How many days.", minimum=1).describe()
    assert described == {
        "name": "days",
        "type": "int",
        "label": "Days",
        "help": "How many days.",
        "required": True,
        "default": None,
        "minimum": 1,
        "maximum": None,
    }
    assert PositiveIntegerInput("n", "N").type == "positive-int"
    assert LabelInput("l", "L").type == "string-label"


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("spec", "value", "html"),
    [
        (TextInput("word", "Word", "A word."), "hi", 'maxlength="200" required value="hi"'),
        (
            PositiveIntegerInput("days", "Days"),
            3,
            'type="number" inputmode="numeric" step="1" min="1"',
        ),
        (RangeInput("size", "Size", minimum=0), None, 'aria-label="To" step="1" min="0"'),
    ],
)
def test_an_input_makes_its_field(spec, value, html):
    """The input spec makes the field of a form, with the partial conditions/_input.html."""
    page = render_to_string(
        "pycal_dashboard/conditions/_input.html",
        {"spec": spec, "widget": spec.widget(), "value": value},
    )
    assert f'data-condition-input="{spec.name}"' in page and f'data-type="{spec.type}"' in page
    assert html in page
    assert f'<label for="input-{spec.name}">{spec.label}</label>' in page


@pytest.mark.django_db
def test_a_label_input_makes_a_choice_of_the_labels():
    repository = Repository.objects.create(full_name=REPO)
    Label.objects.create(repository=repository, name="bug", description="Something is wrong")
    spec = LabelInput("label", "Label")
    page = render_to_string(
        "pycal_dashboard/conditions/_input.html",
        {"spec": spec, "widget": spec.widget({"repository": repository}), "value": "bug"},
    )
    assert '<option value="bug" selected title="Something is wrong">bug</option>' in page


# configuring and assessing


def test_configure_a_condition():
    exists = CONDITIONS["label_exists"]
    assert exists.configure({"label": " bug "}) == {"label": "bug"}
    with pytest.raises(errors.ConditionInputMissing):
        exists.configure({})
    with pytest.raises(errors.ConditionInputUnknown):
        exists.configure({"label": "bug", "colour": "red"})
    assert CONDITIONS["merge_conflict"].configure() == {}
    described = exists.describe()
    assert described["id"] == "label_exists" and described["inputs"][0]["type"] == "string-label"
    assert described["data"][0] == {
        "id": "labels",
        "title": "The labels of the repository and of the pull request",
        "permissions": {"metadata": "read", "issues": "read"},
        "events": ["label", "issues", "pull_request"],
        "enabled": True,
    }


@pytest.fixture
def repository(github):
    github.add_repository(REPO, installation=11)
    github.add_label(REPO, "unused", "No pull request has it", "000000")
    github.add_issue(REPO, "An issue", labels=("bug",))
    github.add_issue(REPO, "Ready", pull_request=True, labels=("needs review",), auto_merge=True)
    github.add_issue(REPO, "Conflict", pull_request=True, mergeable_state="dirty")
    github.add_issue(REPO, "Behind", pull_request=True, mergeable_state="behind")
    github.add_issue(REPO, "Computing", pull_request=True, mergeable_state="unknown")
    github.add_issue(REPO, "Closed", pull_request=True, state="closed", merged=True)
    github.add_issue(REPO, "Refused", pull_request=True, state="closed")
    repository = Repository.objects.create(full_name=REPO)
    assert RepositoryUpdate(repository).run()
    repository.refresh_from_db()
    return repository


def pull(title):
    return Issue.objects.select_related("pull_state", "repository").get(title=title)


@pytest.mark.django_db
def test_the_update_reads_the_data_of_the_conditions(repository, github):
    labels = {label.name: label for label in repository.labels.all()}
    assert set(labels) == {"unused", "bug", "needs review"}
    assert labels["unused"].description == "No pull request has it"
    assert list(pull("Ready").labels.values_list("name", flat=True)) == ["needs review"]
    assert github.pull_requests_read == []  # no request for each pull request:
    (query,) = github.graphql_queries  # one query of GraphQL for all open ones
    assert "mergeStateStatus" in query["query"] and "statusCheckRollup" in query["query"]
    assert query["variables"] == {
        "owner": "collective",
        "name": "icalendar",
        "after": None,
        "first": 20,
    }
    state = pull("Conflict").pull_state
    assert (state.mergeable, state.mergeable_state, state.base_ref) == (False, "dirty", "main")
    assert pull("Ready").pull_state.auto_merge and not pull("Behind").pull_state.auto_merge
    assert not PullRequestState.objects.filter(issue__title="Closed").exists()
    assert ChecksData().enabled()  # the app asks for checks and statuses
    assert PullRequestState.objects.get(issue__title="Ready").checks == "success"  # none ran


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("id", "config", "results"),
    [
        ("label_exists", {"label": "needs review"}, {"Ready": True, "Conflict": False}),
        ("label_absent", {"label": "needs review"}, {"Ready": False, "Conflict": True}),
        ("merge_conflict", {}, {"Conflict": True, "Ready": False, "Behind": False}),
        ("branch_outdated", {}, {"Behind": True, "Ready": False, "Conflict": False}),
        ("auto_merge_enabled", {}, {"Ready": True, "Behind": False}),
        ("merge_conflict", {}, {"Computing": None}),  # GitHub does not know yet
        ("ci_passes", {}, {"Ready": True}),  # no checks: nothing failed
        ("ci_fails", {}, {"Ready": False}),
        ("label_exists", {"label": "bug"}, {"An issue": None}),  # pull requests only
        ("open", {}, {"Ready": True, "Closed": False}),
        ("merged", {}, {"Closed": True, "Ready": False}),
        ("closed", {}, {"Closed": False, "Ready": False, "Refused": True}),
    ],
)
def test_the_conditions_are_assessed(repository, id, config, results):
    condition = CONDITIONS[id]
    values = condition.configure(config, {"repository": repository})
    assert {title: condition.check(pull(title), values) for title in results} == results


@pytest.mark.django_db
def test_a_change_makes_the_state_incomplete_until_it_is_read(repository):
    from django.utils import timezone

    ready = pull("Ready")
    assert CONDITIONS["auto_merge_enabled"].complete(ready)
    Issue.objects.filter(pk=ready.pk).update(changed=timezone.now())
    assert not CONDITIONS["auto_merge_enabled"].complete(pull("Ready"))


@pytest.mark.django_db
def test_without_the_app_the_states_are_not_read(github):
    github.add_repository("public/one")
    github.add_issue("public/one", "Change", pull_request=True)
    repository = Repository.objects.create(full_name="public/one")
    assert RepositoryUpdate(repository).run()
    assert github.pull_requests_read == [] and not PullRequestState.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("rollup", "summary", "passes", "fails"),
    [
        ("SUCCESS", "success", True, False),
        (None, "success", True, False),  # no checks
        ("FAILURE", "failure", False, True),
        ("ERROR", "failure", False, True),
        ("PENDING", "pending", False, False),
        ("EXPECTED", "pending", False, False),
    ],
)
def test_ci_from_the_rollup_of_github(github, rollup, summary, passes, fails):
    """GitHub sums up the check runs and commit statuses of the last commit."""
    github.add_repository(REPO, installation=11)
    github.add_issue(REPO, "Change", pull_request=True)
    github.set_checks(REPO, 1, rollup)
    repository = Repository.objects.create(full_name=REPO)
    assert RepositoryUpdate(repository).run()
    change = pull("Change")
    assert change.pull_state.checks == summary
    assert CONDITIONS["ci_passes"].check(change, {}) is passes
    assert CONDITIONS["ci_fails"].check(change, {}) is fails


@pytest.mark.django_db
def test_many_open_pull_requests_are_read_page_by_page(github):
    github.add_repository(REPO, installation=11, pulls=45)
    repository = Repository.objects.create(full_name=REPO)
    assert RepositoryUpdate(repository).run()
    assert [q["variables"]["after"] for q in github.graphql_queries] == [None, "20", "40"]
    assert PullRequestState.objects.count() == 45


@pytest.mark.django_db
def test_a_refused_query_is_kept_as_the_error(github, monkeypatch):
    from pycal_dashboard.github.client import GitHubClient

    def refused(self, query, **variables):
        raise errors.GitHubQueryFailed("GraphQL undefinedField: mergeStateStatus")

    monkeypatch.setattr(GitHubClient, "graphql", refused)
    github.add_repository(REPO, installation=11, pulls=1)
    repository = Repository.objects.create(full_name=REPO)
    assert not RepositoryUpdate(repository).run()
    repository.refresh_from_db()
    assert repository.error_code == "GitHubQueryFailed" and repository.data_version == 0


@pytest.mark.django_db
def test_removed_labels_are_removed(repository, github):
    github.repositories[REPO]["labels"] = [
        label for label in github.repositories[REPO]["labels"] if label["name"] != "unused"
    ]
    RepositoryUpdate(repository).run()
    assert not repository.labels.filter(name="unused").exists()
