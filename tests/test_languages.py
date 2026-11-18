"""The site in English, German and Spanish: the browser chooses, the menu keeps the choice."""

import re
from pathlib import Path

import pytest

LOCALE = Path(__file__).parents[1] / "pycal_dashboard" / "locale"

pytestmark = pytest.mark.django_db


def test_english_by_default(client):
    page = client.get("/").content.decode()
    assert '<html lang="en"' in page and "Welcome to the community of PyCalendar" in page


@pytest.mark.parametrize(
    ("language", "text"),
    [
        ("de", "Willkommen in der Gemeinschaft von PyCalendar"),
        ("es", "Bienvenido a la comunidad de PyCalendar"),
    ],
)
def test_the_browser_chooses_the_language(client, language, text):
    page = client.get("/", HTTP_ACCEPT_LANGUAGE=f"{language},en;q=0.5").content.decode()
    assert f'<html lang="{language}"' in page and text in page


def test_the_menu_keeps_the_choice(client):
    response = client.post("/language/", {"language": "es", "next": "/about/"})
    assert response.status_code == 302 and response["Location"] == "/about/"
    assert "Acerca de" in client.get("/about/").content.decode()
    page = client.get("/").content.decode()
    assert (
        '<button name="language" value="es" lang="es" aria-pressed="true">Español</button>' in page
    )


def test_errors_are_translated(client):
    page = client.get("/setup/installed/", HTTP_ACCEPT_LANGUAGE="de").content.decode()
    assert "Ungültige Installation" in page
    assert "Was dieser Fehler bedeutet und wie man ihn löst" in page
    assert (
        "Seite nicht gefunden"
        in client.get("/nowhere/", HTTP_ACCEPT_LANGUAGE="de").content.decode()
    )


def test_times_are_translated(client, admin):
    from pycal_dashboard.models import WebhookDelivery

    WebhookDelivery.objects.create(event="ping", outcome="done")
    client.force_login(admin)
    page = client.get("/account/deliveries/", HTTP_ACCEPT_LANGUAGE="es").content.decode()
    assert "justo ahora" in page


def test_the_json_and_the_details_of_errors_stay_english(client):
    assert client.get("/about.json", HTTP_ACCEPT_LANGUAGE="de").json()["build"]
    page = client.get("/setup/installed/", HTTP_ACCEPT_LANGUAGE="de").content.decode()
    assert "Error: InvalidInstallationId (HTTP 400)" in page


@pytest.mark.parametrize("language", ["de", "es"])
def test_every_text_is_translated_and_compiled(language):
    po = (LOCALE / language / "LC_MESSAGES" / "django.po").read_text()
    entries = po.split("\n\n")[1:]  # without the header
    assert entries and not any("#, fuzzy" in entry for entry in entries)
    empty = [
        entry for entry in entries if re.search(r'msgstr(\[\d\])? ""\n?$', entry.strip() + "\n")
    ]
    assert empty == []
    mo = LOCALE / language / "LC_MESSAGES" / "django.mo"
    assert (
        mo.stat().st_mtime >= (LOCALE / language / "LC_MESSAGES" / "django.po").stat().st_mtime - 5
    )


def test_every_template_text_is_marked():
    """Text between tags of the templates is translated, except names and code."""
    templates = Path(__file__).parents[1] / "pycal_dashboard" / "templates"
    for template in templates.rglob("*.html"):
        text = template.read_text()
        text = re.sub(r"{% blocktranslate.*?{% endblocktranslate %}", "", text, flags=re.S)
        text = re.sub(
            r"{%.*?%}|{{.*?}}|<code>.*?</code>|<textarea.*?</textarea>|<svg.*?</svg>",
            "",
            text,
            flags=re.S,
        )
        words = [w for w in re.findall(r">([^<>]*[A-Za-z]{3,}[^<>]*)<", text) if w.strip()]
        allowed = {"AGPL-3.0-or-later", "PyCalendar"}
        assert [w for w in words if w.strip() not in allowed] == [], template
