"""A webhook that GitHub delivered, and what the site did with it."""

from django.db import models


class WebhookDelivery(models.Model):
    """The log of the webhooks, for the administrators of the site."""

    delivery = models.CharField(max_length=100, blank=True, default="")
    event = models.CharField(max_length=100)
    action = models.CharField(max_length=100, blank=True, default="")
    repository = models.CharField(max_length=200, blank=True, default="")
    received = models.DateTimeField(auto_now_add=True)
    # queued (recorded, for the background), handling, done, refused or failed
    outcome = models.CharField(max_length=20)
    error = models.CharField(max_length=100, blank=True, default="")
    detail = models.TextField(blank=True, default="")
    # the body of a queued webhook until the background handled it; then empty
    payload = models.TextField(blank=True, default="")
    handled = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-received"]
        verbose_name_plural = "webhook deliveries"

    def __str__(self) -> str:
        return f"{self.event}.{self.action} {self.outcome}"
