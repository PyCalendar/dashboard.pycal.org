"""A quality check of a step that a person skipped for a pull request, with the reason."""

from django.conf import settings
from django.db import models


class CheckSkip(models.Model):
    """A quality check of a step that a pull request skips, because a person said so.

    A skipped quality check keeps no pull request in its step: when every quality check of the
    step is done or skipped, the step is complete and the pull request goes on to the next one.
    The writers and owners of a project skip quality checks, and the author of the pull request
    does with the link of the PR message (``{quality_check_skip_url_author}``). Everybody sees
    that the quality check is skipped and who skipped it; only the writers and owners see the
    ``reason``, which is Markdown without variables.
    """

    step = models.ForeignKey(
        "PullRequestStep", on_delete=models.CASCADE, related_name="check_skips"
    )
    issue = models.ForeignKey("Issue", on_delete=models.CASCADE, related_name="check_skips")
    # the quality check: the column of its condition, as the filter of the step keeps it
    condition = models.TextField()
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="check_skips",
    )
    reason = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["step", "issue", "condition"], name="check_skip_unique")
        ]

    def __str__(self) -> str:
        return f"{self.issue_id} skips {self.condition} of {self.step_id}"
