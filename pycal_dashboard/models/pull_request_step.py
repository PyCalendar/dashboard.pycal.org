"""A step that pull requests of a project go through: a saved filter of what keeps them there."""

from django.db import models


class PullRequestStep(models.Model):
    """A step of the pull requests of a project, such as *Review* or *Fix the checks*.

    Its filter (exactly one) has the conditions that keep a pull request in the step: failures
    to remove before it can be merged. Steps more to the left (``position``) come first: a pull
    request is in the left-most step whose filter shows it, and in no step when none does.

    ``summary`` is a template in Markdown; ``conditions`` hold, for each condition of the
    filter by its value (``Column.encode``), a ``summary`` (a line of text) and a
    ``description`` (a template in Markdown) that guide people to remove it.
    """

    project = models.ForeignKey("Project", on_delete=models.CASCADE, related_name="steps")
    filter = models.OneToOneField(
        "PullRequestFilter", on_delete=models.CASCADE, related_name="step"
    )
    name = models.CharField(max_length=100)
    summary = models.TextField(blank=True)  # a template in Markdown
    conditions = models.JSONField(default=dict, blank=True)
    position = models.PositiveIntegerField(default=0)
    # not shown in the bar of the page of a pull request, unless the pull request is in it
    hidden = models.BooleanField(default=False)
    # the color of its background, such as #fde68a; "" for none (STEP_COLORS of views/steps.py)
    color = models.CharField(max_length=7, blank=True)
    # what the site does when a pull request enters or leaves the step, such as
    # [{"kind": "add_label", "label": "reviewed"}] (StepCompletion)
    actions = models.JSONField(default=list, blank=True)
    # the GitHub handles of the authors whose pull requests skip the step, such as
    # ["niccokunzmann"] (StepOverrides)
    skip_authors = models.JSONField(default=list, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position", "pk"]

    def __str__(self) -> str:
        return f"{self.project}: {self.name}"
