"""The Django admin: every table, for the administrators of the site (``SITE_ADMINS``)."""

from django.contrib import admin

from .models import Installation, LogAction, LogTrigger, Preferences, WebhookDelivery

admin.site.register(
    WebhookDelivery, list_display=["event", "action", "repository", "outcome", "received"]
)
admin.site.register(
    Installation,
    list_display=["account_login", "github_id", "account_type", "permissions_notified", "updated"],
)
admin.site.register(Preferences, list_display=["user", "language", "theme"])
admin.site.register(LogTrigger, list_display=["summary", "kind", "actor_login", "created"])
admin.site.register(LogAction, list_display=["text", "kind", "created"])
