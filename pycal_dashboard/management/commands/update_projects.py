"""Run the updates that wait, in a process of their own, until none waits."""

from django.core.management.base import BaseCommand

from pycal_dashboard.services.update_queue import UpdateQueue


class Command(BaseCommand):
    """``manage.py update_projects``: at the start of the container and every hour after it."""

    help = "Run the updates that wait, such as after a migration, then end."

    def add_arguments(self, parser):
        """``--stale`` also updates the repositories not read in the last day.

        Args:
            parser: The parser of the arguments.
        """
        parser.add_argument(
            "--stale",
            action="store_true",
            help="also update the repositories of projects that were not read in the last day",
        )

    def handle(self, *args, **options):
        """Update what waits, and with ``--stale`` what may be out of date.

        ``manage.py prepare`` queues the projects with older data after a migration that
        changes what the site keeps of GitHub (``DATA_VERSION``). ``--stale`` renews every day
        what no webhook tells of. The process ends when no update waits, so that it uses no
        memory while the site is idle.

        Args:
            *args: Not used.
            **options: ``stale``.
        """
        if options["stale"]:
            queued = UpdateQueue.stale(start=False)
            self.stdout.write(f"{queued} repositories may be out of date")
        count = UpdateQueue.work()
        self.stdout.write(f"{count} updates done")
