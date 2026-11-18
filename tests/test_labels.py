"""The rules of the labels and the labeler, against the fake GitHub."""

import pytest

from pycal_dashboard.errors import CannotWriteLabels, PullRequestSizeUnknown, UnknownLabelRule
from pycal_dashboard.github.app import GitHubApp
from pycal_dashboard.labels.rule_set import RuleSet
from pycal_dashboard.labels.size_rule import SizeRule
from pycal_dashboard.models import LabelChange
from pycal_dashboard.services.item_store import ItemStore
from pycal_dashboard.services.labeler import PullRequestLabeler
from tests.conftest import REPOSITORY


@pytest.mark.parametrize(
    ("lines", "label"),
    [
        (0, "size: XS"),
        (9, "size: XS"),
        (10, "size: S"),
        (49, "size: S"),
        (50, "size: M"),
        (249, "size: M"),
        (250, "size: L"),
        (999, "size: L"),
        (1000, "size: XL"),
    ],
)
def test_size_limits(lines, label):
    assert SizeRule().choose({"additions": lines, "deletions": 0}) == label


def test_size_unknown():
    with pytest.raises(PullRequestSizeUnknown):
        SizeRule().choose({"number": 3})


def test_unknown_rule():
    with pytest.raises(UnknownLabelRule, match="known: first-contribution, size"):
        RuleSet.parse("size,colour")


def test_labels_of_people_stay():
    rules = RuleSet.parse("size,first-contribution")
    added, removed = rules.changes(
        {"additions": 1, "deletions": 1, "author_association": "MEMBER"},
        {"bug", "first contribution", "size: XL"},
    )
    assert added == {"size: XS"}
    assert removed == {"first contribution", "size: XL"}


def labeler(github, db):
    github.install(1, "PyCalendar", [REPOSITORY])
    repository = ItemStore.repository(github.repositories[REPOSITORY])
    return repository, PullRequestLabeler(GitHubApp.for_installation(1), repository)


def test_label_a_pull_request(github, db):
    repository, labels = labeler(github, db)
    pull = github.pull(REPOSITORY, 3, author_association="FIRST_TIMER", labels=["bug"])
    ItemStore.item(repository, pull)
    assert labels.label(pull) == ({"first contribution", "size: XS"}, set())
    assert github.labels_of(REPOSITORY, 3) == ["bug", "first contribution", "size: XS"]
    assert set(github.repo_labels[REPOSITORY]) == {"first contribution", "size: XS"}
    assert repository.items.get(number=3).labels == ["bug", "first contribution", "size: XS"]
    assert LabelChange.objects.filter(repository=repository, added=True).count() == 2


def test_smallest_change(github, db):
    repository, labels = labeler(github, db)
    pull = github.pull(REPOSITORY, 3, additions=100, labels=["size: XS"])
    assert labels.label(pull) == ({"size: M"}, {"size: XS"})
    changes = [
        r for r in github.requests if r.method in ("POST", "DELETE") and "/issues/" in r.url.path
    ]
    assert len(changes) == 2
    github.requests.clear()
    pull["labels"] = [{"name": "size: M"}]
    assert labels.label(pull) == (set(), set())
    assert not [r for r in github.requests if r.method != "GET"]


def test_reads_the_size_of_a_listed_pull(github, db):
    repository, labels = labeler(github, db)
    github.pull(REPOSITORY, 3, additions=2000)
    listed = {"number": 3, "state": "open", "labels": []}
    assert labels.label(listed) == ({"size: XL"}, set())


def test_closed_pull_requests_are_not_labeled(github, db):
    repository, labels = labeler(github, db)
    pull = github.pull(REPOSITORY, 3, state="closed")
    assert labels.label(pull) == (set(), set())


def test_no_rules(github, db, settings):
    settings.PULL_REQUEST_LABELS = RuleSet.parse("")
    repository, labels = labeler(github, db)
    assert labels.label(github.pull(REPOSITORY, 3)) == (set(), set())


def test_missing_permission(github, db):
    repository, labels = labeler(github, db)
    pull = github.pull(REPOSITORY, 3)
    github.fail_with, github.fail_message = 403, "Resource not accessible by integration"
    with pytest.raises(CannotWriteLabels):
        labels.label(pull)
