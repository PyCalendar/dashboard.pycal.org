"""The background work in a process of its own, for the modes ``external-...`` of FETCH_WORKER."""

from __future__ import annotations

import logging
import time
from typing import Any

from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandParser
from django.db import close_old_connections

from pycal_dashboard import worker_mode
from pycal_dashboard.services.app_notice import AppNotice
from pycal_dashboard.services.update_queue import UpdateQueue
from pycal_dashboard.services.webhook_queue import WebhookQueue

log = logging.getLogger(__name__)
POLL = 2.0  # seconds between looks at the queues while nothing waits
HOURLY = 3600.0  # seconds between the renewals of what no webhook tells of
APP_CHECK = "app-check-requested"  # the key in the cache that asks for a check of the app


class Command(BaseCommand):
    """``manage.py fetch_worker``: webhooks, updates and what follows them, until stopped.

    The container starts it again when it stops, such as out of memory, so that the pages of
    gunicorn never do this work and never wait for it.
    """

    help = "Handle the webhooks and the updates from GitHub in the background (FETCH_WORKER)."

    def add_arguments(self, parser: CommandParser):
        """``--once`` stops when nothing waits.

        Parameters:
            parser: The parser of the arguments.
        """
        parser.add_argument("--once", action="store_true", help="stop when nothing waits")

    def handle(self, *args: Any, **options: Any):
        """Handle what waits; every hour renew what no webhook tells of.

        Parameters:
            *args: Not used.
            **options: ``once``.
        """
        self.stdout.write(f"fetch worker: {worker_mode.mode()}")
        try:  # a new version may need more permissions; a site without an app has none
            call_command("check_installations", stdout=self.stdout)
        except Exception as error:  # noqa: BLE001 - the worker runs on without the check
            self.stdout.write(f"no check of the installations: {error}")
        renewed = 0.0
        while True:
            close_old_connections()
            done = WebhookQueue.work() + UpdateQueue.work()
            if cache.get(APP_CHECK):  # Check again on the page Notifications
                cache.delete(APP_CHECK)
                AppNotice.refresh()
            if time.monotonic() - renewed >= HOURLY and not options["once"]:
                AppNotice.refresh()  # GitHub tells no change of the permissions of the app
                queued = UpdateQueue.stale(start=False)
                renewed = time.monotonic()
                self.stdout.write(f"{queued} repositories may be out of date")
                continue
            if done:
                continue
            if options["once"]:
                break
            time.sleep(POLL)
        self.stdout.write("fetch worker: nothing waits")
