"""Errors of labeling pull requests.

They are logged with the webhook delivery that caused them, on the page
*Webhook deliveries*, and on the page *Labels* of the repository.
"""

from .base import DashboardError


class LabelError(DashboardError):
    """A pull request could not be labeled.

    The detail shows the pull request and what GitHub answered. The labels are
    set again when the pull request changes or with ``manage.py
    sync_repositories``.
    """

    title = "The pull request could not be labeled"
    status = 502
    guide = "reference/labels.html"
    guide_title = "Labels of pull requests"


class CannotWriteLabels(LabelError):
    """The GitHub App may not write the labels of the pull request.

    The installation lacks the permission *Pull requests: write*. An owner of
    the organization accepts it in the settings of the installation on GitHub,
    see :doc:`/reference/permissions`.
    """

    title = "The GitHub App may not write labels"
    status = 403


class PullRequestSizeUnknown(LabelError):
    """GitHub did not say how many lines the pull request changes.

    The size label needs ``additions`` and ``deletions`` of the pull request.
    The label is set at the next change of the pull request.
    """

    title = "The size of the pull request is unknown"
