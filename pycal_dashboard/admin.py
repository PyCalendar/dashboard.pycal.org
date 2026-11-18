"""The Django admin: every table, for the administrators of the site (``SITE_ADMINS``)."""

from django.contrib import admin

from .models import Profile, WebhookDelivery

admin.site.register(Profile, list_display=["user", "email_notifications"])
admin.site.register(
    WebhookDelivery, list_display=["event", "action", "repository", "outcome", "received"]
)
