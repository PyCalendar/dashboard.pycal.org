"""Times like on GitHub, links to the documentation as ? and links to GitHub with its mark."""

from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest
from django.template import Context, Template
from django.utils import timezone as django_timezone

from pycal_dashboard.templatetags.times import ago

NOW = datetime(2026, 11, 12, 15, 0, tzinfo=UTC)
TEMPLATES = Path(__file__).parents[1] / "pycal_dashboard" / "templates"


@pytest.mark.parametrize(
    ("before", "text"),
    [
        (timedelta(seconds=10), "just now"),
        (timedelta(minutes=1), "1 minute ago"),
        (timedelta(minutes=59), "59 minutes ago"),
        (timedelta(hours=1), "1 hour ago"),
        (timedelta(hours=23), "23 hours ago"),
        (timedelta(hours=30), "yesterday"),
        (timedelta(days=29), "29 days ago"),
        (timedelta(days=30), "on 2026-10-13"),
    ],
)
def test_how_long_ago(before, text):
    assert ago(NOW - before, NOW) == text


def test_the_tag_shows_utc_on_hover_for_any_time_zone(monkeypatch):
    monkeypatch.setattr(django_timezone, "now", lambda: NOW)
    berlin = timezone(timedelta(hours=1))
    html = Template("{% load times %}{% when value %}").render(
        Context({"value": datetime(2026, 11, 12, 14, 0, tzinfo=berlin)})
    )
    assert html == (
        '<time class="when" datetime="2026-11-12T13:00:00Z" title="2026-11-12 13:00 UTC">'
        "2 hours ago</time>"
    )


def test_no_time_is_empty():
    assert Template("{% load times %}{% when value %}").render(Context({"value": None})) == ""


def test_no_page_formats_times_itself():
    for template in TEMPLATES.rglob("*.html"):
        text = template.read_text()
        assert "|date:" not in text and "<time " not in text, template


def test_the_script_is_static_and_the_page_has_no_inline_script(client, db):
    page = client.get("/").content.decode()
    assert '<script src="/static/local-time.js" defer></script>' in page
    assert "<script>" not in page


def test_help_link():
    html = Template('{% load help %}{% help_link "https://docs.example.org/x.html" "X" %}').render(
        Context()
    )
    assert 'class="help-link"' in html and 'target="_blank"' in html
    assert 'aria-label="Help: X (opens in a new tab)"' in html
    assert '<svg class="icon book"' in html and ">?<" not in html  # an open book
    assert Template('{% load help %}{% help_link "" "X" %}').render(Context()) == ""


def test_github_link():
    mark = Template('{% load github %}{% github_link "https://github.com/a" "a on GitHub" %}')
    html = mark.render(Context())
    assert "github-link-icon" in html and 'aria-label="a on GitHub"' in html and "<svg" in html
    text = Template('{% load github %}{% github_link "https://github.com/a" "a" "Text" "button" %}')
    assert 'class="github-link button"' in text.render(Context())


def test_pages_link_their_documentation_with_a_question_mark(client, alice):
    client.force_login(alice)
    account = client.get("/account/").content.decode()
    assert 'class="help-link" href="https://docs.example.org/tutorial/account.html"' in account
    assert 'href="https://github.com/alice"' in account and "github-mark" in account
