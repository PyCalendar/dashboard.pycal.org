"""Settings, configured with environment variables; docs/reference/settings.rst lists them."""

# The type hints of django-environ allow no defaults; the values are checked by Django.
# pyright: reportArgumentType=false, reportReturnType=false

import os
import sys
from pathlib import Path

import environ

from pycal_dashboard import registered_settings
from pycal_dashboard.footer_links import DEFAULT as DEFAULT_FOOTER_LINKS
from pycal_dashboard.footer_links import parse_footer_links
from pycal_dashboard.import_guard import IMPORT_GUARD
from pycal_dashboard.organizations import parse_organizations
from pycal_dashboard.sign_in import SignIn
from pycal_dashboard.theme import Theme

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env()
DATA_DIR = Path(env("DATA_DIR", default=str(BASE_DIR / "data")))
TESTING = "pytest" in sys.modules
# The credentials of the GitHub App registered on the site (/setup/github-app/); the variables
# of the environment take precedence. The tests use their own settings.
if not TESTING:
    registered_settings.load(DATA_DIR / ".env", os.environ)


def kept_secret(name: str) -> str:
    """A secret from the environment, or generated once into the data directory.

    Args:
        name: The name of the setting and of its file, such as ``SECRET_KEY``.

    Returns:
        The secret.
    """
    if env(name, default=""):
        return env(name)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / name.lower()
    if not path.exists():
        with IMPORT_GUARD:  # see import_guard.py
            from django.core.management.utils import get_random_secret_key

        registered_settings.write_private(path, get_random_secret_key())
    return path.read_text().strip()


DEBUG = env.bool("DEBUG", default=False)
SECRET_KEY = kept_secret("SECRET_KEY")

SITE_NAME = env("SITE_NAME", default="dashboard.pycal.org")
# the address of the site: the GitHub App, its webhooks and the links of the labels use it
SITE_URL = env("SITE_URL", default="https://dashboard.pycal.org").rstrip("/")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])
# forms are accepted from the address of the site, also behind a tunnel without X-Forwarded-Proto
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[SITE_URL])
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_FAILURE_VIEW = "pycal_dashboard.views.errors.csrf_failure"
X_FRAME_OPTIONS = "DENY"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    # before allauth: its templates in templates/ replace those of allauth
    "pycal_dashboard",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.github",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # the language: the cookie of the language menu, else the browser (Accept-Language)
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    # the rights of the Django admin follow SITE_ADMINS, also for sessions of before a change
    "pycal_dashboard.admin_rights.AdminRightsMiddleware",
    # the language that a person chose in the account, on every device
    "pycal_dashboard.preferences_middleware.PreferencesMiddleware",
    # <page>.json: the public information of a page, readable by other sites
    "pycal_dashboard.public_json.PublicJsonMiddleware",
    "pycal_dashboard.middleware.ErrorPageMiddleware",
]

ROOT_URLCONF = "pycal_dashboard.urls"
WSGI_APPLICATION = "pycal_dashboard.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "pycal_dashboard.context.site",
            ],
        },
    },
]

