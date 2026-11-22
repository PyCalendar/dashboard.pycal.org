"""The page Settings of the administrators: the hosts whose images texts of Markdown show."""

import pytest

from pycal_dashboard.markdown_text import render
from pycal_dashboard.models import LogAction, SiteSettings

pytestmark = pytest.mark.django_db
BADGE = "![Replies](https://insight.pycal.org/badge/s/x/replies/a.svg)"


def test_only_the_administrators_see_the_settings(client, settings, admin, alice):
    settings.SITE_ADMINS = ["admin"]
    client.force_login(alice)
    assert client.get("/setup/settings/").status_code == 403
    assert "data-site-settings-link" not in client.get("/projects/").content.decode()
    assert client.post("/setup/settings/", {"image_hosts": "evil.example"}).status_code == 403
    assert SiteSettings.current().image_hosts == []
    client.force_login(admin)
    assert "data-site-settings-link" in client.get("/projects/").content.decode()
    assert client.get("/setup/settings/").status_code == 200


def test_an_allowed_host_shows_its_images(client, settings, admin):
    settings.SITE_ADMINS = ["admin"]
    assert "<img" not in render(BADGE)  # none by default: its text
    client.force_login(admin)
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


@pytest.mark.parametrize("text", ["not a host", "insight.pycal.org/path", "a.b:8080", "x" * 300])
def test_a_wrong_host_is_refused(client, settings, admin, text):
    settings.SITE_ADMINS = ["admin"]
    client.force_login(admin)
    page = client.post("/setup/settings/", {"image_hosts": text}, follow=True)
    assert "The host of images is not valid" in page.content.decode()
    assert SiteSettings.current().image_hosts == []
