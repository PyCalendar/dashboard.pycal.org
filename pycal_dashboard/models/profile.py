"""The private preferences of a person who signed in."""

from django.conf import settings
from django.db import models


class Profile(models.Model):
    """What a person chose on the page Account; nobody else sees it."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dashboard_profile"
    )
    # emails about the account and the site, to the verified primary address
    email_notifications = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"preferences of {self.user}"
