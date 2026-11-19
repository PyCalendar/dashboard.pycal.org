"""The group of the status: open, closed, merged, auto-merging."""

from django.utils.translation import gettext_noop

from pycal_dashboard.conditions.condition.auto_merge_enabled import AutoMergeEnabled
from pycal_dashboard.conditions.condition.closed import Closed
from pycal_dashboard.conditions.condition.merged import Merged
from pycal_dashboard.conditions.condition.open import Open
from pycal_dashboard.conditions.group.switches import SwitchesGroup


class StatusGroup(SwitchesGroup):
    """The status of a pull request: ``open``, ``closed``, ``merged``, ``auto_merge_enabled``.

    Its cell shows the status with its color, as the column of the status, and auto-merging
    when it is enabled.
    """

    id = "status"
    title = gettext_noop("Status")
    switches = (
        ("open", Open, gettext_noop("open")),
        ("closed", Closed, gettext_noop("closed")),
        ("merged", Merged, gettext_noop("merged")),
        ("auto_merge", AutoMergeEnabled, gettext_noop("auto-merging")),
    )
    exclusive = ("open", "closed", "merged")  # auto-merging is open, too
    phrase = (gettext_noop("it is %(states)s"), gettext_noop("it is not %(states)s"))
