"""A project: a set of repositories on GitHub that people look at together."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone

from pycal_dashboard import project_slugs

from .project_slug import ProjectSlug

ATTEMPTS = 100  # random slugs tried before giving up; a million exist


def random_slug() -> str:
    """A random slug that no project has or had, such as ``3f9a0c``.

    Returns:
        The slug.
    """
    for _attempt in range(ATTEMPTS):
        slug = project_slugs.random_slug()
        if not ProjectSlug.taken(slug) and not Project.objects.filter(slug=slug).exists():
            return slug
    raise RuntimeError("no free random slug")  # pragma: no cover


class Project(models.Model):
    """A set of repositories, public or private, that the people of the project change.

    The person who creates it owns it; owners share it with others, who may read or also change
    it (``ProjectMember``). Who may do what is in ``ProjectAccess``. Its address is
    ``/projects/<slug>/<name>/``: the slug is random unless people choose one; every slug it had
    stays recorded (``ProjectSlug``), so that old links lead to it.
    """

    slug = models.CharField(max_length=80, unique=True, default=random_slug)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    public = models.BooleanField(default=True)
    repositories = models.ManyToManyField("Repository", blank=True, related_name="projects")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
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

    @property
    def name_part(self) -> str:
        """The name in the address, which only makes links readable."""
        return project_slugs.name_part(self.name)

    def path(self, page: str = "") -> str:
        """The address of a page of the project.

        Args:
            page: The page after the project, such as ``repositories/``; "" for the overview.

        Returns:
            The path, such as ``/projects/3f9a0c/icalendar/repositories/``.
        """
        return reverse("project", args=[self.slug, self.name_part]) + page

    def get_absolute_url(self) -> str:
        """The overview of the project, also for the Django admin."""
        return self.path()

    def clean(self) -> None:
        """Check the slug, such as when the Django admin changes it.

        Raises:
            ValidationError: The slug breaks the rules or belongs to another project.
        """
        self.slug = self.slug.strip().lower()
        if not project_slugs.valid(self.slug):
            raise ValidationError({"slug": "Only a to z, 0 to 9, single hyphens and one ~."})
        if ProjectSlug.taken(self.slug, self if self.pk else None):
            raise ValidationError({"slug": "Another project has or had this slug."})

    def save(self, *args, **kwargs) -> None:
        """Save the project and record its slug in the history of its slugs."""
        with transaction.atomic():
            super().save(*args, **kwargs)
            now = timezone.now()
            recorded, created = ProjectSlug.objects.get_or_create(
                slug=self.slug, defaults={"project": self, "since": now}
            )
            if not created and recorded.until is not None and recorded.project_id == self.pk:
                recorded.since, recorded.until = now, None  # back to an old slug of its own
                recorded.save(update_fields=["since", "until"])
            ProjectSlug.objects.filter(project=self, until=None).exclude(slug=self.slug).update(
                until=now
            )
