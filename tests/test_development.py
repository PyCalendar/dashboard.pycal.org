"""The settings for development and behind a tunnel."""

from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_the_development_example_names_only_known_settings():
    import re

    example = (ROOT / ".env.development.example").read_text()
    names = set(re.findall(r"^#? ?([A-Z][A-Z_]+)=", example, re.MULTILINE))
    assert names <= set(
        re.findall(r"^#? ?([A-Z][A-Z_]+)=", (ROOT / ".env.example").read_text(), re.MULTILINE)
    )
    assert {"SITE_URL", "SITE_NAME", "GITHUB_OAUTH_CLIENT_ID", "SITE_ADMINS"} <= names


def test_forms_are_accepted_from_the_address_of_the_site(settings):
    from django.conf import settings as django_settings

    assert django_settings.CSRF_TRUSTED_ORIGINS  # the default is SITE_URL


def test_a_form_through_a_tunnel(settings, db):
    from django.test import Client

    settings.CSRF_TRUSTED_ORIGINS = ["https://laptop.tail1234.ts.net"]
    client = Client(enforce_csrf_checks=True)
    client.get("/", HTTP_HOST="laptop.tail1234.ts.net")
    token = client.cookies.get("csrftoken")
    response = client.post(
        "/theme/",
        {"theme": "dark", "csrfmiddlewaretoken": token.value if token else ""},
        HTTP_HOST="laptop.tail1234.ts.net",
        HTTP_ORIGIN="https://laptop.tail1234.ts.net",
    )
    assert response.status_code == 302
