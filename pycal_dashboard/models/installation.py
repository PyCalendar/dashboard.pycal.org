"""An installation of the GitHub App on an account or organization, with its permissions."""

from django.db import models

from pycal_dashboard.import_guard import IMPORT_GUARD


class Installation(models.Model):
    """The GitHub App installed on an account or an organization of GitHub.

    The permissions and events are those that the owners accepted, from the webhooks of the
    installation and the check at every start. When the site needs more, the people who
    installed or changed the installation get an email (``permissions_notified``). This is the
    only data of GitHub that the site keeps.
    """

    github_id = models.BigIntegerField(unique=True)
    account_login = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, default="User")  # User or Organization
    permissions = models.JSONField(default=dict, blank=True)
    events = models.JSONField(default=list, blank=True)
    # the GitHub ids of the people who installed or changed it: they get the emails
    admin_github_ids = models.JSONField(default=list, blank=True)
    # the missing permissions that the people were told about, such as "issues:read"
    permissions_notified = models.CharField(max_length=500, blank=True)
    suspended = models.BooleanField(default=False)
    removed = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["account_login"]

    def __str__(self) -> str:
        return f"{self.account_login} ({self.github_id})"

    @property
    def settings_url(self) -> str:
        """The page on GitHub where the installation is configured and permissions accepted.

        Examples:
            >>> organization = Installation(github_id=5, account_login="O")
            >>> organization.account_type = "Organization"
            >>> organization.settings_url
            'https://github.com/organizations/O/settings/installations/5'
            >>> Installation(github_id=6, account_login="me").settings_url
            'https://github.com/settings/installations/6'
        """
        if self.account_type == "Organization":
            return (
                f"https://github.com/organizations/{self.account_login}"
                f"/settings/installations/{self.github_id}"
            )
        return f"https://github.com/settings/installations/{self.github_id}"

    @property
    def missing_permissions(self) -> dict[str, str]:
        """The permissions that the site needs and the installation lacks."""
        with IMPORT_GUARD:  # see import_guard.py
            from pycal_dashboard.github.permissions import missing

        return missing(self.permissions or {})
