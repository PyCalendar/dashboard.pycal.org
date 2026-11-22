"""The addresses of the pages."""

from allauth.account import views as account_views
from django.contrib import admin
from django.urls import include, path, register_converter

from .project_slug_converter import ProjectSlugConverter
from .views import (
    account,
    account_email,
    contributors,
    filters,
    message,
    oauth_app,
    pages,
    projects,
    pull_request,
    registration,
    setup,
    site_settings,
    steps,
    webhook,
)

register_converter(ProjectSlugConverter, "project_slug")

urlpatterns = [
    path("", pages.home, name="home"),
    path("about/", pages.about, name="about"),
    path("about/privacy/", pages.privacy, name="privacy"),
    path("about/version/", pages.about_version, name="about_version"),
    path("about/github-app/", pages.about_github_app, name="about_github_app"),
    path("licenses/", pages.licenses_page, name="licenses"),
    path("licenses/packages/<str:name>/", pages.package_license, name="package_license"),
    path("licenses/<str:name>/", pages.license_text, name="license_text"),
    path("health/", pages.health, name="health"),
    path("theme/", pages.theme, name="theme"),
    path("language/", pages.language, name="set_language"),
    path("favicon.ico", pages.favicon, name="favicon"),
    path("robots.txt", pages.robots_txt, name="robots_txt"),
    path("llms.txt", pages.llms_txt, name="llms_txt"),
    path("markdown/preview/", pages.markdown_preview, name="markdown_preview"),
    path("projects/", projects.projects, name="projects"),
    path("projects/new/", projects.project_new, name="project_new"),
    path("projects/<project_slug:slug>/", projects.project, name="project"),
    path("projects/<project_slug:slug>/update/", projects.project_update, name="project_update"),
    path(
        "projects/<project_slug:slug>/pull-requests/",
        projects.project_pull_requests,
        name="project_pull_requests",
    ),
    path(
        "projects/<project_slug:slug>/contributors/<str:login>/",
        contributors.project_contributor,
        name="project_contributor",
    ),
    path(
        "projects/<project_slug:slug>/pull/<int:number>/",
        pull_request.project_pull_request,
        name="project_pull_request",
    ),
    path(
        "projects/<project_slug:slug>/pull/<int:number>/skip/",
        pull_request.project_pull_request_skip,
        name="project_pull_request_skip",
    ),
    path(
        "projects/<project_slug:slug>/pull/<int:number>/badge.svg",
        pull_request.project_pull_request_badge,
        {"kind": "svg"},
        name="project_pull_request_badge",
    ),
    path(
        "projects/<project_slug:slug>/pull/<int:number>/badge.png",
        pull_request.project_pull_request_badge,
        {"kind": "png"},
        name="project_pull_request_badge_png",
    ),
    path("projects/<project_slug:slug>/filters/", filters.project_filters, name="project_filters"),
    path("projects/<project_slug:slug>/steps/", steps.project_steps, name="project_steps"),
    path("projects/<project_slug:slug>/message/", message.project_message, name="project_message"),
    path(
        "projects/<project_slug:slug>/sync/labels/",
        message.project_sync_labels,
        name="project_sync_labels",
    ),
    path(
        "projects/<project_slug:slug>/message/edit/",
        message.project_message_edit,
        name="project_message_edit",
    ),
    path(
        "projects/<project_slug:slug>/message/review/",
        message.project_message_review,
        name="project_message_review",
    ),
    path(
        "projects/<project_slug:slug>/message/scope/",
        message.project_message_scope,
        name="project_message_scope",
    ),
    path(
        "projects/<project_slug:slug>/message/preview/",
        message.project_message_preview,
        name="project_message_preview",
    ),
    path(
        "projects/<project_slug:slug>/steps/add/", steps.project_step_add, name="project_step_add"
    ),
    path(
        "projects/<project_slug:slug>/steps/check/",
        steps.project_steps_check,
        name="project_steps_check",
    ),
    path(
        "projects/<project_slug:slug>/steps/<int:number>/move/",
        steps.project_step_move,
        name="project_step_move",
    ),
    path(
        "projects/<project_slug:slug>/steps/<int:number>/edit/",
        steps.project_step_edit,
        name="project_step_edit",
    ),
    path(
        "projects/<project_slug:slug>/steps/<int:number>/preview/",
        steps.project_step_preview,
        name="project_step_preview",
    ),
    path(
        "projects/<project_slug:slug>/steps/<int:number>/remove/",
        steps.project_step_remove,
        name="project_step_remove",
    ),
    path(
        "projects/<project_slug:slug>/filters/<int:number>/",
        filters.project_filter_counts,
        name="project_filter_counts",
    ),
    path(
        "projects/<project_slug:slug>/filters/save/",
        filters.project_filter_save,
        name="project_filter_save",
    ),
    path("projects/<project_slug:slug>/settings/", projects.project_edit, name="project_edit"),
    path(
        "projects/<project_slug:slug>/settings/backup/",
        projects.project_backup,
        name="project_backup",
    ),
    path(
        "projects/<project_slug:slug>/settings/restore/",
        projects.project_restore,
        name="project_restore",
    ),
    path("projects/<project_slug:slug>/address/", projects.project_slug, name="project_slug"),
    path(
        "projects/<project_slug:slug>/repositories/",
        projects.project_repositories,
        name="project_repositories",
    ),
    path(
        "projects/<project_slug:slug>/collaborators/",
        projects.project_collaborators,
        name="project_collaborators",
    ),
    # the addresses before: the tab People, and the name of the project after the slug
    path("projects/<project_slug:slug>/people/", projects.project_moved, {"page": "people"}),
    path("projects/<project_slug:slug>/<str:name>/", projects.project_moved),
    path("projects/<project_slug:slug>/<str:name>/<str:page>/", projects.project_moved),
    path("repositories/complete/", projects.repository_complete, name="repository_complete"),
    path("people/complete/", projects.people_complete, name="people_complete"),
    path("account/", account.account, name="account"),
    path("account/deliveries/", account.deliveries, name="deliveries"),
    path("account/delete/", account.account_delete, name="account_delete"),
    path("account/notifications/", account.notifications, name="notifications"),
    path("logs/", account.logs, name="logs"),
    path("setup/settings/", site_settings.site_settings, name="site_settings"),
    path("setup/github-app/", registration.register_app, name="register_app"),
    path("setup/github-app/registered/", registration.app_registered, name="app_registered"),
    path("setup/installed/", setup.installed, name="installed"),
    path("setup/oauth-app/", oauth_app.oauth_app, name="oauth_app"),
    path("github/webhook/", webhook.webhook, name="webhook"),
    # the email addresses: allauth leaves them out with SOCIALACCOUNT_ONLY
    path("accounts/email/", account_email.AccountEmailView.as_view(), name="account_email"),
    path(
        "accounts/confirm-email/",
        account_views.email_verification_sent,
        name="account_email_verification_sent",
    ),
    path(
        "accounts/confirm-email/<str:key>/",
        account_views.confirm_email,
        name="account_confirm_email",
    ),
    path("accounts/", include("allauth.urls")),
    path("admin/", admin.site.urls),
]

handler400 = "pycal_dashboard.views.errors.bad_request"
handler403 = "pycal_dashboard.views.errors.permission_denied"
handler404 = "pycal_dashboard.views.errors.page_not_found"
handler500 = "pycal_dashboard.views.errors.server_error"
