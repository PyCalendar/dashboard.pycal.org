"""Tell the people of an installation by email when it lacks permissions that the site needs."""

import logging
from itertools import groupby

from allauth.socialaccount.models import SocialAccount
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import translation

from pycal_dashboard.actions import EmailSent
from pycal_dashboard.github import permissions
from pycal_dashboard.github.permissions import describe
from pycal_dashboard.models import Installation, Notification, ProjectMember

from .email_addresses import recipients
from .notifier import Notifier

log = logging.getLogger(__name__)


class PermissionNotice:
    """Compare the permissions of an installation with what the site needs; tell once."""

    def __init__(self, installation: Installation, app_permissions: dict | None = None):
        """The notice for an installation.

        Parameters:
            installation: The installation, with the permissions that GitHub last told.
            app_permissions: The permissions of the GitHub App itself, when the site read
                them; None when not known. GitHub asks an installation to accept only the
                permissions that the app has, so only those are told: the owners of the app
                add the others first (``AppNotice``).
        """
        self.installation = installation
        self.app_permissions = app_permissions

    def missing(self) -> dict[str, str]:
        """The permissions that the installation lacks and its owners can accept now.

        Returns:
            Those that it lacks, without those that the app itself does not have yet.
        """
        missing = self.installation.missing_permissions
        if self.app_permissions is None:
            return missing
        granted = permissions.missing(self.app_permissions, missing)
        return {name: level for name, level in missing.items() if name not in granted}

    def github_ids(self) -> list[int]:
        """The people who are told about the installation.

        They are those who installed or changed it, and the writers and owners of the projects
        with a repository it is installed on.

        Returns:
            Their GitHub ids.
        """
        found = {int(i) for i in self.installation.admin_github_ids}
        members = ProjectMember.objects.filter(
            project__repositories__installation=self.installation,
            role__in=[ProjectMember.WRITE, ProjectMember.OWNER],
        ).values_list("user__profile__github_id", flat=True)
        found |= {int(i) for i in members if i}
        return sorted(found)

    def user_ids(self) -> list[int]:
        """The people of the site who are told about the installation, see :meth:`github_ids`.

        Returns:
            The ids of their users.
        """
        ids = [str(i) for i in self.github_ids()]
        return list(
            SocialAccount.objects.filter(provider="github", uid__in=ids).values_list(
                "user_id", flat=True
            )
        )

    def notify(self, missing: dict[str, str]) -> None:
        """Notify the people on the site while the installation lacks permissions, else resolve.

        Everybody who is told gets the notification, also those who switched the emails off.

        Parameters:
            missing: The permissions it lacks, by name.
        """
        installation = self.installation
        notifier = Notifier(Notification.PERMISSIONS, installation.github_id)
        if not missing or installation.removed:
            notifier.resolve()
            return
        params = {"account": installation.account_login, "missing": dict(sorted(missing.items()))}
        notifier.notify(self.user_ids(), params, installation.settings_url)

    def send_if_needed(self) -> int:
        """Email the people of the installation if it lacks permissions nobody was told about.

        Each set of missing permissions is told once; when the owners accepted them, the next
        set is told again. Each person gets the email in their language.

        Returns:
            How many emails were sent.
        """
        installation = self.installation
        missing = self.missing()
        described = describe(missing)
        self.notify(missing)
        if not missing or installation.removed:
            if installation.permissions_notified:
                installation.permissions_notified = ""
                installation.save(update_fields=["permissions_notified", "updated"])
            return 0
        if installation.permissions_notified == described:
            return 0
        people = recipients(self.github_ids(), "email_permissions")
        if not people:
            log.warning("%s lacks %s and nobody gets an email", installation, described)
            return 0
        sent = 0
        for language, group in groupby(people, key=lambda person: person[1]):
            addresses = [address for address, _language in group]
            with translation.override(language or settings.LANGUAGE_CODE):
                context = {
                    "installation": installation,
                    "missing": sorted(missing.items()),
                    "site_name": settings.SITE_NAME,
                    "site_url": settings.SITE_URL,
                    "docs_url": settings.DOCS_URL.rstrip("/") + "/",
                }
                subject = render_to_string("pycal_dashboard/email/permissions_subject.txt", context)
                body = render_to_string("pycal_dashboard/email/permissions_message.txt", context)
            EmailSent(subject.strip(), body, addresses).run()
            sent += 1
        installation.permissions_notified = described
        installation.save(update_fields=["permissions_notified", "updated"])
        return sent
