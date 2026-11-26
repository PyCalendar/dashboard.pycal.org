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
    phrase = (gettext_noop("PR CI is %(states)s"), gettext_noop("PR CI is not %(states)s"))

    @classmethod
    def opposite(cls, choices: tuple[str, ...]) -> tuple[str, ...] | None:
        """None: the other states of the CI are not the opposite for sure.

        The CI of a closed or merged pull request is unknown, and whether it passes or fails is
        not known, so failing is not known where passing or unknown holds. A column of the CI is
        inverted by its filter, or as the NOT of its condition, instead.

        Parameters:
            choices: The switches that are on.

        Returns:
            None.
        """
        return None

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
