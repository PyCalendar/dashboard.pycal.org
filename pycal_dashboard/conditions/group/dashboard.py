"""The group of the data of the dashboard: the PR Sync and the skips of steps."""

from __future__ import annotations

from django.utils.translation import gettext_noop

from pycal_dashboard.conditions.condition.pr_sync_on import PrSyncOn
from pycal_dashboard.conditions.condition.step_skipped import StepSkipped
from pycal_dashboard.conditions.group.switches import SwitchesGroup


class DashboardGroup(SwitchesGroup):
    """What the dashboard keeps of a pull request: ``pr_sync`` and ``step_skipped``.

    The data is of the project, not of GitHub, so the results are not kept in the cache under
    the version of the repositories: they change when the PR Sync writes its message or a
    writer skips a step.
    """

    id = "dashboard"
    title = gettext_noop("Dashboard")
    cached = False
    switches = (
        ("sync", PrSyncOn, gettext_noop("PR Sync on")),
        ("skipped", StepSkipped, gettext_noop("a skipped step")),
    )
    phrase = (gettext_noop("it has %(states)s"), gettext_noop("it does not have %(states)s"))
    words = {"sync": gettext_noop("the PR Sync on")}
    help = gettext_noop(
        "Data of the dashboard, not of GitHub: whether the PR Sync of the project is on for a "
        "pull request, and whether it skips a step, skipped by a person or for its author."
    )
