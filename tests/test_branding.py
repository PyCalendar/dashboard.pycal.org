"""The icon, the links of the footer and the time until people are signed out."""

import re

import pytest
from django.core.management import call_command

from pycal_dashboard import build_info
from pycal_dashboard.checks import check_favicon
from pycal_dashboard.errors import InvalidFooterLink
from pycal_dashboard.footer_links import parse_footer_links
from tests.conftest import person


def test_footer_links(client, db, settings):
    settings.FOOTER_LINKS = parse_footer_links(
        "pycal.org=https://pycal.org,Blog=https://b.example/"
    )
    content = client.get("/").content.decode()
    assert '<a href="https://pycal.org">pycal.org</a>' in content
    assert '<a href="https://b.example/">Blog</a>' in content


def test_the_footer_repeats_nothing_of_the_page_about(client, db, settings):
    """The page About has the documentation, the code and the version; the footer links it."""
    settings.FOOTER_LINKS = []
    about = client.get("/about/").content.decode()
    footer = about.split('<footer class="footer">')[1]
    main = about.split("<main")[1].split("</main>")[0]
    links = re.findall(r'href="([^"]+)"', footer)
    assert links == ["/about/"]
    for shown in re.findall(r'href="([^"]+)"', main):
        assert shown not in links
    version = build_info.get(settings.SOURCE_URL)["version"]
    assert version in main and version not in footer


@pytest.mark.parametrize("value", ["no-address", "=https://a.example", "A=ftp://a.example"])
def test_invalid_footer_link(value):
    with pytest.raises(InvalidFooterLink):
        parse_footer_links(value)


def test_favicon_of_pycal(client, db):
    response = client.get("/favicon.ico")
    assert response.status_code == 200 and response["Content-Type"] == "image/png"
    assert '<link rel="icon" href="/favicon.ico">' in client.get("/").content.decode()


def test_favicon_address(client, db, settings):
    settings.FAVICON = "https://pycal.org/favicon.png"
    response = client.get("/favicon.ico")
    assert response.status_code == 302 and response["Location"] == settings.FAVICON
    assert f'<link rel="icon" href="{settings.FAVICON}">' in client.get("/").content.decode()


def test_favicon_file(client, db, settings, tmp_path):
    icon = tmp_path / "icon.svg"
    icon.write_text("<svg xmlns='http://www.w3.org/2000/svg'/>")
    settings.FAVICON = str(icon)
    response = client.get("/favicon.ico")
    assert response["Content-Type"] == "image/svg+xml"
    assert check_favicon() == []


@pytest.mark.parametrize(
    ("name", "error"),
    [("missing.png", "pycal_dashboard.E001"), ("icon.gif", "pycal_dashboard.E002")],
)
def test_wrong_favicon_stops_the_site(settings, tmp_path, name, error):
    (tmp_path / "icon.gif").write_bytes(b"GIF89a")
    settings.FAVICON = str(tmp_path / name)
    assert [found.id for found in check_favicon()] == [error]


def test_signed_out_after_an_hour(client, alice):
    from django.conf import settings

    assert settings.SIGN_OUT_MINUTES == 60 and settings.SESSION_COOKIE_AGE == 3600
    client.force_login(alice)
    assert client.session.get_expiry_age() == 3600


def test_unknown_site_admins_are_named_at_the_start(db, settings, capsys):
    settings.SITE_ADMINS = ["admin", "typo"]
    person(7, "admin")
    call_command("prepare")
    assert (
        "SITE_ADMINS without an account on this site (a typo, or they never signed in): typo"
        in (capsys.readouterr().out)
    )
