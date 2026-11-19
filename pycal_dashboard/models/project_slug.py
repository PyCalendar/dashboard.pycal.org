"""A slug that a project has or had: old slugs lead to the project, forever."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import models
from django.utils import timezone

from pycal_dashboard.project_slugs import RESERVED

if TYPE_CHECKING:
    from pycal_dashboard.models import Project


class ProjectSlug(models.Model):
    """The time a project had a slug, ``/projects/<slug>/...``.

    Every slug that a project ever had stays recorded, so that links with it keep working and
    no other project takes it, also after the project was deleted (``project`` is then empty).
    The current slug has no ``until``.
    """

    slug = models.CharField(max_length=80, unique=True)
    project = models.ForeignKey(
        "Project",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="slugs",
    )
    since = models.DateTimeField(default=timezone.now)
    until = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-since"]
        verbose_name_plural = "project slugs"

    def __str__(self) -> str:
        return self.slug

    @classmethod
    def taken(cls, slug: str, project: Project | None = None) -> bool:
        """Whether a slug belongs or belonged to another project.

        Parameters:
            slug: The slug, in lower case.
            project: The project that asks; its own old sluges are free for it.

        Returns:
            True if it may not be used.
        """
        if slug in RESERVED:
            return True
        found = cls.objects.filter(slug=slug).first()
        if found is None:
            return False
        return project is None or found.project_id != project.pk
