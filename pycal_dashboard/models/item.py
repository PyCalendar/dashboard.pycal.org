"""An issue or a pull request of a repository."""

from django.db import models


class Item(models.Model):
    """An issue or pull request, as last read from GitHub."""

    repository = models.ForeignKey("Repository", on_delete=models.CASCADE, related_name="items")
    number = models.PositiveIntegerField()
    is_pull = models.BooleanField(default=False)
    title = models.CharField(max_length=500)
    state = models.CharField(max_length=10, default="open")  # open or closed
    draft = models.BooleanField(default=False)
    merged = models.BooleanField(default=False)
    author_login = models.CharField(max_length=100, db_index=True)
    author_association = models.CharField(max_length=40, blank=True, default="")
    author_is_bot = models.BooleanField(default=False)
    labels = models.JSONField(default=list, blank=True)
    comments = models.PositiveIntegerField(default=0)
    requested_reviewers = models.JSONField(default=list, blank=True)
    additions = models.PositiveIntegerField(null=True, blank=True)
    deletions = models.PositiveIntegerField(null=True, blank=True)
    html_url = models.URLField(blank=True, default="")
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    closed_at = models.DateTimeField(null=True, blank=True)
    merged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(fields=["repository", "number"], name="unique_item_number")
        ]
        indexes = [models.Index(fields=["state", "is_pull"])]

    def __str__(self) -> str:
        return f"{self.repository.full_name}#{self.number}"

    @property
    def kind(self) -> str:
        """``pull request`` or ``issue``."""
        return "pull request" if self.is_pull else "issue"

    @property
    def status(self) -> str:
        """``open``, ``draft``, ``merged`` or ``closed``."""
        if self.merged:
            return "merged"
        if self.state == "open" and self.draft:
            return "draft"
        return self.state
