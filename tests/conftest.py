"""Fixtures: a fake GitHub, a GitHub App with a key, people and webhooks."""

import json

import pytest
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model

from pycal_dashboard.github import client as github_client
from pycal_dashboard.github.webhook_signature import sign
from pycal_dashboard.sign_in import SignIn
from tests.fakes.github import FakeGitHub

WEBHOOK_SECRET = "webhook-secret"
REPOSITORY = "PyCalendar/icalendar"
OTHER = "PyCalendar/plann"


@pytest.fixture(scope="session")
def private_key() -> str:
    """A private key as GitHub sends it: the app signs its token with it."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ).decode()


@pytest.fixture(autouse=True)
def english():
    """Every test starts in English: a request in another language may leave it active."""
    from django.utils import translation

    translation.activate("en")
    yield
    translation.activate("en")


@pytest.fixture(autouse=True)
def app_settings(settings, private_key, tmp_path):
    settings.DATA_DIR = tmp_path / "data"
    settings.GITHUB_APP_ID = "1"
    settings.GITHUB_APP_SLUG = "dashboard-test"
    settings.GITHUB_APP_PRIVATE_KEY = private_key
    settings.GITHUB_WEBHOOK_SECRET = WEBHOOK_SECRET
    settings.GITHUB_ORGANIZATIONS = ["pycalendar"]
    settings.SITE_URL = "https://dashboard.example.org"
    settings.SITE_ADMINS = ["admin"]
    settings.SIGN_IN = SignIn("oauth-client", "oauth-secret")
    settings.SOCIALACCOUNT_PROVIDERS = settings.SIGN_IN.providers()
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.DOCS_URL = "https://docs.example.org/"
    return settings


@pytest.fixture(autouse=True)
def github(monkeypatch) -> FakeGitHub:
    """The fake GitHub that answers all requests of the site."""
    fake = FakeGitHub()
    monkeypatch.setattr(github_client, "TRANSPORT", fake.transport())
    return fake


def person(github_id: int, login: str, **user_fields):
    user = get_user_model().objects.create(username=login, **user_fields)
    SocialAccount.objects.create(
        user=user, provider="github", uid=str(github_id), extra_data={"login": login}
    )
    return user


@pytest.fixture
def alice(db):
    return person(42, "alice")


@pytest.fixture
def bob(db):
    return person(43, "bob")


@pytest.fixture
def admin(db):
    return person(7, "admin")


def send_webhook(
    client, event: str, payload: dict, secret: str | None = WEBHOOK_SECRET, delivery="d-1"
):
    body = json.dumps(payload).encode()
    headers = {"HTTP_X_GITHUB_DELIVERY": delivery}
    if event:
        headers["HTTP_X_GITHUB_EVENT"] = event
    if secret is not None:
        headers["HTTP_X_HUB_SIGNATURE_256"] = sign(secret, body)
    return client.post("/github/webhook/", body, content_type="application/json", **headers)


def repository_payload(full_name: str = REPOSITORY, private: bool = False) -> dict:
    owner, name = full_name.split("/")
    return {
        "id": 1000,
        "full_name": full_name,
        "name": name,
        "owner": {"login": owner, "type": "Organization"},
        "private": private,
    }


def pull_payload(number: int = 6, action="opened", repo=REPOSITORY, account="PyCalendar"):
    return {
        "action": action,
        "number": number,
        "pull_request": {
            "number": number,
            "title": f"Pull request {number}",
            "state": "open",
            "user": {"login": "dave", "type": "User"},
            "author_association": "FIRST_TIME_CONTRIBUTOR",
            "labels": [],
            "additions": 30,
            "deletions": 2,
        },
        "repository": repository_payload(repo),
        "installation": {"id": 1, "account": {"login": account}},
    }
