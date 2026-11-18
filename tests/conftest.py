"""Fixtures: a fake GitHub, a GitHub App with a key, people and repositories."""

import json

import pytest
from allauth.socialaccount.models import SocialAccount
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.contrib.auth import get_user_model

from pycal_dashboard.github import client as github_client
from pycal_dashboard.github.app import GitHubApp
from pycal_dashboard.github.webhook_signature import sign
from pycal_dashboard.services.repository_sync import RepositorySync
from pycal_dashboard.sign_in import SignIn
from tests.fakes.github import FakeGitHub

WEBHOOK_SECRET = "webhook-secret"
REPOSITORY = "PyCalendar/icalendar"
OTHER = "PyCalendar/plann"


@pytest.fixture(scope="session")
def private_key() -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ).decode()


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
    settings.SIGN_IN = SignIn("client", "secret", "github-app")
    settings.SOCIALACCOUNT_PROVIDERS = settings.SIGN_IN.providers()
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.DOCS_URL = "https://docs.example.org/"
    return settings


@pytest.fixture(autouse=True)
def github(monkeypatch) -> FakeGitHub:
    """The fake GitHub that answers all requests of the site."""
    fake = FakeGitHub()
    monkeypatch.setattr(github_client, "TRANSPORT", fake.transport())
    GitHubApp.forget_tokens()
    yield fake
    GitHubApp.forget_tokens()


@pytest.fixture
def organization(github, db) -> FakeGitHub:
    """PyCalendar on GitHub, with the app installed, issues and pull requests."""
    github.install(1, "PyCalendar", [REPOSITORY, OTHER, "PyCalendar/secret"])
    github.repositories["PyCalendar/secret"]["private"] = True
    github.issue(REPOSITORY, 1, "alice", labels=["good first issue"])
    github.issue(REPOSITORY, 2, "bob", comments=3)
    github.pull(REPOSITORY, 3, "carol", author_association="FIRST_TIME_CONTRIBUTOR")
    github.pull(
        REPOSITORY, 4, "alice", additions=600, deletions=10, requested_reviewers=[{"login": "bob"}]
    )
    github.pull(
        REPOSITORY,
        5,
        "bob",
        state="closed",
        pull_request={"merged_at": "2026-11-17T10:00:00Z"},
        merged_at="2026-11-17T10:00:00Z",
        closed_at="2026-11-17T10:00:00Z",
    )
    github.pull(OTHER, 1, "dependabot[bot]", user={"login": "dependabot[bot]", "type": "Bot"})
    github.issue("PyCalendar/secret", 1, "mallory", title="A private issue")
    return github


@pytest.fixture
def synced(organization, db) -> FakeGitHub:
    """The organization, read by the site."""
    RepositorySync(1).run()
    return organization


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


def pull_payload(
    github: FakeGitHub, number: int, action="opened", repo=REPOSITORY, account="PyCalendar"
):
    pull = github.find(repo, number)
    return {
        "action": action,
        "pull_request": {k: v for k, v in pull.items() if k != "pull_request"},
        "repository": github.repositories[repo],
        "installation": {"id": 1, "account": {"login": account}},
    }
