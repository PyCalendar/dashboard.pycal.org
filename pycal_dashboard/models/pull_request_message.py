"""The message of a project about the state of its pull requests, as a comment on each."""

from django.conf import settings
from django.db import models


class PullRequestMessage(models.Model):
    """A template of a message that the GitHub App writes as a comment on pull requests.

    It is off until a scope is switched on: the pull requests ``listed`` by their numbers (on
    by default, without numbers none), all new ones (opened after ``new_since``), all open ones,
    or the closed and merged ones too. A pull request with the message has it updated whenever
    the message or its values change (``MessageComments``).
    """

    project = models.OneToOneField("Project", on_delete=models.CASCADE, related_name="message")
    template = models.TextField(blank=True)  # Markdown with the variables of steps
    # the pull requests by their number, such as "42" or "collective/icalendar#42"
    listed = models.JSONField(default=list, blank=True)
    to_listed = models.BooleanField(default=True)
    to_new = models.BooleanField(default=False)
    new_since = models.DateTimeField(null=True, blank=True)  # when to_new was switched on
    to_open = models.BooleanField(default=False)
    to_closed = models.BooleanField(default=False)
    updated = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )

    def __str__(self) -> str:
        return f"{self.project}: message"
