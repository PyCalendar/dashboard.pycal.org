"""A repository of an installation."""

from django.db import models


class Repository(models.Model):
    """A repository as GitHub describes it; private ones are kept but never shown."""

    github_id = models.BigIntegerField(unique=True)
    installation = models.ForeignKey(
        "Installation",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="repositories",
    )
    full_name = models.CharField(max_length=200, db_index=True)
    description = models.TextField(blank=True, default="")
    html_url = models.URLField(blank=True, default="")
    private = models.BooleanField(default=False)
    archived = models.BooleanField(default=False)
    fork = models.BooleanField(default=False)
    default_branch = models.CharField(max_length=200, default="main")
    language = models.CharField(max_length=100, blank=True, default="")
    topics = models.JSONField(default=list, blank=True)
    stars = models.PositiveIntegerField(default=0)
    forks = models.PositiveIntegerField(default=0)
    pushed_at = models.DateTimeField(null=True, blank=True)
    synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["full_name"]
        verbose_name_plural = "repositories"

    def __str__(self) -> str:
        return self.full_name

    @property
    def owner(self) -> str:
        """The organization or account, such as ``PyCalendar``."""
        return self.full_name.split("/", 1)[0]

    @property
    def name(self) -> str:
        """The name without the owner, such as ``icalendar``."""
        return self.full_name.split("/", 1)[-1]
