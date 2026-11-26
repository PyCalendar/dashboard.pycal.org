"""The factory of the conditions: it makes them, and writes them down and reads them again."""

import pytest

from pycal_dashboard import errors
from pycal_dashboard.conditions import CONDITIONS
from pycal_dashboard.conditions.condition.any_of import AnyOf
from pycal_dashboard.conditions.condition.closed import Closed
from pycal_dashboard.conditions.condition.label_exists import LabelExists
from pycal_dashboard.conditions.condition.merged import Merged
from pycal_dashboard.conditions.condition.negation import Not
from pycal_dashboard.conditions.condition.open import Open
from pycal_dashboard.conditions.condition.reviews import Reviews
from pycal_dashboard.conditions.factory import ConditionFactory
from pycal_dashboard.conditions.group.column import GROUPS, Column
from pycal_dashboard.conditions.group.labels import LabelsGroup
from pycal_dashboard.conditions.group.reviews import ReviewsGroup
from pycal_dashboard.models import Issue

from .test_steps import project  # noqa: F401 (fixture)

# a creation spec of every condition
SPECS = {
    "label_exists": {"label": "bug"},
    "label_absent": {"label": "bug"},
    "reviews": {"comparison": "below", "reviews": 2, "kinds": ("approved",)},
    "review_ratio": {"comparison": "below", "ratio": 1.5},
    "author_state": {"state": "reviews_given", "comparison": "at_least", "number": 2},
    "author_type": {"types": ("member", "owner")},
    "text_matches": {"field": "title", "mode": "starts", "text": "WIP"},
}


@pytest.mark.parametrize("id", list(CONDITIONS))
def test_every_condition_yields_the_spec_that_made_it(id):
    """Made of its class, of its id or of its spec with the id: always the same condition."""
    factory = ConditionFactory()
    condition = factory.create(id, SPECS.get(id, {}))
    assert condition == factory.create(CONDITIONS[id], SPECS.get(id, {}))
    assert factory.create(id, condition.spec()) == condition
    assert factory.load(factory.dump(condition)) == condition
    assert factory.dump(condition)["id"] == id
    assert hash(condition) == hash(factory.load(factory.dump(condition)))
    assert condition.negate().negate() == condition


def test_label_absent_and_the_not_of_label_present_are_the_same():
    factory = ConditionFactory()
    absent = factory.create("label_absent", {"label": "bug"})
    assert absent == factory.create(LabelExists, {"label": "bug"}).negate()
    assert absent == factory.create(LabelExists.negate(), {"label": "bug"})
    assert absent == LabelExists({"label": "bug"}).negate()
    assert isinstance(absent, Not) and absent.id == "label_absent"
    assert absent.negate() == LabelExists({"label": "bug"})
    assert absent.spec() == {"label": "bug"}
    assert factory.dump(absent) == {"id": "label_absent", "label": "bug"}


def test_the_choices_absent_and_the_not_of_present_read_the_same():
    """Both read as the NOT of present; the default writes it as absent."""
    factory = ConditionFactory()
    absent = factory.decode(LabelsGroup, ("absent", "bug"))
    assert absent == factory.decode(LabelsGroup, ("present", "bug"), negated=True)
    assert factory.encode(LabelsGroup, absent) == (("absent", "bug"), False)
    present = factory.decode(LabelsGroup, ("absent", "bug"), negated=True)
    assert present == LabelExists({"label": "bug"})
    assert factory.encode(LabelsGroup, present) == (("present", "bug"), False)
    for value in ("not~labels~applies~present~bug", "labels~applies~absent~bug"):
        assert Column.decode(value).encode() == "labels~applies~absent~bug"
    assert Column.decode("not~labels~skip~absent~bug").encode() == "labels~skip~present~bug"


def test_the_not_of_a_comparison_is_the_opposite_comparison():
    factory = ConditionFactory()
    below = factory.decode(ReviewsGroup, ("at_least", "2"), negated=True)
    assert factory.encode(ReviewsGroup, below) == (("below", "2"), False)
    assert Column.decode("not~reviews~applies~at_least~2").encode() == "reviews~applies~below~2"
    exactly = factory.decode(ReviewsGroup, ("exactly", "2"), negated=True)
    assert factory.encode(ReviewsGroup, exactly) == (("exactly", "2"), True)  # no opposite
    author = "not~author~all~reviews_given~below~2"
    assert Column.decode(author).encode() == "author~all~reviews_given~at_least~2"


def test_a_not_without_choices_of_its_own_is_written_with_not():
    factory = ConditionFactory()
    status = GROUPS["status"]
    assert factory.encode(status, Open().negate()) == (("open",), True)
    both = factory.decode(status, ("open", "merged"), negated=True)
    assert both == AnyOf([Open(), Merged()]).negate()
    assert factory.encode(status, both) == (("open", "merged"), True)
    assert Column.decode("not~status~skip~open~merged").encode() == "not~status~skip~open~merged"


def test_a_group_has_no_choices_for_a_condition_of_another():
    with pytest.raises(errors.ConditionNotInGroup):
        ConditionFactory().encode(LabelsGroup, Reviews({"reviews": 1}))
    with pytest.raises(errors.ConditionNotInGroup):
        ConditionFactory().encode(LabelsGroup, Reviews({"reviews": 1}).negate())


def test_the_groups_leave_the_conditions_to_the_factory():
    """No group checks conditions or inverts them itself: the column does, through the factory."""
    for group in GROUPS.values():
        for name in ("applies", "evidence", "invert"):
            assert not hasattr(group, name), (group.id, name)


@pytest.mark.parametrize("id", list(GROUPS))
def test_every_group_reads_the_choices_it_writes(id):
    from .test_invert import EXAMPLES

    factory = ConditionFactory()
    for example in EXAMPLES:
        if example.split("~")[0] == id:
            column = Column.decode(example.format("applies"))
            choices = column.group.choices_of(column.group.specs(column.choices))
            assert choices == column.choices
            assert factory.encode(column.group, column.condition) == (column.choices, False)


@pytest.mark.django_db
def test_any_of_holds_when_one_holds(project):  # noqa: F811
    both = AnyOf([Open(), Closed()])
    assert both == ConditionFactory().any_of([Open(), Closed()]) and hash(both)
    assert ConditionFactory().any_of([Open()]) == Open()
    assert both.spec() == {"conditions": (Open(), Closed())}
    for issue in Issue.objects.filter(pull_request=True):
        results = [Open().check(issue), Closed().check(issue)]
        assert both.check(issue) is (True if any(results) else False)
        assert both.negate().check(issue) is (not any(results))


def test_the_not_keeps_what_it_reads_of_its_condition_as_a_property():
    """The second time, the attribute is found on the class, without __getattr__."""
    absent = LabelExists.negate()({"label": "bug"})
    assert absent.inputs == LabelExists.inputs
    assert isinstance(Not.__dict__["inputs"], property)
    assert Not(Open()).inputs == () and Not(LabelExists).inputs == LabelExists.inputs
    with pytest.raises(AttributeError):
        Not(Open()).nothing  # noqa: B018 - it raises
    assert "nothing" not in Not.__dict__
    assert Not(Open(), "x").id == "x"  # its own attributes are not those of the condition
