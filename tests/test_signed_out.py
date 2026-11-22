"""Signing out stays on the page if visitors see it; else the next page higher that they see."""

import pytest

from pycal_dashboard.models import Project

from .test_steps import project  # noqa: F401 (fixtures)

pytestmark = pytest.mark.django_db


def sign_out_from(client, page: str) -> str:
    """Sign out with the address of the menu of the page; the address where it ends."""
    html = client.get(page).content.decode()
    menu = html.split('name="next" value="')[1].split('"')[0]
    answer = client.post("/accounts/logout/", {"next": menu.replace("&amp;", "&")}, follow=True)
    assert answer.status_code == 200
    return answer.redirect_chain[-1][0]


@pytest.mark.parametrize(
    ("page", "end"),
    [
        ("/projects/icalendar/pull-requests/?page=1", "/projects/icalendar/pull-requests/?page=1"),
        ("/projects/icalendar/settings/danger/", "/projects/icalendar/"),
        ("/projects/icalendar/message/edit/", "/projects/icalendar/message/"),
        ("/account/notifications/", "/"),
    ],
)
def test_signing_out_stays_or_goes_up(client, project, bob, page, end):  # noqa: F811
    client.force_login(bob)
    assert sign_out_from(client, page) == end
    assert "_auth_user_id" not in client.session


def test_a_private_project_goes_to_the_projects(client, project, bob):  # noqa: F811
    Project.objects.filter(pk=project.pk).update(public=False)
    client.force_login(bob)
    assert sign_out_from(client, "/projects/icalendar/steps/") == "/projects/"


def test_the_message_of_signing_out_shows(client, project, bob):  # noqa: F811
    client.force_login(bob)
    html = client.get("/projects/icalendar/settings/").content.decode()
    target = html.split('name="next" value="')[1].split('"')[0].replace("&amp;", "&")
    page = client.post("/accounts/logout/", {"next": target}, follow=True).content.decode()
    assert "signed out" in page.lower()
