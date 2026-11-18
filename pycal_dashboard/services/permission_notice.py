"""Tell the people of an installation by email when it lacks permissions that the site needs."""

import logging
from itertools import groupby

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import translation

from pycal_dashboard.actions import EmailSent
from pycal_dashboard.github.permissions import describe
from pycal_dashboard.models import Installation

from .email_addresses import recipients

log = logging.getLogger(__name__)


class PermissionNotice:
    """Compare the permissions of an installation with what the site needs; tell once."""

    def __init__(self, installation: Installation):
        """The notice for an installation.

        Args:
            installation: The installation, with the permissions that GitHub last told.
        """
        self.installation = installation

    def send_if_needed(self) -> int:
        """Email the people of the installation if it lacks permissions nobody was told about.

        Each set of missing permissions is told once; when the owners accepted them, the next
        set is told again. Each person gets the email in their language.

        Returns:
            How many emails were sent.
        """
        installation = self.installation
        missing = installation.missing_permissions
        described = describe(missing)
        if not missing or installation.removed:
            if installation.permissions_notified:
                installation.permissions_notified = ""
                installation.save(update_fields=["permissions_notified", "updated"])
            return 0
        if installation.permissions_notified == described:
            return 0
        people = recipients(installation.admin_github_ids, "email_permissions")
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
