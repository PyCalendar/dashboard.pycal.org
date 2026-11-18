"""Read every installation of the GitHub App again: repositories, issues, pull requests."""

from django.core.management.base import BaseCommand, CommandError

from pycal_dashboard.errors import DashboardError
from pycal_dashboard.github.app import GitHubApp
from pycal_dashboard.services.repository_sync import RepositorySync


class Command(BaseCommand):
    """``manage.py sync_repositories``: also labels the open pull requests."""

    help = "Read the repositories, issues and pull requests of the installations from GitHub."

    def handle(self, *args, **options):
        """Read everything and print a summary per installation.

        Args:
            *args: Not used.
            **options: Of Django.

        Raises:
            CommandError: The site has no GitHub App, or GitHub failed.
        """
        if not GitHubApp.configured():
            self.stdout.write("No GitHub App yet: nothing to read.")
            return
        try:
            summaries = RepositorySync.everything()
        except DashboardError as error:
            raise CommandError(f"{error.title}: {error} ({error.docs_url()})") from error
        for summary in summaries:
            self.stdout.write(
                f"{summary['repositories']} repositories, {summary['items']} issues and pull "
                f"requests, {summary['labeled']} labeled"
            )
            for problem in summary["errors"]:
                self.stderr.write(problem)
