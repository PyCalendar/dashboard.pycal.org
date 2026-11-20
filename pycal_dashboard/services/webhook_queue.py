"""The webhooks of GitHub: recorded by the web process, handled in the background."""

from __future__ import annotations

import json
import logging
from datetime import timedelta

from django.utils import timezone

from pycal_dashboard.actions import Trigger, WebhookTrigger
from pycal_dashboard.errors import DashboardError, translate
from pycal_dashboard.models import WebhookDelivery

from .webhook_handler import WebhookHandler

log = logging.getLogger(__name__)
# a delivery that is handled longer was stopped with its process: it is handled again
STUCK = timedelta(minutes=10)


class WebhookQueue:
    """Deliveries of webhooks that wait for the background, the oldest first.

    The web process checks the signature, records the delivery with its payload and answers at
    once (``queued``); the background (``manage.py fetch_worker``, or the thread of the
    updates) handles it with :meth:`handle` and empties its payload. In the mode ``inline`` the
    request handles it.
    """

    @staticmethod
    def handle(
        delivery: WebhookDelivery, event: str, payload: dict
    ) -> tuple[str, DashboardError | None]:
        """Do what a webhook asks for, and record the outcome in the delivery and the log.

        Parameters:
            delivery: The delivery, saved or not.
            event: The header ``X-GitHub-Event``.
            payload: The payload.

        Returns:
            What was done, and the error if it failed.
        """
        handler = WebhookHandler(event, payload)
        delivery.action = handler.action[:100]
        delivery.repository = handler.repository_name[:200]
        failure = None
        with Trigger.start("webhook", f"Webhook {event}", delivery=delivery.delivery) as trigger:
            try:
                done = handler.handle()
            except Exception as exception:  # noqa: BLE001 - every failure is logged with it
                failure = translate(exception)
                if failure.code == "UnexpectedError":
                    log.exception("webhook %s", event)
                delivery.outcome, delivery.error = "failed", failure.code
                delivery.detail = done = str(failure)
                WebhookTrigger.complete(trigger, event, payload, failure.code)
            else:
                WebhookTrigger.complete(trigger, event, payload, done)
                delivery.outcome, delivery.detail = "done", done
        delivery.payload = ""  # the data of GitHub is not kept longer than needed
        delivery.handled = timezone.now()
        delivery.save()
        return done, failure

    @staticmethod
    def record(delivery: WebhookDelivery, body: bytes) -> WebhookDelivery:
        """Record a checked webhook for the background.

        Parameters:
            delivery: The delivery with its id and event.
            body: The payload as GitHub sent it.

        Returns:
            The delivery, queued.
        """
        delivery.outcome = "queued"
        delivery.payload = body.decode("utf-8", errors="replace")
        delivery.save()
        return delivery

    @classmethod
    def claim(cls) -> WebhookDelivery | None:
        """Take the oldest queued delivery, or one whose handling was stopped.

        Returns:
            The delivery, marked as handled now; None when none waits.
        """
        stuck = timezone.now() - STUCK
        waiting = WebhookDelivery.objects.filter(outcome="queued") | WebhookDelivery.objects.filter(
            outcome="handling", handled__lt=stuck
        )
        for delivery in waiting.order_by("received", "pk")[:5]:
            taken = WebhookDelivery.objects.filter(pk=delivery.pk, outcome=delivery.outcome)
            if taken.update(outcome="handling", handled=timezone.now()):
                delivery.refresh_from_db()
                return delivery
        return None

    @classmethod
    def work(cls) -> int:
        """Handle the queued deliveries until none waits.

        Returns:
            How many were handled.
        """
        count = 0
        while (delivery := cls.claim()) is not None:
            try:
                payload = json.loads(delivery.payload or "{}")
            except ValueError:
                payload = {}
            cls.handle(delivery, delivery.event, payload if isinstance(payload, dict) else {})
            count += 1
        return count
