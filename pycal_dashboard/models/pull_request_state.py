"""What a pull request is like now, beyond its issue: its branches, merging and checks."""

from django.db import models


class PullRequestState(models.Model):
    """The state of an open pull request that the conditions check, read in the background.

    GitHub computes ``mergeable`` after a change: None until it knows. ``mergeable_state`` is
    ``clean``, ``dirty`` (a conflict), ``behind`` (the branch is out of date), ``blocked``,
    ``unstable``, ``has_hooks`` or ``unknown``. ``checks`` sums up the checks and statuses of its
    last commit: ``success``, ``failure``, ``pending``, or "" while the site cannot read them;
    ``checks_complete`` is the last of them that is not ``pending``.
    """

    SUCCESS = "success"
    FAILURE = "failure"
    PENDING = "pending"

    issue = models.OneToOneField("Issue", on_delete=models.CASCADE, related_name="pull_state")
    head_sha = models.CharField(max_length=40, blank=True)
    head_ref = models.CharField(max_length=255, blank=True)
    base_ref = models.CharField(max_length=255, blank=True)
    mergeable = models.BooleanField(null=True, blank=True)
    mergeable_state = models.CharField(max_length=20, blank=True)
    auto_merge = models.BooleanField(default=False)
    checks = models.CharField(max_length=10, blank=True)
    # the last result of the checks that is complete: success or failure, while new ones run
    checks_complete = models.CharField(max_length=10, blank=True)
    # when the site read the pull request, and its checks, the last time
    updated = models.DateTimeField(null=True, blank=True)
    checks_updated = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "pull request state"

    def __str__(self) -> str:
        return f"{self.issue}: {self.mergeable_state or 'unknown'}"
