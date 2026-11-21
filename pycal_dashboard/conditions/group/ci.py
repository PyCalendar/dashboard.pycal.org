"""The group of the continuous integration: passing or failing."""

from django.utils.translation import gettext, gettext_noop

from pycal_dashboard.conditions.condition.ci_fails import CiFails
from pycal_dashboard.conditions.condition.ci_passes import CiPasses
from pycal_dashboard.conditions.condition.ci_unknown import CiUnknown
from pycal_dashboard.conditions.group.switches import SwitchesGroup
from pycal_dashboard.conditions.spec.checks import ChecksData
from pycal_dashboard.models import Issue


class CiGroup(SwitchesGroup):
    """The checks of a pull request: ``ci_passes``, ``ci_fails`` or ``ci_unknown``.

    The last complete result counts while new checks run. Its cell shows ``passing`` in green
    or ``failing`` in red.
    """

    id = "ci"
    title = gettext_noop("CI")
    switches = (
        ("passing", CiPasses, gettext_noop("passing")),
        ("failing", CiFails, gettext_noop("failing")),
        ("unknown", CiUnknown, gettext_noop("unknown")),
    )
    exclusive = ("passing", "failing", "unknown")
    help = gettext_noop(
        "Unknown: the checks are read for open pull requests only, so closed and merged ones "
        "are unknown; also open ones whose checks are not read yet, or that the GitHub App may "
        "not read."
    )
    phrase = (gettext_noop("its CI is %(states)s"), gettext_noop("its CI is not %(states)s"))

    @classmethod
    def unknown(cls, issue: Issue, choices: tuple[str, ...]) -> str:
        """Why the result of the checks is not known.

        Parameters:
            issue: The pull request.
            choices: The switches that are on.

        Returns:
            The reason, translated: closed, the permissions of the app, or not read yet.
        """
        if issue.state != Issue.OPEN:
            return gettext("not known: the checks are read for open pull requests only")
        installation = issue.repository.installation
        granted = dict(installation.permissions or {}) if installation else {}
        if not ChecksData().enabled(granted):
            return gettext(
                "not known: the GitHub App may not read the checks yet; the owners of its "
                "installation accept the permissions checks and statuses on GitHub"
            )
        return gettext("not known yet: no check of the last commit has completed")
