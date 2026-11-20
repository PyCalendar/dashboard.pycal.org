"""A comment that the GitHub App wrote on a pull request: the message of a project."""

from django.db import models


class PullRequestComment(models.Model):
    """The comment of the message of a project on a pull request, to update it, not repeat it.

    ``digest`` is the hash of the text it has on GitHub: a comment whose text would be the same
    is not written again.
    """

    project = models.ForeignKey("Project", on_delete=models.CASCADE, related_name="comments")
    issue = models.ForeignKey("Issue", on_delete=models.CASCADE, related_name="comments")
    github_id = models.BigIntegerField()
    digest = models.CharField(max_length=64)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["project", "issue"], name="comment_unique")]

    def __str__(self) -> str:
        return f"{self.project_id}: {self.issue_id} comment {self.github_id}"
