"""The trigger of the actions that are running: a webhook, a person, or the site."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from pycal_dashboard.models import LogTrigger

_current: ContextVar[LogTrigger | None] = ContextVar("log_trigger", default=None)


class Trigger:
    """Start triggers and find the one that the running actions belong to."""

    @staticmethod
    @contextmanager
    def start(kind: str, summary: str, **scope: Any) -> Iterator[LogTrigger]:
        """Record a trigger; the actions inside the ``with`` block belong to it.

        Parameters:
            kind: Such as ``webhook``, ``sign-in`` or ``setup``.
            summary: What happened, for people, such as ``@alice signed in``.
            **scope: ``actor_login``, ``repository`` and ``delivery`` of
                :class:`~pycal_dashboard.models.LogTrigger`.

        Yields:
            The trigger; its summary and scope can still be changed and saved.
        """
        trigger = LogTrigger.objects.create(kind=kind, summary=summary[:300], **scope)
        token = _current.set(trigger)
        try:
            yield trigger
        finally:
            _current.reset(token)

    @staticmethod
    def current() -> LogTrigger:
        """The trigger of the running actions.

        Returns:
            The trigger of the ``with`` block of :meth:`start`; outside of one, a new trigger
            ``background``, so that no action is lost.
        """
        found = _current.get()
        if found is None:
            found = LogTrigger.objects.create(kind="background", summary="Work of the site")
        return found
