"""A notification of a person on the site, such as an installation that needs permissions."""

from django.conf import settings
from django.db import models


class Notification(models.Model):
    """Something a person should know or do, shown in their menu until they read it.

    A notification is about one thing, its ``kind`` and ``key``, such as the permissions of an
    installation: one per person and thing. It is resolved when the thing is done, such as
    when the owners accepted the permissions; ``params`` hold what its text says, which the
    page translates when it shows it.
    """

    PERMISSIONS = "permissions"  # an installation of the GitHub App lacks permissions
    APP_PERMISSIONS = "app_permissions"  # the GitHub App itself lacks permissions or events
    KINDS = [(PERMISSIONS, "permissions"), (APP_PERMISSIONS, "app permissions")]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    kind = models.CharField(max_length=30, choices=KINDS)
    key = models.CharField(max_length=100)  # such as the id of the installation
    params = models.JSONField(default=dict, blank=True)
    url = models.URLField(max_length=300, blank=True)  # where to act, such as on GitHub
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    read = models.DateTimeField(null=True, blank=True)
    resolved = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-updated"]
        constraints = [
            models.UniqueConstraint(fields=["user", "kind", "key"], name="notification_unique")
        ]
        indexes = [models.Index(fields=["user", "read", "resolved"])]

    def __str__(self) -> str:
        return f"{self.user}: {self.kind} {self.key}"

    @property
    def active(self) -> bool:
        """Whether it still asks for something: not resolved."""
        return self.resolved is None
