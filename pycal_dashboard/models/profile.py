"""The private preferences of a person who signed in."""

from django.conf import settings
from django.db import models


class Profile(models.Model):
    """What a person chose on the page Account; nobody else sees it."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dashboard_profile"
    )
    # a weekly email with what waits for the person: reviews, answers to their issues
    email_digest = models.BooleanField(default=False)
    # the start page shows these repositories first
    watched = models.ManyToManyField("Repository", blank=True, related_name="watchers")
    show_drafts = models.BooleanField(default=True)
    days = models.PositiveIntegerField(default=90)  # the period of the statistics

    def __str__(self) -> str:
        return f"preferences of {self.user}"
