"""The worker that updates projects in the background: a thread that ends when nothing waits.

It runs in the process of the site only while jobs wait, so the site keeps no idle process or
thread for it. A job that a stopped process left behind is taken again (``UpdateQueue.claim``)
when the next job starts the worker, or when the page of its project is opened.
"""

import logging
import threading

from django.db import close_old_connections, connections

from pycal_dashboard.import_guard import IMPORT_GUARD

log = logging.getLogger(__name__)


class UpdateWorker:
    """Runs ``UpdateQueue.work`` in a thread of the process."""

    # False in the tests of the code, which run the queue themselves; the browser tests start it
    enabled = True
    _thread: threading.Thread | None = None
    _lock = threading.Lock()

    @classmethod
    def start(cls) -> bool:
        """Start the thread unless it runs.

        Returns:
            True if a thread was started.
        """
        if not cls.enabled:
            return False
        with cls._lock:
            if cls._thread is not None and cls._thread.is_alive():
                return False
            cls._thread = threading.Thread(target=cls.main, name="update-worker", daemon=True)
            cls._thread.start()
            return True

    @staticmethod
    def main() -> None:
        """Run the queue until it is empty, with connections of its own to the database."""
        with IMPORT_GUARD:  # see import_guard.py; the queue imports this module
            from .update_queue import UpdateQueue

        close_old_connections()
        try:
            UpdateQueue.work()
        except Exception:  # the thread must not die silently: the log says why
            log.exception("The update of projects failed")
        finally:
            connections.close_all()
