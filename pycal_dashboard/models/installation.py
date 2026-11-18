"""An installation of the GitHub App on an organization or account."""

from django.db import models


class Installation(models.Model):
    """Where the GitHub App is installed; its repositories appear on the dashboard."""

    github_id = models.BigIntegerField(unique=True)
    account_login = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, default="Organization")
    permissions = models.JSONField(default=dict)
    suspended = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.account_login} ({self.github_id})"
