"""Tell the administrators of the site when the GitHub App itself lacks permissions or events."""

from __future__ import annotations

from typing import TYPE_CHECKING

from allauth.socialaccount.models import SocialAccount
from django.conf import settings

from pycal_dashboard.models import Notification

from .notifier import Notifier

if TYPE_CHECKING:
    from pycal_dashboard.github.app_check import AppCheck

# the app is one: the key of its notification
KEY = "app"


class AppNotice:
    """The notification of the administrators while the GitHub App lacks something.

    A new version of the site may need permissions or events that the registration of the app
    on GitHub does not have yet. Its owner adds them in the settings of the app first; only
    then does GitHub ask the owners of each installation to accept them.
    """

    def __init__(self, check: AppCheck):
        """The notice of the app as GitHub describes it.

        Parameters:
            check: What the app has and lacks.
        """
        self.check = check

    @staticmethod
    def user_ids() -> list[int]:
        """The users of the administrators of the site (``SITE_ADMINS``) who signed in.

        Returns:
            Their ids.
        """
        admins = {login.lower() for login in settings.SITE_ADMINS}
        return [
            account.user_id
            for account in SocialAccount.objects.filter(provider="github")
            if str((account.extra_data or {}).get("login", "")).lower() in admins
        ]

    def notify(self) -> bool:
        """Notify the administrators while the app lacks something, else resolve it.

        Returns:
            True if the app lacks something.
        """
        notifier = Notifier(Notification.APP_PERMISSIONS, KEY)
        if self.check.complete:
            notifier.resolve()
            return False
        params = {
            "app": str(self.check.app.get("slug", "")),
            "missing": dict(sorted(self.check.missing_permissions.items())),
            "events": sorted(self.check.missing_events),
        }
        notifier.notify(self.user_ids(), params, self.check.settings_url)
        return True
