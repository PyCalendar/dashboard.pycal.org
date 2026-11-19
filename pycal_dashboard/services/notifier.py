"""Notify people on the site, and resolve the notifications when the thing is done."""

from __future__ import annotations

from collections.abc import Iterable

from django.db import transaction
from django.utils import timezone

from pycal_dashboard.models import Notification


class Notifier:
    """The notifications of one thing, such as the permissions of an installation.

    Parameters of a notification that change, such as other missing permissions, make it
    unread again; the same ones leave it as it is, so a person who read it is not asked again.
    """

    def __init__(self, kind: str, key: str):
        """The notifications of a thing.

        Parameters:
            kind: Such as ``Notification.PERMISSIONS``.
            key: The thing, such as the id of an installation.
        """
        self.kind = kind
        self.key = str(key)

    @transaction.atomic
    def notify(self, user_ids: Iterable[int], params: dict, url: str = "") -> int:
        """Tell people about the thing, once for each change of it.

        Parameters:
            user_ids: The people.
            params: What the text says, such as the account and the missing permissions.
            url: Where to act.

        Returns:
            How many notifications are new or unread again.
        """
        changed = 0
        for user_id in set(user_ids):
            found = Notification.objects.filter(user_id=user_id, kind=self.kind, key=self.key)
            notification = found.first()
            if notification is None:
                Notification.objects.create(
                    user_id=user_id, kind=self.kind, key=self.key, params=params, url=url
                )
                changed += 1
            elif notification.params != params or notification.resolved is not None:
                found.update(
                    params=params, url=url, read=None, resolved=None, updated=timezone.now()
                )
                changed += 1
        return changed

    def resolve(self) -> int:
        """The thing is done: its notifications no longer ask for anything.

        Returns:
            How many were resolved.
        """
        return Notification.objects.filter(
            kind=self.kind, key=self.key, resolved__isnull=True
        ).update(resolved=timezone.now(), updated=timezone.now())
