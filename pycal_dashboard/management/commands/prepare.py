"""Prepare the site at every start: the database, the domain and the GitHub App."""

from urllib.parse import urlparse

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management import call_command
from django.core.management.base import BaseCommand

from pycal_dashboard.services.app_registration import AppRegistration


class Command(BaseCommand):
    """``manage.py prepare``: migrate, set the domain and ask for the GitHub App."""

    help = "Migrate the database, set the domain and print the setup code of the GitHub App."

    def handle(self, *args, **options):
        """Prepare the site.

        Without a GitHub App, the log says where to register it and the setup code that
        allows it: the site needs the app for its data, its webhooks and signing in.

        Args:
            *args: Not used.
            **options: Of Django.
        """
        call_command("migrate", interactive=False, verbosity=0)
        domain = urlparse(settings.SITE_URL).netloc or "localhost"
        Site.objects.update_or_create(
            pk=settings.SITE_ID, defaults={"domain": domain, "name": settings.SITE_NAME}
        )
        self.stdout.write(f"prepared {domain}")
        if AppRegistration.source():
            self.stdout.write(f"GitHub App {settings.GITHUB_APP_SLUG or settings.GITHUB_APP_ID}")
            return
        obstacle = AppRegistration.obstacle()
        if obstacle:
            self.stdout.write(
                f"This site has no GitHub App and cannot register one: {obstacle.title}: "
                f"{obstacle.detail} ({obstacle.docs_url()})"
            )
            return
        code = (
            AppRegistration.setup_code()
            if AppRegistration.needs_setup_code()
            else "(none needed with DEBUG)"
        )
        self.stdout.write(
            "This site has no GitHub App yet. Register it on "
            f"{settings.SITE_URL}/setup/github-app/ with the setup code {code}"
        )
