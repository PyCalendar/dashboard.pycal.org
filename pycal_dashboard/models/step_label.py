"""The status label of a step in a repository on GitHub."""

from django.db import models


class StepLabel(models.Model):
    """The label of a step in a repository, which shows on GitHub which step a pull request is in.

    The site creates it, and keeps its name, description and color as the step has them
    (``StatusLabels``). It finds the label again by its id on GitHub (``github_id``): a label
    renamed or recolored on GitHub renames or recolors the step. ``name`` and ``color`` are what
    the site last saw or wrote, to tell a change on GitHub from one on the site.
    """

    step = models.ForeignKey("PullRequestStep", on_delete=models.CASCADE, related_name="labels")
    repository = models.ForeignKey(
        "Repository", on_delete=models.CASCADE, related_name="step_labels"
    )
    github_id = models.BigIntegerField(null=True, blank=True)
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=6, blank=True)  # such as d73a4a, without #
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["step", "repository"], name="step_label_unique")
        ]

    def __str__(self) -> str:
        return f"{self.repository_id}: {self.name}"
