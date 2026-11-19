"""Read the installations of the GitHub App and tell their people what permissions they lack."""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError

from pycal_dashboard.actions import Trigger
from pycal_dashboard.errors import DashboardError
from pycal_dashboard.github.app_check import AppCheck
from pycal_dashboard.github.client import GitHubClient
from pycal_dashboard.models import Installation
from pycal_dashboard.services.app_notice import AppNotice
from pycal_dashboard.services.installation_store import InstallationStore
from pycal_dashboard.services.permission_notice import PermissionNotice


class Command(BaseCommand):
    """``manage.py check_installations``: at every start of the container."""

    help = "Record the installations of the GitHub App and email those that lack permissions."

    def handle(self, *args: Any, **options: Any):
        """Read every installation from GitHub, record it and send the notices.

        A new version of the site that needs more permissions tells the people of every
        installation once, at its first start.

        Parameters:
            *args: Not used.
            **options: Of Django.

        Raises:
            CommandError: GitHub could not be asked, such as without a GitHub App.
        """
        try:
            AppNotice(AppCheck.read()).notify()  # the app first: its owner adds what it lacks
            client = GitHubClient(AppCheck.token())
            found = []
            for number in range(1, 51):
                answer = client.request(
                    "GET", "/app/installations", params={"per_page": 100, "page": number}
                ).json()
                found.extend(answer)
                if len(answer) < 100:
                    break
        except DashboardError as error:
            raise CommandError(f"{error.title}: {error} ({error.docs_url()})") from error
        sent = lacking = 0
        with Trigger.start("installations", f"Check of {len(found)} installations"):
            for data in found:
                installation = InstallationStore.record(data)
                lacking += bool(installation.missing_permissions)
                sent += PermissionNotice(installation).send_if_needed()
            seen = [data["id"] for data in found]
            Installation.objects.exclude(github_id__in=seen).update(removed=True)
        self.stdout.write(
            f"{len(found)} installations, {lacking} lack permissions, {sent} emails sent"
        )
