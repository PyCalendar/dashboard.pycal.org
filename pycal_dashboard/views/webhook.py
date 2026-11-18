"""The webhook of the GitHub App."""

import json
import logging

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from pycal_dashboard.actions import Trigger, WebhookTrigger
from pycal_dashboard.errors import (
    DashboardError,
    WebhookError,
    WebhookEventMissing,
    WebhookPayloadInvalid,
    translate,
)
from pycal_dashboard.github.webhook_signature import verify
from pycal_dashboard.models import WebhookDelivery
from pycal_dashboard.services.webhook_handler import WebhookHandler

log = logging.getLogger(__name__)


def read(request) -> tuple[str, dict]:
    """Check the signature and read the webhook.

    Args:
        request: The request of GitHub.

    Returns:
        The event and the payload.

    Raises:
        WebhookError: The webhook is not from GitHub or not readable.
    """
    verify(settings.GITHUB_WEBHOOK_SECRET, request.body, request.headers.get("X-Hub-Signature-256"))
    event = request.headers.get("X-GitHub-Event", "")
    if not event:
        raise WebhookEventMissing("X-GitHub-Event")
    try:
        payload = json.loads(request.body)
    except ValueError as error:
        raise WebhookPayloadInvalid(str(error)) from error
    if not isinstance(payload, dict):
        raise WebhookPayloadInvalid(type(payload).__name__)
    return event, payload


@csrf_exempt  # GitHub signs the webhooks instead
@require_POST
def webhook(request):
    """Receive a webhook of GitHub, check its signature and handle it.

    Args:
        request: The request of GitHub.

    Returns:
        JSON with what was done, or the error with its link to the documentation.
    """
    delivery = WebhookDelivery(delivery=request.headers.get("X-GitHub-Delivery", "")[:100])
    delivery.event = request.headers.get("X-GitHub-Event", "")[:100]
    try:
        event, payload = read(request)
    except WebhookError as error:
        delivery.outcome, delivery.error, delivery.detail = "refused", error.code, str(error)
        delivery.save()
        return JsonResponse(error.as_json(), status=error.status)
    handler = WebhookHandler(event, payload)
    delivery.action = handler.action[:100]
    delivery.repository = handler.repository_name[:200]
    with Trigger.start("webhook", f"Webhook {event}", delivery=delivery.delivery) as trigger:
        try:
            done = handler.handle()
        except Exception as exception:  # noqa: BLE001 - every failure is logged with the delivery
            error: DashboardError = translate(exception)
            if error.code == "UnexpectedError":
                log.exception("webhook %s", event)
            delivery.outcome, delivery.error, delivery.detail = "failed", error.code, str(error)
            delivery.save()
            WebhookTrigger.complete(trigger, event, payload, error.code)
            # 200: GitHub would not deliver it again anyway; the deliveries of GitHub show why
            return JsonResponse(error.as_json(), status=200 if error.status < 500 else error.status)
        WebhookTrigger.complete(trigger, event, payload, done)
    delivery.outcome = "done"
    delivery.detail = done
    delivery.save()
    return JsonResponse({"done": done})
