"""Errors of the webhooks that GitHub sends to the site.

GitHub shows them in the list of recent deliveries of the GitHub App, with the
status of the answer. The site keeps them on the page *Webhook deliveries* for
its administrators.
"""

from django.utils.translation import gettext_lazy as _

from .base import DashboardError


class WebhookError(DashboardError):
    """A webhook of GitHub could not be handled.

    Resolve:
        Look up the answer of the dashboard in the recent deliveries in the advanced settings of
        the GitHub App, and check the setup with :doc:`/how-to/github-app`.
    """

    title = _("The webhook could not be handled")
    guide = "how-to/github-app.html"
    guide_title = _("Register the GitHub App")


class WebhookSecretNotConfigured(WebhookError):
    """The dashboard has no secret to check the webhooks with.

    Resolve:
        Set ``GITHUB_WEBHOOK_SECRET`` to the webhook secret of the GitHub App, see
        :doc:`/reference/settings`.

    Context:
        Without ``GITHUB_WEBHOOK_SECRET`` anybody could send webhooks to the dashboard, so they
        are refused.
    """

    title = _("The site has no webhook secret")
    status = 503


class WebhookSignatureMissing(WebhookError):
    """The webhook has no signature.

    This happens when:

    - the GitHub App has no webhook secret, or
    - the request does not come from GitHub.

    Resolve:
        - When the GitHub App has no webhook secret, set one in the settings of the GitHub App,
          the same as ``GITHUB_WEBHOOK_SECRET`` of the dashboard.
        - When the request does not come from GitHub, nothing needs to be done: the dashboard
          refused it.

    Context:
        GitHub signs every webhook with the secret of the app in the header
        ``X-Hub-Signature-256``.
    """

    title = _("The webhook has no signature")
    status = 401


class WebhookSignatureInvalid(WebhookError):
    """The signature of the webhook does not match the secret.

    This happens when:

    - the webhook secret of the GitHub App and ``GITHUB_WEBHOOK_SECRET`` of the dashboard
      differ, or
    - the request does not come from GitHub.

    Resolve:
        - When the secrets differ, set both to the same value.
        - When the request does not come from GitHub, nothing needs to be done: the dashboard
          refused it.
    """

    title = _("The signature of the webhook is invalid")
    status = 401


class WebhookPayloadInvalid(WebhookError):
    """The content of the webhook is not the JSON object GitHub sends.

    Resolve:
        Set the content type of the webhook in the settings of the GitHub App to
        ``application/json``.

    Note:
        The detail is the error of reading the JSON, or the kind of value that it holds
        instead of an object, such as ``list``.
    """

    title = _("The content of the webhook is invalid")


class WebhookEventMissing(WebhookError):
    """The webhook does not say which event it is, so it does not come from GitHub.

    Resolve:
        - When someone else sent the request, nothing needs to be done: the dashboard refused it.
        - When you sent it yourself, such as to test the dashboard, add the header
          ``X-GitHub-Event`` with the name of the event.

    Context:
        GitHub names the event in the header ``X-GitHub-Event``.
    """

    title = _("The webhook names no event")
