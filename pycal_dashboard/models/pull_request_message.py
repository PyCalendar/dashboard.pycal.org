"""The message of a project about the state of its pull requests, as a comment on each."""

from django.conf import settings
from django.db import models


class PullRequestMessage(models.Model):
    """A template of a message that the GitHub App writes as a comment on pull requests.

    It is off until a scope is switched on: the pull requests ``listed`` by their numbers (on
    by default, without numbers none), the open pull requests of the ``authors`` by their GitHub
    handles (on by default, without handles none), all new ones (opened after ``new_since``),
    all open ones, or the closed and merged ones too. People add their own GitHub handle to the
    ``authors`` on the page of signing up (``signup_text``). A pull request with the message has it
    updated whenever the message or its values change (``MessageComments``).
    """

    project = models.OneToOneField("Project", on_delete=models.CASCADE, related_name="message")
    template = models.TextField(blank=True)  # Markdown with the variables of steps
    # the message being edited, saved while it is edited; None when it is the template: Apply
    # makes it the template, which the pull requests get
    draft = models.TextField(null=True, blank=True)
    # the pull requests by their number, such as "42" or "collective/icalendar#42"
    listed = models.JSONField(default=list, blank=True)
    to_listed = models.BooleanField(default=True)
    # the GitHub handles of the authors whose open pull requests get it, such as ["octocat"]
    authors = models.JSONField(default=list, blank=True)
    to_authors = models.BooleanField(default=True)
    # the text of the page where people sign up for the message (Markdown); empty for the
    # default text, which says to sign in to enable it on the repositories
    signup_text = models.TextField(blank=True)
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
