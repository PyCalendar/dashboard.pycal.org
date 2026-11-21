"""A step that a person skipped for a pull request, with the reason."""

from django.conf import settings
from django.db import models


class StepSkip(models.Model):
    """A step of a project that a pull request skips, because a writer of the project said so.

    The pull request is not in a skipped step: when it is the step it would be in, it is in the
    next one. Everybody sees that the step is skipped and who skipped it; only the writers and
    owners of the project see the ``reason``. A step also skips itself for the pull requests of
    the authors it names (``PullRequestStep.skip_authors``): such a skip is not saved, and it
    names nobody (:attr:`automatic`).
    """

    step = models.ForeignKey("PullRequestStep", on_delete=models.CASCADE, related_name="skips")
    issue = models.ForeignKey("Issue", on_delete=models.CASCADE, related_name="step_skips")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="step_skips",
    )
    reason = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["step", "issue"], name="step_skip_unique")]

    def __str__(self) -> str:
        return f"{self.issue_id} skips {self.step_id}"

    @property
    def automatic(self) -> bool:
        """Whether the step skips itself for the author of the pull request: nobody chose it."""
        return self.pk is None
