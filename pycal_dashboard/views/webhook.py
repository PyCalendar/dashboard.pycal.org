"""The webhook of the GitHub App."""

from __future__ import annotations

import json
import logging

from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from pycal_dashboard import worker_mode
from pycal_dashboard.errors import WebhookError, WebhookEventMissing, WebhookPayloadInvalid
from pycal_dashboard.github.webhook_signature import verify
from pycal_dashboard.models import WebhookDelivery
from pycal_dashboard.services.update_worker import UpdateWorker
from pycal_dashboard.services.webhook_handler import WebhookHandler
from pycal_dashboard.services.webhook_queue import WebhookQueue

log = logging.getLogger(__name__)


def read(request: HttpRequest) -> tuple[str, dict]:
    """Check the signature and read the webhook.

    Parameters:
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
def webhook(request: HttpRequest):
    """Receive a webhook of GitHub, check its signature, and record it for the background.

    The background handles it (``WebhookQueue``), so that GitHub gets its answer at once,
    also during many deliveries; in the mode ``inline`` of ``FETCH_WORKER`` the request does.

    Parameters:
        request: The request of GitHub.

    Returns:
        JSON: queued (202), what was done, or the error with its link to the documentation.
    """
    delivery = WebhookDelivery(delivery=request.headers.get("X-GitHub-Delivery", "")[:100])
    delivery.event = request.headers.get("X-GitHub-Event", "")[:100]
    try:
        event, payload = read(request)
    except WebhookError as error:
        delivery.outcome, delivery.error, delivery.detail = "refused", error.code, str(error)
        delivery.save()
        return JsonResponse(error.as_json(), status=error.status)
    if worker_mode.mode() != worker_mode.INLINE:
        handler = WebhookHandler(event, payload)
        delivery.action = handler.action[:100]
        delivery.repository = handler.repository_name[:200]
        WebhookQueue.record(delivery, request.body)
        UpdateWorker.start()  # the thread of the mode internal; the others leave it to the worker
        return JsonResponse({"queued": delivery.pk}, status=202)
    done, error = WebhookQueue.handle(delivery, event, payload)
    if error is not None:
        # 200: GitHub would not deliver it again anyway; the deliveries of GitHub show why
        return JsonResponse(error.as_json(), status=200 if error.status < 500 else error.status)
    return JsonResponse({"done": done})
