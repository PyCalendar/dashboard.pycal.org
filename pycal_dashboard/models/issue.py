"""An issue or a pull request of a repository, as the site read it from GitHub."""

from django.db import models


class Issue(models.Model):
    """An issue or a pull request: on GitHub, a pull request is an issue with code.

    The site reads them all, open and closed, in the background (``RepositoryUpdate``): the
    title, who created it, when, and its description. They are public on GitHub for a public
    repository; those of a private repository are seen only by the collaborators of its
    private projects, like the repository.
    """

    OPEN = "open"
    CLOSED = "closed"
    STATES = [(OPEN, "open"), (CLOSED, "closed")]

    repository = models.ForeignKey("Repository", on_delete=models.CASCADE, related_name="issues")
    number = models.PositiveIntegerField()
    github_id = models.BigIntegerField(null=True, blank=True)
    pull_request = models.BooleanField(default=False)
    title = models.CharField(max_length=500)
    # who created it; None when GitHub does not say, such as for a deleted account
    author = models.ForeignKey(
        "GitHubUser", null=True, blank=True, on_delete=models.SET_NULL, related_name="issues"
    )
    description = models.TextField(blank=True)
    labels = models.ManyToManyField("Label", blank=True, related_name="issues")
    state = models.CharField(max_length=10, choices=STATES, default=OPEN)
    created = models.DateTimeField()
    # when it was closed, and merged for a pull request; when GitHub last changed it
    closed = models.DateTimeField(null=True, blank=True)
    merged = models.DateTimeField(null=True, blank=True)
    changed = models.DateTimeField(null=True, blank=True)
    # who closed it, read with the reviews (ReviewsData); None while not known
    closed_by = models.ForeignKey(
        "GitHubUser",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="closed_issues",
    )

    class Meta:
        ordering = ["-created"]
        constraints = [
            models.UniqueConstraint(fields=["repository", "number"], name="issue_number_unique")
        ]
        indexes = [models.Index(fields=["repository", "pull_request", "state"])]

    def __str__(self) -> str:
        return f"{self.repository_id}#{self.number} {self.title}"

    @property
    def url(self) -> str:
        """The issue or pull request on GitHub."""
        kind = "pull" if self.pull_request else "issues"
        return f"https://github.com/{self.repository.full_name}/{kind}/{self.number}"

    @property
    def status(self) -> str:
        """``open``, ``merged`` or ``closed``, as GitHub shows it."""
        if self.state == self.OPEN:
            return "open"
        return "merged" if self.merged else "closed"
