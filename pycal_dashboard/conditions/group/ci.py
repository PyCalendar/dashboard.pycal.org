"""The group of the continuous integration: passing or failing."""

from django.utils.translation import gettext_noop

from pycal_dashboard.conditions.condition.ci_fails import CiFails
from pycal_dashboard.conditions.condition.ci_passes import CiPasses
from pycal_dashboard.conditions.group.switches import SwitchesGroup


class CiGroup(SwitchesGroup):
    """The checks of a pull request: ``ci_passes`` or ``ci_fails``.

    The last complete result counts while new checks run. Its cell shows ``passing`` in green
    or ``failing`` in red.
    """

    id = "ci"
    title = gettext_noop("CI")
    switches = (
        ("passing", CiPasses, gettext_noop("passing")),
        ("failing", CiFails, gettext_noop("failing")),
    )
