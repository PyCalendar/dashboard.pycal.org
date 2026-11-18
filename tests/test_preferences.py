"""The language and the colors: chosen in the account, else by the browser and the menus."""

import pytest

from pycal_dashboard.models import LogAction, Preferences

pytestmark = pytest.mark.django_db


def lang(page) -> str:
    return page.content.decode().split('<html lang="')[1].split('"')[0]


def theme(page) -> str:
    return page.content.decode().split('data-theme="')[1].split('"')[0]


def test_without_a_choice_the_browser_decides(client, alice):
    client.force_login(alice)
    assert lang(client.get("/", HTTP_ACCEPT_LANGUAGE="es")) == "es"
    assert theme(client.get("/")) == "auto"


def test_the_account_chooses_the_language_on_every_device(client, alice):
    client.force_login(alice)
    response = client.post("/account/", {"language": "de", "theme": "dark"})
    assert response.status_code == 302
    assert Preferences.objects.get(user=alice).language == "de"
    page = client.get("/account/", HTTP_ACCEPT_LANGUAGE="es")  # the browser says Spanish
    assert lang(page) == "de" and theme(page) == "dark"
    assert "Deine Einstellungen sind gespeichert." in page.content.decode()
    assert '<option value="de" lang="de" selected>Deutsch</option>' in page.content.decode()
    action = LogAction.objects.get(kind="preferences")
    assert action.text == "@alice saved the preferences: language de, colors dark, no emails"


def test_the_account_overrides_the_cookie_of_the_menus(client, alice):
    client.cookies["theme"] = "light"
    client.cookies["django_language"] = "es"
    client.force_login(alice)
    client.post("/account/", {"language": "de", "theme": "dark"})
    page = client.get("/")
    assert lang(page) == "de" and theme(page) == "dark"


def test_the_menus_change_the_account(client, alice):
    client.force_login(alice)
    client.post("/account/", {"language": "de", "theme": "dark"})
    client.post("/language/", {"language": "es", "next": "/"})
    client.post("/theme/", {"theme": "light", "next": "/"})
    preferences = Preferences.objects.get(user=alice)
    assert (preferences.language, preferences.theme) == ("es", "light")
    page = client.get("/")
    assert lang(page) == "es" and theme(page) == "light"


def test_back_to_the_browser(client, alice):
    client.force_login(alice)
    client.post("/account/", {"language": "de", "theme": "dark"})
    client.post("/account/", {"language": "", "theme": ""})
    assert lang(client.get("/", HTTP_ACCEPT_LANGUAGE="es")) == "es"


def test_visitors_choose_with_the_menus_only(client, db):
    client.post("/language/", {"language": "de", "next": "/"})
    client.post("/theme/", {"theme": "dark", "next": "/"})
    page = client.get("/")
    assert lang(page) == "de" and theme(page) == "dark"
    assert not Preferences.objects.exists()


@pytest.mark.parametrize(("field", "value"), [("language", "fr"), ("theme", "pink")])
def test_unknown_preferences(client, alice, field, value):
    client.force_login(alice)
    response = client.post("/account/", {field: value})
    assert response.status_code == 400 and b'data-error="UnknownPreference"' in response.content
    assert not Preferences.objects.exists()
