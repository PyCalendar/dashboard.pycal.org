"""A filter of the pull requests of a project: its columns of conditions, saved with a name."""

from django.conf import settings
from django.db import models


class PullRequestFilter(models.Model):
    """The columns of conditions of the table of pull requests, saved for a project.

    ``columns`` keeps them in their order, each with its filter, as the address of the table
    keeps them (``Column.encode``), such as ``["labels~applies~present~bug"]``. The tab
    *Filters* of the project lists them; each opens the table of pull requests with them.
    """

    project = models.ForeignKey("Project", on_delete=models.CASCADE, related_name="filters")
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)  # Markdown
    columns = models.JSONField(default=list, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["project", "name"], name="filter_name_unique")
        ]

    def __str__(self) -> str:
        return f"{self.project}: {self.name}"
