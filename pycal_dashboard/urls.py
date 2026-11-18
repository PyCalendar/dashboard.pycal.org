"""The addresses of the pages."""

from allauth.account import views as account_views
from django.contrib import admin
from django.urls import include, path

from .views import account, api, dashboard, pages, registration, setup, webhook

urlpatterns = [
    path("", pages.home, name="home"),
    path("about/", pages.about, name="about"),
    path("health/", pages.health, name="health"),
    path("theme/", pages.theme, name="theme"),
    path("repositories/", dashboard.repositories, name="repositories"),
    path("repositories/<str:owner>/<str:repo>/", dashboard.repository, name="repository"),
    path("contribute/", dashboard.contribute, name="contribute"),
    path("reviews/", dashboard.reviews, name="reviews"),
    path("contributors/", dashboard.contributors, name="contributors"),
    path("contributors/<str:login>/", dashboard.contributor, name="contributor"),
    path("account/", account.account, name="account"),
    path("account/deliveries/", account.deliveries, name="deliveries"),
    path("setup/github-app/", registration.register_app, name="register_app"),
    path("setup/github-app/registered/", registration.app_registered, name="app_registered"),
    path("setup/installed/", setup.installed, name="installed"),
    path("github/webhook/", webhook.webhook, name="webhook"),
    path("api/v1/", api.index, name="api"),
    path("api/v1/overview/", api.overview, name="api_overview"),
    path("api/v1/repositories/", api.repositories, name="api_repositories"),
    path("api/v1/repositories/<str:owner>/<str:repo>/", api.repository, name="api_repository"),
    path("api/v1/starter-issues/", api.starter_issues, name="api_starter_issues"),
    path("api/v1/reviews/", api.reviews, name="api_reviews"),
    path("api/v1/contributors/", api.contributors, name="api_contributors"),
    path("api/v1/contributors/<str:login>/", api.contributor, name="api_contributor"),
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
