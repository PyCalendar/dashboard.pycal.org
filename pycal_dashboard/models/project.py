"""A project: a set of repositories on GitHub that people look at together."""

from django.conf import settings
from django.db import models


class Project(models.Model):
    """A set of repositories, public or private, that the people of the project change.

    The person who creates it owns it; owners share it with others, who may read or also change
    it (``ProjectMember``). Who may do what is in ``ProjectAccess``.
    """

    slug = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    public = models.BooleanField(default=True)
    repositories = models.ManyToManyField("Repository", blank=True, related_name="projects")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="created_projects",
    )
    created = models.DateTimeField(auto_now_add=True)
    # when an update of all its repositories ended last, None before the first
    updated = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
