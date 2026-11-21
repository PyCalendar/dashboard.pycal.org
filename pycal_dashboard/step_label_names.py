"""The names, colors and descriptions of the labels of steps on GitHub, without GitHub itself.

The pages use them, so they need none of the packages that speak with GitHub.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from django.conf import settings

if TYPE_CHECKING:
    from pycal_dashboard.models import PullRequestStep

PREFIX = "Step: "  # what labels of steps had before their names, such as "Step: Review"
MAX_NAME = 50  # GitHub allows labels of at most 50 characters
MAX_DESCRIPTION = 100  # and descriptions of at most 100
DEFAULT_COLOR = "ededed"  # the gray of GitHub for a label: a step without a color


def label_name(step: PullRequestStep) -> str:
    """The name of the label of a step on GitHub: the name of the step.

    Parameters:
        step: The step.

    Returns:
        Such as ``Review``, at most 50 characters.
    """
    return step.name[:MAX_NAME].strip()


def step_name(label: str) -> str:
    """The name of a step from the name of its label, renamed on GitHub.

    Parameters:
        label: The name of the label, such as ``Peer review``.

    Returns:
        The name; without the prefix ``Step:`` that the labels had before.

    Examples:
        >>> step_name("Step: Peer review"), step_name("Peer review")
        ('Peer review', 'Peer review')
    """
    name = label[len(PREFIX) :] if label.lower().startswith(PREFIX.lower()) else label
    return " ".join(name.split())[:100] or label


def label_color(step: PullRequestStep) -> str:
    """The color of the label of a step: that of the step, else the gray of GitHub.

    Parameters:
        step: The step, whose color is such as ``#bbf7d0`` or "".

    Returns:
        Such as ``bbf7d0``, without ``#``.
    """
    return (step.color or "").lstrip("#").lower() or DEFAULT_COLOR


def step_color(label: str) -> str:
    """The color of a step from the color of its label, changed on GitHub.

    Parameters:
        label: Such as ``d73a4a``.

    Returns:
        Such as ``#d73a4a``; "" for the gray of GitHub: no color.

    Examples:
        >>> step_color("D73A4A"), step_color("ededed")
        ('#d73a4a', '')
    """
    color = label.lower().lstrip("#")
    return "" if color == DEFAULT_COLOR or not re.fullmatch(r"[0-9a-f]{6}", color) else f"#{color}"


def description(step: PullRequestStep) -> str:
    """The description of the label of a step: who made it, and the link to the step.

    Parameters:
        step: The step.

    Returns:
        Such as ``Created by dashboard.pycal.org: https://.../steps/?step_id=7``; the link alone
        when both do not fit into 100 characters.
    """
    url = f"{settings.SITE_URL}{step.project.path('steps/')}?step_id={step.pk}"
    text = f"Created by {settings.SITE_NAME}: {url}"
    return text if len(text) <= MAX_DESCRIPTION else url[:MAX_DESCRIPTION]
