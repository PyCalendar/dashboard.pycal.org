"""The group of the status: open, closed, merged, auto-merging."""

from django.utils.translation import gettext_noop

from pycal_dashboard.conditions.condition.auto_merge_enabled import AutoMergeEnabled
from pycal_dashboard.conditions.condition.closed import Closed
from pycal_dashboard.conditions.condition.draft import Draft
from pycal_dashboard.conditions.condition.merged import Merged
from pycal_dashboard.conditions.condition.open import Open
from pycal_dashboard.conditions.group.switches import SwitchesGroup


class StatusGroup(SwitchesGroup):
    """The status: ``open``, ``closed``, ``merged``, ``auto_merge_enabled`` and ``draft``.

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
        ("draft", Draft, gettext_noop("draft")),
    )
    exclusive = ("open", "closed", "merged")  # auto-merging and drafts are open, too
    phrase = (gettext_noop("PR is %(states)s"), gettext_noop("PR is not %(states)s"))
    words = {"draft": gettext_noop("a draft")}
