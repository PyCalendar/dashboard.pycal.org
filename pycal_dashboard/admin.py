"""The Django admin: every table, to browse the database."""

from django.contrib import admin

from .models import Installation, Item, Profile, Repository, WebhookDelivery

admin.site.register(Installation, list_display=["account_login", "github_id", "suspended"])
admin.site.register(
    Repository,
    list_display=["full_name", "private", "archived", "synced_at"],
    search_fields=["full_name"],
)
admin.site.register(
    Item,
    list_display=["__str__", "title", "is_pull", "state", "author_login"],
    list_filter=["is_pull", "state"],
    search_fields=["title", "author_login"],
)
admin.site.register(Profile, list_display=["user", "email_digest"])
admin.site.register(
    WebhookDelivery, list_display=["event", "action", "repository", "outcome", "received"]
)
