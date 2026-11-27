"""People sign up for the PR message themselves: their pull requests on the repositories get it."""

import pytest

from pycal_dashboard.models import PullRequestMessage, PullRequestStep
from pycal_dashboard.services.message_signup import MessageSignup
from tests.conftest import person

from .test_message import MONALISA, REPO, project, save, update  # noqa: F401 (fixture)

pytestmark = pytest.mark.django_db
SIGNUP = "/projects/icalendar/message/scope/new/user/"


@pytest.fixture
def mona(github, project):  # noqa: F811
    """Monalisa signed in with GitHub, with an open pull request and a closed one."""
    github.add_issue(REPO, "Hers", pull_request=True, user=MONALISA)  # #4, open
    github.add_issue(REPO, "Done", pull_request=True, user=MONALISA, state="closed")  # #5
    update(project)
    return person(MONALISA["id"], "monalisa")


@pytest.fixture
def applied(client, project, bob):  # noqa: F811
    """The message, applied by Bob, for the open pull requests of people: nobody yet."""
    client.force_login(bob)
    save(client, to_authors="on", authors="")
    client.logout()
    return PullRequestMessage.objects.get()


def section(page: str) -> str:
    return page.split("data-message-signup>")[1].split("</section>")[0]


def test_without_an_applied_message_for_people_there_is_no_sign_up(client, project, bob):  # noqa: F811
    assert client.get(SIGNUP).status_code == 404
    client.force_login(bob)
    save(client, to_open="on")  # the switch of people is off
    answer = client.get(SIGNUP)
    assert answer.status_code == 404 and "No sign up for the PR message" in answer.content.decode()
    page = client.get("/projects/icalendar/message/").content.decode()
    assert "data-signup-link" not in page


def test_visitors_see_the_text_the_repositories_and_signing_in(client, applied):
    page = client.get(SIGNUP).content.decode()
    shown = section(page)
    assert "Log in to enable the Pull Request Messages" in shown
    assert "<li>github.com/collective/icalendar</li>" in shown
    assert "<a " not in shown  # no links: nobody gets lost
    assert (
        "Sign in with GitHub" in shown
        and 'name="next" value="/projects/icalendar/message/scope/new/user/"' in shown
    )
    assert 'class="tabs' not in page  # no tabs of the project nor of PR Sync
    assert client.post(SIGNUP, {"enabled": "on"})["Location"].startswith("/accounts/login/")


def test_the_writers_change_the_text(client, applied, bob):
    client.force_login(bob)
    scope = client.get("/projects/icalendar/message/scope/").content.decode()
    assert MessageSignup.default_text() in scope  # the default, to change
    client.post(
        "/projects/icalendar/message/scope/",
        {"to_authors": "on", "signup_text": MessageSignup.default_text(), "save": "yes"},
    )
    applied.refresh_from_db()
    assert applied.signup_text == ""  # the default stays the default, also when translated
    text = "Sign in to get **the status** of your pull requests\non iCalendar:"
    client.post(
        "/projects/icalendar/message/scope/",
        {"to_authors": "on", "signup_text": text, "save": "yes"},
    )
    client.logout()
    shown = section(client.get(SIGNUP).content.decode())
    assert "<strong>the status</strong>" in shown and "Log in to enable" not in shown


def test_sign_up_and_out(client, github, applied, mona):
    client.force_login(mona)
    shown = section(client.get(SIGNUP).content.decode())
    assert "Hello @monalisa," in shown
    assert 'name="enabled" value="on">' in shown  # off by default
    assert "Enable Pull Request Messages for all your pull requests on these repositories?" in shown
    assert "<li>github.com/collective/icalendar</li>" in shown and "<a " not in shown
    answer = client.post(SIGNUP, {"enabled": "on"})
    assert answer["Location"] == SIGNUP
    applied.refresh_from_db()
    assert applied.authors == ["monalisa"]
    page = client.get(SIGNUP).content.decode()
    assert 'name="enabled" value="on" checked>' in section(page)
    assert "Your pull requests on these repositories get the PR message." in page
    update(applied.project)
    assert {c["issue"] for c in github.comments.values()} == {f"{REPO}#4"}  # not the closed
    client.post(SIGNUP, {"enabled": "on"})  # again: once
    applied.refresh_from_db()
    assert applied.authors == ["monalisa"]
    client.post(SIGNUP, {})  # switched off
    applied.refresh_from_db()
    assert applied.authors == []
    assert "Your pull requests no longer get the PR message." in client.get(SIGNUP).content.decode()


def test_the_handle_keeps_the_others_whatever_its_case(client, applied, mona):
    applied.authors = ["octocat", "MonaLisa"]
    applied.save()
    client.force_login(mona)
    assert 'value="on" checked>' in section(client.get(SIGNUP).content.decode())
    client.post(SIGNUP, {})
    applied.refresh_from_db()
    assert applied.authors == ["octocat"]


def test_an_account_without_a_github_handle(client, applied):
    from django.contrib.auth import get_user_model

    admin = get_user_model().objects.create(username="root")
    client.force_login(admin)
    answer = client.post(SIGNUP, {"enabled": "on"})
    assert answer.status_code == 400 and "Sign in with GitHub" in answer.content.decode()
    applied.refresh_from_db()
    assert applied.authors == []


def test_the_message_page_links_the_sign_up(client, applied):
    page = client.get("/projects/icalendar/message/").content.decode()
    assert "Pull Requests with a status message" in page
    assert "Which pull requests get it" not in page
    scope = page.split("data-scope-title>")[1]
    assert "pull requests with a status message." in scope.split("data-message-count>")[1]
    link = scope.split("data-signup-link>")[1].split("</p>")[0]
    assert f'href="{SIGNUP}"' in link and "Sign up" in link
    assert PullRequestStep.objects.exists()
