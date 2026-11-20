"""A review of a pull request, as the site read it from GitHub."""

from django.db import models


class Review(models.Model):
    """A review that a person gave on a pull request: approved, changes requested, commented.

    The background reads the reviews of all pull requests of a repository
    (``ReviewsData``), so that the states of people count them, such as ``reviews_given``.
    """

    github_id = models.BigIntegerField(unique=True)
    issue = models.ForeignKey("Issue", on_delete=models.CASCADE, related_name="reviews")
    # who gave it; None when GitHub does not say, such as for a deleted account
    author = models.ForeignKey(
        "GitHubUser", null=True, blank=True, on_delete=models.SET_NULL, related_name="reviews"
    )
    # APPROVED, CHANGES_REQUESTED, COMMENTED or DISMISSED, as GitHub names them
    state = models.CharField(max_length=20, blank=True)
    submitted = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["submitted", "pk"]
        indexes = [models.Index(fields=["author", "issue"])]

    def __str__(self) -> str:
        return f"{self.issue_id}: {self.state} by {self.author_id}"
