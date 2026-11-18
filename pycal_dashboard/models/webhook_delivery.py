"""A webhook that GitHub delivered, and what the site did with it."""

from django.db import models


class WebhookDelivery(models.Model):
    """The log of the webhooks, for the administrators of the site."""

    delivery = models.CharField(max_length=100, blank=True, default="")
    event = models.CharField(max_length=100)
    action = models.CharField(max_length=100, blank=True, default="")
    repository = models.CharField(max_length=200, blank=True, default="")
    received = models.DateTimeField(auto_now_add=True)
    outcome = models.CharField(max_length=20)  # done, refused or failed
    error = models.CharField(max_length=100, blank=True, default="")
    detail = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-received"]
        verbose_name_plural = "webhook deliveries"

    def __str__(self) -> str:
        return f"{self.event}.{self.action} {self.outcome}"
