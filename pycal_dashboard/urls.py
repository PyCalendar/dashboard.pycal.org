"""The addresses of the pages."""

from allauth.account import views as account_views
from django.contrib import admin
from django.urls import include, path, register_converter

from .project_slug_converter import ProjectSlugConverter
from .views import account, oauth_app, pages, projects, registration, setup, webhook

register_converter(ProjectSlugConverter, "project_slug")

urlpatterns = [
    path("", pages.home, name="home"),
    path("about/", pages.about, name="about"),
    path("about/privacy/", pages.privacy, name="privacy"),
    path("licenses/", pages.licenses_page, name="licenses"),
    path("licenses/packages/<str:name>/", pages.package_license, name="package_license"),
    path("licenses/<str:name>/", pages.license_text, name="license_text"),
    path("health/", pages.health, name="health"),
    path("theme/", pages.theme, name="theme"),
    path("language/", pages.language, name="set_language"),
    path("favicon.ico", pages.favicon, name="favicon"),
    path("projects/", projects.projects, name="projects"),
    path("projects/new/", projects.project_new, name="project_new"),
    path("projects/<project_slug:slug>/", projects.project, name="project"),
    path("projects/<project_slug:slug>/update/", projects.project_update, name="project_update"),
    path(
        "projects/<project_slug:slug>/pull-requests/",
        projects.project_pull_requests,
        name="project_pull_requests",
    ),
    path("projects/<project_slug:slug>/settings/", projects.project_edit, name="project_edit"),
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
    path("logs/", account.logs, name="logs"),
    path("setup/github-app/", registration.register_app, name="register_app"),
    path("setup/github-app/registered/", registration.app_registered, name="app_registered"),
    path("setup/installed/", setup.installed, name="installed"),
    path("setup/oauth-app/", oauth_app.oauth_app, name="oauth_app"),
    path("github/webhook/", webhook.webhook, name="webhook"),
    # the email addresses: allauth leaves them out with SOCIALACCOUNT_ONLY
    path("accounts/email/", account_views.email, name="account_email"),
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
