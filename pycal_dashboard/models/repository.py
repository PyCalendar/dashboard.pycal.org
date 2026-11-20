"""A repository on GitHub that is part of projects, with what the site read of it."""

from django.db import models


class Repository(models.Model):
    """A repository on GitHub, in one or more projects (``Project.repositories``).

    The site reads its description, whether it is private, the numbers of open issues and
    pull requests, and all its issues and pull requests (``Issue``) in the background
    (``UpdateJob``). A private repository is only in private
    projects, see ``ProjectAccess``.
    """

    full_name = models.CharField(max_length=140, unique=True)  # owner/name, as on GitHub
    github_id = models.BigIntegerField(null=True, blank=True, unique=True)
    private = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    installation = models.ForeignKey(
        "Installation",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="repositories",
    )
    open_issues = models.PositiveIntegerField(null=True, blank=True)
    open_pull_requests = models.PositiveIntegerField(null=True, blank=True)
    # when the site read it last, None before; the error of the last reading, "" for none
    updated = models.DateTimeField(null=True, blank=True)
    error_code = models.CharField(max_length=100, blank=True)
    error_detail = models.CharField(max_length=500, blank=True)
    error_at = models.DateTimeField(null=True, blank=True)  # when the last update failed
    # the version of what the site keeps of GitHub when it was read completely the last time,
    # 0 for never: below DATA_VERSION (github/data_version.py), it is read completely again
    data_version = models.PositiveSmallIntegerField(default=0)
    # when GitHub last changed the issues and pull requests the site has: the next update
    # reads only those changed since
    issues_changed = models.DateTimeField(null=True, blank=True)
    # when GitHub last changed the pull requests whose reviews and closers the site read
    # (ReviewsData): the next update reads those changed since; None while never read
    reviews_changed = models.DateTimeField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["full_name"]
        verbose_name_plural = "repositories"

    def __str__(self) -> str:
        return self.full_name

    @property
    def owner(self) -> str:
        """The account of the repository, such as ``PyCalendar``."""
        return self.full_name.split("/", 1)[0]

    @property
    def name(self) -> str:
        """The name without the account, such as ``icalendar``."""
        return self.full_name.split("/", 1)[-1]

    @property
    def url(self) -> str:
        """The repository on GitHub."""
        return f"https://github.com/{self.full_name}"

    @property
    def app_installed(self) -> bool:
        """Whether the GitHub App is installed on it and the installation is active."""
        installation = self.installation
        return bool(installation and not installation.removed and not installation.suspended)
