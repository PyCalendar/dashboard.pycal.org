"""The names of the permissions and events are those of GitHub.

``pycal_dashboard/github/permission_names.txt`` is the page of the permissions of a GitHub App
on GitHub, as people see it: the reference of ``permission_names.py``.
"""

from pathlib import Path

import pytest

from pycal_dashboard.github.permission_names import EVENTS, GROUPS, PERMISSIONS
from pycal_dashboard.github.permissions import EVENTS as SUBSCRIBED
from pycal_dashboard.github.permissions import REQUIRED

REFERENCE = (
    Path(__file__).parent.parent / "pycal_dashboard" / "github" / "permission_names.txt"
).read_text()
LINES = [line.strip() for line in REFERENCE.splitlines() if line.strip()]
# events that GitHub offers only once their permissions are chosen: not on the page of reference
NOT_IN_REFERENCE = {"check_run", "check_suite", "status", "push"}


def test_every_permission_and_event_of_the_app_has_its_name():
    assert set(REQUIRED) <= set(PERMISSIONS)
    assert set(SUBSCRIBED) <= set(EVENTS)


@pytest.mark.parametrize("key", sorted(PERMISSIONS))
def test_a_permission_is_named_as_on_github(key):
    group, name, description = PERMISSIONS[key]
    assert str(GROUPS[group]) in REFERENCE
    assert name in LINES, name
    after = LINES[LINES.index(name) + 1 :][:3]  # the sentence follows, or "Selected" first
    assert any(line.startswith(str(description)) for line in after), (name, after)


@pytest.mark.parametrize("key", sorted(set(EVENTS) - NOT_IN_REFERENCE))
def test_an_event_is_named_as_on_github(key):
    name, description = EVENTS[key]
    line = next((line for line in LINES if line.startswith(name + " ")), "")
    assert line, name
    words = str(description).rstrip(".").split(", ")[0]
    assert words.split()[0] in line, (name, line)
