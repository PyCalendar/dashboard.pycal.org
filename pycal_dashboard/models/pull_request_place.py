"""Where a pull request is in the steps of a project, as the site saw it last."""

from django.db import models


class PullRequestPlace(models.Model):
    """The step that an open pull request was in at the last update, None for none.

    When an update finds it no longer in that step and the step complete, the actions of the
    step follow (``StepCompletion``). The first time the site sees a pull request in a project,
    it only records its place: nothing happens for steps completed before.
    """

    project = models.ForeignKey("Project", on_delete=models.CASCADE, related_name="places")
    issue = models.ForeignKey("Issue", on_delete=models.CASCADE, related_name="places")
    step = models.ForeignKey(
        "PullRequestStep", null=True, blank=True, on_delete=models.SET_NULL, related_name="places"
    )
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["project", "issue"], name="place_unique")]

    def __str__(self) -> str:
        return f"{self.project_id}: {self.issue_id} in {self.step_id}"
