"""The worker of the mode ``internal``: a thread that handles webhooks and updates, then ends.

In the modes ``external-...`` of ``FETCH_WORKER`` it starts no thread: ``manage.py
fetch_worker``, a process of its own, does the work.

It runs in the process of the site only while jobs wait, so the site keeps no idle process or
thread for it. A job that a stopped process left behind is taken again (``UpdateQueue.claim``)
when the next job starts the worker, or when the page of its project is opened.
"""

import logging
import threading

from django.db import close_old_connections, connections

from pycal_dashboard import worker_mode
from pycal_dashboard.import_guard import IMPORT_GUARD

log = logging.getLogger(__name__)


class UpdateWorker:
    """Runs ``UpdateQueue.work`` in a thread of the process."""

    # False in the tests, which run the queue themselves or start the worker with the fixture
    # update_worker, which stops it at the end
    enabled = True
    _thread: threading.Thread | None = None
    _lock = threading.Lock()
    _stopping = threading.Event()

    @classmethod
    def start(cls) -> bool:
        """Start the thread unless it runs.

        Returns:
            True if a thread was started.
        """
        if not cls.enabled or worker_mode.external():
            return False  # the tests run it themselves; a process of its own does it
        with cls._lock:
            if cls._thread is not None and cls._thread.is_alive():
                return False
            cls._thread = threading.Thread(target=cls.main, name="update-worker", daemon=True)
            cls._thread.start()
            return True

    @classmethod
    def stopping(cls) -> bool:
        """Whether the worker should stop after the repository it reads, see :meth:`stop`."""
        return cls._stopping.is_set()

    @classmethod
    def stop(cls, timeout: float = 30) -> None:
        """Stop the thread after the repository it reads, and start no other one.

        A job that it leaves unfinished is taken again later (``UpdateQueue.claim``).

        Parameters:
            timeout: The seconds to wait for the thread.
        """
        cls.enabled = False
        cls._stopping.set()
        try:
            if cls._thread is not None:
                cls._thread.join(timeout)
        finally:
            cls._thread = None
            cls._stopping.clear()

    @staticmethod
    def main() -> None:
        """Run the queue until it is empty, with connections of its own to the database."""
        with IMPORT_GUARD:  # see import_guard.py; the queues import this module
            from .update_queue import UpdateQueue
            from .webhook_queue import WebhookQueue

        close_old_connections()
        try:
            while WebhookQueue.work() + UpdateQueue.work():  # webhooks may queue updates
                pass
        except Exception:  # the thread must not die silently: the log says why
            log.exception("The update of projects failed")
        finally:
            connections.close_all()
