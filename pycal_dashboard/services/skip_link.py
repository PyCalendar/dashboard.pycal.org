"""The addresses that open the dialog to skip a step or a quality check of a pull request."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlencode

from django.utils.crypto import constant_time_compare, salted_hmac

from pycal_dashboard.step_template import steps_url

if TYPE_CHECKING:
    from pycal_dashboard.models import Issue, Project, PullRequestStep

# what the dialog skips: the step itself, else a quality check by the column of its condition
STEP = "step"


class SkipLink:
    """The links to skip a step, or one of its quality checks, for one pull request.

    Each opens the page of the pull request with the step shown and the dialog that asks why it
    may be skipped (``?step=7&skip=step``, or the condition of the quality check after
    ``skip=``). The link of the writers and owners of the project
    (``{step_skip_url}``, ``{quality_check_skip_url}``) holds nothing secret. The link
    of the author (``{step_skip_url_author}``, ``{quality_check_skip_url_author}``) also
    has a ``key``: a secret of dashboard.pycal.org for this pull request, step and quality
    check, which lets the author of the pull request skip it, too, after signing in. Nobody
    else can make the key, so the author skips only what the project offers them in a text.
    """

    def __init__(self, project: Project, issue: Issue, step: PullRequestStep):
        """The links of a step of a pull request.

        Parameters:
            project: The project.
            issue: The pull request.
            step: The step.
        """
        self.project = project
        self.issue = issue
        self.step = step

    def key(self, target: str) -> str:
        """The secret of the link of the author.

        Parameters:
            target: ``step``, or the condition of a quality check.

        Returns:
            20 hexadecimal digits, made with the ``SECRET_KEY``.
        """
        value = f"{self.issue.pk}:{self.step.pk}:{target}"
        return salted_hmac("pycal_dashboard.skip_link", value).hexdigest()[:20]

    def valid(self, target: str, key: str) -> bool:
        """Whether a key is that of the link of the author.

        Parameters:
            target: ``step``, or the condition of a quality check.
            key: The key of the address; "" for none.

        Returns:
            True if it is.
        """
        return bool(key) and constant_time_compare(self.key(target), key)

    def url(self, target: str = STEP, author: bool = False) -> str:
        """The address that opens the dialog.

        Parameters:
            target: ``step``, or the condition of a quality check.
            author: Whether it is the link of the author, with the key.

        Returns:
            Such as ``https://dashboard.pycal.org/projects/icalendar/pull/42/?repository=
            collective%2Ficalendar&step=7&skip=step``.
        """
        query = {"step": self.step.pk, "skip": target}
        if author:
            query["key"] = self.key(target)
        page = steps_url(self.project, self.issue.number, self.issue.repository.full_name)
        return f"{page}&{urlencode(query)}"

    def values(self, condition: str = "") -> dict[str, str]:
        """The variables of the links.

        Parameters:
            condition: The quality check; "" for the step.

        Returns:
            ``step_skip_url`` and ``step_skip_url_author``, or with a condition
            ``quality_check_skip_url`` and ``quality_check_skip_url_author``.
        """
        prefix = "quality_check" if condition else "step"
        target = condition or STEP
        return {
            f"{prefix}_skip_url": self.url(target),
            f"{prefix}_skip_url_author": self.url(target, author=True),
        }
