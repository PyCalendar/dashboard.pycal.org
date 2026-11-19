"""Say which permissions and events the GitHub App lacks."""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError

from pycal_dashboard.errors import DashboardError
from pycal_dashboard.github.app_check import AppCheck


class Command(BaseCommand):
    """``manage.py check_app``: compare the app on GitHub with what the site needs."""

    help = "Read the GitHub App from GitHub and name the permissions and events it lacks."

    def handle(self, *args: Any, **options: Any):
        """Check the app.

        Parameters:
            *args: Not used.
            **options: Of Django.

        Raises:
            CommandError: The app could not be read, or it lacks something.
        """
        try:
            check = AppCheck.read()
        except DashboardError as error:
            raise CommandError(f"{error.title}: {error} ({error.docs_url()})") from error
        if not check.complete:
            raise CommandError(check.describe())
        self.stdout.write(f"The GitHub App {check.app.get('slug', '')} has everything it needs.")
