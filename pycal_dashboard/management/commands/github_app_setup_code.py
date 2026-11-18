"""Show the setup code that allows registering the GitHub App on the site."""

from django.core.management.base import BaseCommand

from pycal_dashboard.services.app_registration import AppRegistration


class Command(BaseCommand):
    """``manage.py github_app_setup_code``: the code for the page *Register the GitHub App*."""

    help = "Show the setup code for registering the GitHub App on the site."

    def handle(self, *args, **options):
        """Print the code, or why none is needed.

        Args:
            *args: Not used.
            **options: Of Django.
        """
        source = AppRegistration.source()
        if source:
            self.stdout.write(f"The site has a GitHub App (from the {source}); no code is needed.")
            return
        obstacle = AppRegistration.obstacle()
        if obstacle:
            self.stdout.write(
                f"The site cannot register its GitHub App: {obstacle.title}: {obstacle}"
            )
            return
        self.stdout.write(AppRegistration.setup_code())
