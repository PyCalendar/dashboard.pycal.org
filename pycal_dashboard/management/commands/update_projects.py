"""Run the updates of projects that wait, in a process of their own, until none waits."""

from django.core.management.base import BaseCommand

from pycal_dashboard.services.update_queue import UpdateQueue


class Command(BaseCommand):
    """``manage.py update_projects``: at every start of the container, in the background."""

    help = "Run the updates of projects that wait, such as after a migration, then end."

    def handle(self, *args, **options):
        """Update the projects that wait, such as those with older data of GitHub.

        ``manage.py prepare`` queues them after a migration that changes what the site keeps of
        GitHub (``DATA_VERSION``). The process ends when no update waits, so that it uses no
        memory while the site is idle.

        Args:
            *args: Not used.
            **options: Of Django.
        """
        count = UpdateQueue.work()
        self.stdout.write(f"{count} project updates done")
