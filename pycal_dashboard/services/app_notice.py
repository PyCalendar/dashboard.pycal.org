"""Tell the administrators of the site when the GitHub App itself lacks permissions or events."""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

from allauth.socialaccount.models import SocialAccount
from django.conf import settings
from django.db import connections

from pycal_dashboard.import_guard import IMPORT_GUARD
from pycal_dashboard.models import Notification

from .notifier import Notifier

if TYPE_CHECKING:
    from pycal_dashboard.github.app_check import AppCheck

# the app is one: the key of its notification
KEY = "app"
log = logging.getLogger(__name__)


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

    @classmethod
    def refresh(cls) -> bool | None:
        """Read the app from GitHub again, and notify or resolve.

        GitHub sends no webhook when the owners change the permissions of the app.

        Returns:
            True if the app lacks something, False if not, None if GitHub could not be asked.
        """
        with IMPORT_GUARD:  # see import_guard.py: only the checks of the app read it
            from pycal_dashboard.github.app_check import AppCheck

        try:
            return cls(AppCheck.read()).notify()
        except Exception:  # such as without an app or while GitHub is down: the next time
            log.warning("The GitHub App could not be checked", exc_info=True)
            return None

    @classmethod
    def refresh_in_background(cls) -> threading.Thread:
        """Check the app in a thread, so that the page that asks for it does not wait.

        Returns:
            The thread.
        """

        def run() -> None:
            try:
                cls.refresh()
            finally:
                connections.close_all()

        thread = threading.Thread(target=run, name="app-check", daemon=True)
        thread.start()
        return thread
