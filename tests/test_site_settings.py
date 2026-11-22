"""The page Settings of the administrators: the hosts whose images texts of Markdown show."""

import pytest

from pycal_dashboard.markdown_text import render
from pycal_dashboard.models import LogAction, SiteSettings
from pycal_dashboard.models.site_settings import DEFAULT_IMAGE_HOSTS

pytestmark = pytest.mark.django_db
BADGE = "![Replies](https://insight.pycal.org/badge/s/x/replies/a.svg)"


def test_only_the_administrators_see_the_settings(client, settings, admin, alice):
    settings.SITE_ADMINS = ["admin"]
    client.force_login(alice)
    assert client.get("/setup/settings/").status_code == 403
    assert "data-site-settings-link" not in client.get("/projects/").content.decode()
    assert client.post("/setup/settings/", {"image_hosts": "evil.example"}).status_code == 403
    assert SiteSettings.current().image_hosts == list(DEFAULT_IMAGE_HOSTS)
    client.force_login(admin)
    assert "data-site-settings-link" in client.get("/projects/").content.decode()
    assert client.get("/setup/settings/").status_code == 200


def test_the_default_hosts_show_their_images(client):
    assert SiteSettings.current().image_hosts == ["*.shields.io", "github.com", "*.pycal.org"]
    for address in [
        "https://insight.pycal.org/badge/s/x/replies/a.svg",
        "https://img.shields.io/badge/a-b-green.svg",
        "https://github.com/user-attachments/assets/a.png",
    ]:
        assert f'src="{address}"' in render(f"![x]({address})")
    for address in [
        "https://pycal.org.evil.example/a.svg",
        "https://evilpycal.org/a.svg",
        "https://gist.github.com.example/a.svg",
        "https://other.example/a.png",
    ]:
        assert "<img" not in render(f"![x]({address})")
    privacy = client.get("/about/privacy/").content.decode().split("data-image-hosts")[1]
    assert "<code>*.pycal.org</code>" in privacy


def test_an_empty_list_loads_no_images(client, settings, admin):
    settings.SITE_ADMINS = ["admin"]
    client.force_login(admin)
    client.post("/setup/settings/", {"image_hosts": ""})
    assert SiteSettings.current().image_hosts == []
    assert "<img" not in render(BADGE)


def test_a_host_below_a_star_shows_its_images(client, settings, admin):
    settings.SITE_ADMINS = ["admin"]
    client.force_login(admin)
    client.post("/setup/settings/", {"image_hosts": "*.example.org"})
    assert SiteSettings.current().image_hosts == ["*.example.org"]
    assert "<img" in render("![x](https://a.b.example.org/a.png)")
    assert "<img" not in render("![x](https://example.org/a.png)")
    assert "<img" not in render(BADGE)


def test_an_allowed_host_shows_its_images(client, settings, admin):
    settings.SITE_ADMINS = ["admin"]
    client.force_login(admin)
    client.post("/setup/settings/", {"image_hosts": ""})
    assert "<img" not in render(BADGE)  # none: its text
    answer = client.post(
        "/setup/settings/", {"image_hosts": "https://Insight.pycal.org/\n\ninsight.pycal.org"}
    )
    assert answer["Location"] == "/setup/settings/"
    assert SiteSettings.current().image_hosts == ["insight.pycal.org"]
    assert 'src="https://insight.pycal.org/badge/s/x/replies/a.svg"' in render(BADGE)
    assert "<img" not in render(BADGE.replace("https://", "http://"))  # over HTTPS only
    assert "<img" not in render("![x](https://other.example/a.png)")
    assert LogAction.objects.filter(
        text="The images of these hosts load in Markdown: insight.pycal.org"
    ).exists()
    page = client.get("/setup/settings/").content.decode()
    assert ">insight.pycal.org</textarea>" in page
    privacy = client.get("/about/privacy/").content.decode()
    assert "<code>insight.pycal.org</code>" in privacy.split("data-image-hosts")[1]
    client.post("/setup/settings/", {"image_hosts": ""})
    assert (
        "<img" not in render(BADGE)
        and "data-image-hosts" not in client.get("/about/privacy/").content.decode()
    )


@pytest.mark.parametrize(
    "text",
    [
        "not a host",
        "insight.pycal.org/path",
        "a.b:8080",
        "x" * 300,
        "*.org",
        "*",
        "a.*.org",
        "**.a.org",
    ],
)
def test_a_wrong_host_is_refused(client, settings, admin, text):
    settings.SITE_ADMINS = ["admin"]
    client.force_login(admin)
    page = client.post("/setup/settings/", {"image_hosts": text}, follow=True)
    assert "The host of images is not valid" in page.content.decode()
    assert SiteSettings.current().image_hosts == list(DEFAULT_IMAGE_HOSTS)
