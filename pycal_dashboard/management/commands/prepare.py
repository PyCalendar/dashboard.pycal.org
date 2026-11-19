"""Prepare the site at every start: the database, the domain and the GitHub App."""

from urllib.parse import urlparse

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management import call_command
from django.core.management.base import BaseCommand

from pycal_dashboard.import_guard import IMPORT_GUARD
from pycal_dashboard.services.app_registration import AppRegistration
from pycal_dashboard.services.update_queue import UpdateQueue


class Command(BaseCommand):
    """``manage.py prepare``: migrate, set the domain and ask for the GitHub App."""

    help = "Migrate the database, set the domain and print the setup code of the GitHub App."

    def handle(self, *args, **options):
        """Prepare the site.

        Without a GitHub App, the log says where to register it and the setup code that
        allows it; the same for the OAuth app that signs people in.

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
        outdated = UpdateQueue.outdated()
        if outdated:
            self.stdout.write(
                f"{outdated} projects have older data of GitHub: manage.py update_projects "
                "updates them"
            )
        unknown = self.unknown_admins()
        if unknown:
            self.stdout.write(
                "SITE_ADMINS without an account on this site (a typo, or they never signed "
                f"in): {', '.join(unknown)}"
            )
        self.github_app()
        self.oauth_app()

    @staticmethod
    def unknown_admins() -> list[str]:
        """The handles of ``SITE_ADMINS`` that no account of the site has.

        Returns:
            The handles, such as a misspelled one; they get admin rights when they sign in.
        """
        with IMPORT_GUARD:  # see import_guard.py
            from allauth.socialaccount.models import SocialAccount

        known = {
            str(account.extra_data.get("login", "")).lower()
            for account in SocialAccount.objects.filter(provider="github")
        }
        return [login for login in settings.SITE_ADMINS if login not in known]

    def code(self) -> str:
        """The setup code that allows the setup, as the log shows it.

        Returns:
            The code, or a note that DEBUG needs none.
        """
        if AppRegistration.needs_setup_code():
            return AppRegistration.setup_code()
        return "(none needed with DEBUG)"

    def github_app(self) -> None:
        """Say which GitHub App the site has, or where to register it."""
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
        self.stdout.write(
            "This site has no GitHub App yet. Register it on "
            f"{settings.SITE_URL}/setup/github-app/ with the setup code {self.code()}"
        )

    def oauth_app(self) -> None:
        """Say whether people can sign in, or where to enter the OAuth app."""
        if settings.SIGN_IN.configured:
            self.stdout.write("People sign in with the OAuth app.")
            return
        self.stdout.write(
            "Nobody can sign in: this site has no OAuth app. Enter it on "
            f"{settings.SITE_URL}/setup/oauth-app/ with the setup code {self.code()}"
        )