DATABASES = {"default": env.db("DATABASE_URL", default=f"sqlite:///{DATA_DIR / 'db.sqlite3'}")}
DATABASES["default"]["CONN_MAX_AGE"] = 60
if DATABASES["default"]["ENGINE"].endswith("sqlite3"):
    DATABASES["default"].setdefault("OPTIONS", {}).update(
        {
            "timeout": 30,
            "transaction_mode": "IMMEDIATE",
            "init_command": "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;",
        }
    )
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Sign in with GitHub only: no passwords, no email sign up.
AUTHENTICATION_BACKENDS = ["allauth.account.auth_backends.AuthenticationBackend"]
SITE_ID = 1
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/account/"
LOGOUT_REDIRECT_URL = "/"
SOCIALACCOUNT_ONLY = True
# People sign in with GitHub only, so allauth must not ask them to confirm an address first.
# The emails of the site go only to addresses that GitHub or a link confirmed.
ACCOUNT_EMAIL_VERIFICATION = "none"
# the emails of allauth, such as the link that verifies an address, name the site
ACCOUNT_EMAIL_SUBJECT_PREFIX = f"[{SITE_NAME}] "
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https" if SITE_URL.startswith("https://") else "http"
ACCOUNT_LOGIN_METHODS = {"username"}
ACCOUNT_SIGNUP_FIELDS = ["username*"]
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_LOGIN_ON_GET = False  # a button with POST: no sign in by a link of another site
SOCIALACCOUNT_STORE_TOKENS = False  # the site only reads who signed in
SOCIALACCOUNT_QUERY_EMAIL = True  # the verified addresses of GitHub
# People sign in with a separate OAuth app (GITHUB_OAUTH_CLIENT_ID, pycal_dashboard/sign_in.py),
# entered on /setup/oauth-app/ or set here; without it nobody can sign in.
SIGN_IN = SignIn.from_environment(dict(os.environ))
SOCIALACCOUNT_PROVIDERS = SIGN_IN.providers()
# GitHub handles that administer this site: the Django admin and the webhook deliveries
SITE_ADMINS = [login.lower() for login in env.list("SITE_ADMINS", default=[])]
# minutes after signing in when people are signed out again, also while they use the site
SIGN_OUT_MINUTES = env.float("SIGN_OUT_MINUTES", default=60)
SESSION_COOKIE_AGE = max(60, round(SIGN_OUT_MINUTES * 60))

# The GitHub App: docs/how-to/github-app.rst
GITHUB_API = env("GITHUB_API", default="https://api.github.com").rstrip("/")
GITHUB_APP_ID = env("GITHUB_APP_ID", default="")
GITHUB_APP_SLUG = env("GITHUB_APP_SLUG", default="")
GITHUB_APP_PRIVATE_KEY = env("GITHUB_APP_PRIVATE_KEY", default="").replace("\\n", "\n")
_key_file = env("GITHUB_APP_PRIVATE_KEY_FILE", default="")
if _key_file and not GITHUB_APP_PRIVATE_KEY and Path(_key_file).is_file():
    GITHUB_APP_PRIVATE_KEY = Path(_key_file).read_text()
GITHUB_WEBHOOK_SECRET = env("GITHUB_WEBHOOK_SECRET", default="")
# the organizations of the community of the site: the links of the start page, the account that
# owns the GitHub App in the form of its registration; every account may install the app
GITHUB_ORGANIZATIONS = parse_organizations(env("GITHUB_ORGANIZATIONS", default="PyCalendar"))

# Branding: the colors of sign.pycal.org, changed with COLOR_... (docs/reference/settings.rst)
THEME = Theme.from_environment(dict(os.environ))
SOURCE_URL = env("SOURCE_URL", default="https://github.com/PyCalendar/dashboard.pycal.org")
DOCS_URL = env("DOCS_URL", default="https://docs.dashboard.pycal.org/")
# the icon: an address (https://...) or the path of a PNG, ICO or SVG file; empty: pycal's
FAVICON = env("FAVICON", default="")
# the extra links of the footer: Title=URL, comma separated; empty: none
FOOTER_LINKS = parse_footer_links(env("FOOTER_LINKS", default=DEFAULT_FOOTER_LINKS))

EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_BACKEND = (
    "django.core.mail.backends.smtp.EmailBackend"
    if EMAIL_HOST
    else "django.core.mail.backends.console.EmailBackend"
)
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=EMAIL_PORT == 465)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=not EMAIL_USE_SSL)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default=f"dashboard@{SITE_NAME}")

LANGUAGE_CODE = "en"
TIME_ZONE = "UTC"
USE_I18N = True
# English, German and Spanish; the first one comes from the browser, the menu keeps the choice
LANGUAGES = [("en", "English"), ("de", "Deutsch"), ("es", "Español")]
LOCALE_PATHS = [BASE_DIR / "pycal_dashboard" / "locale"]
LANGUAGE_COOKIE_AGE = 365 * 24 * 3600
LANGUAGE_COOKIE_SAMESITE = "Lax"
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        if TESTING or DEBUG
        else "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
    "loggers": {"httpx": {"level": "WARNING"}},
}
