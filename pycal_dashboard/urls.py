"""The addresses of the pages."""

from allauth.account import views as account_views
from django.contrib import admin
from django.urls import include, path

from .views import account, api, oauth_app, pages, registration, setup, webhook

urlpatterns = [
    path("", pages.home, name="home"),
    path("about/", pages.about, name="about"),
    path("health/", pages.health, name="health"),
    path("theme/", pages.theme, name="theme"),
    path("favicon.ico", pages.favicon, name="favicon"),
    path("account/", account.account, name="account"),
    path("account/deliveries/", account.deliveries, name="deliveries"),
    path("setup/github-app/", registration.register_app, name="register_app"),
    path("setup/github-app/registered/", registration.app_registered, name="app_registered"),
    path("setup/installed/", setup.installed, name="installed"),
    path("setup/oauth-app/", oauth_app.oauth_app, name="oauth_app"),
    path("github/webhook/", webhook.webhook, name="webhook"),
    path("api/v1/", api.index, name="api"),
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
