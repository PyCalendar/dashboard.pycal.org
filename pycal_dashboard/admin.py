"""The Django admin: every table, for the administrators of the site (``SITE_ADMINS``)."""

from django.contrib import admin

from .models import (
    GitHubUser,
    Installation,
    Issue,
    Label,
    LogAction,
    LogTrigger,
    Notification,
    Preferences,
    Profile,
    Project,
    ProjectMember,
    ProjectSlug,
    PullRequestFilter,
    PullRequestState,
    PullRequestStep,
    Repository,
    UpdateJob,
    WebhookDelivery,
)

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
admin.site.register(Profile, list_display=["user", "github_name", "github_id"])
admin.site.register(Project, list_display=["name", "slug", "public", "created_by", "updated"])
admin.site.register(ProjectMember, list_display=["project", "user", "role", "added"])
admin.site.register(
    Repository,
    list_display=["full_name", "private", "open_issues", "open_pull_requests", "updated"],
)
admin.site.register(
    UpdateJob, list_display=["project", "status", "done", "total", "errors", "created"]
)
admin.site.register(ProjectSlug, list_display=["slug", "project", "since", "until"])
admin.site.register(GitHubUser, list_display=["login", "github_id", "type", "user"])
admin.site.register(
    Issue,
    list_display=["repository", "number", "pull_request", "title", "author", "state", "created"],
    list_filter=["pull_request", "state"],
    search_fields=["title", "repository__full_name", "author__login"],
)
admin.site.register(Label, list_display=["name", "repository", "color", "description"])
admin.site.register(
    PullRequestState,
    list_display=["issue", "mergeable_state", "auto_merge", "checks", "updated"],
)
admin.site.register(PullRequestFilter, list_display=["name", "project", "created_by", "updated"])
admin.site.register(
    Notification, list_display=["user", "kind", "key", "created", "read", "resolved"]
)
admin.site.register(PullRequestStep, list_display=["name", "project", "filter", "position"])
