"""static/local-time.js shows the times in the local time of the browser, like GitHub."""

from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[2] / "static" / "local-time.js"
PAGE = """<!doctype html><html lang="{lang}" data-on-date="{on}"><head>
<script src="https://site.test/static/local-time.js" defer></script></head><body>
<time id="recent" class="when" datetime="{recent}" title="UTC">server text</time>
<time id="old" class="when" datetime="2026-01-05T23:30:00Z" title="2026-01-05 23:30 UTC">x</time>
</body></html>"""


@pytest.mark.parametrize(
    ("zone", "local", "day"),
    [("Europe/Berlin", "12:30", "Jan 6, 2026"), ("America/New_York", "6:30", "Jan 5, 2026")],
)
def test_times_are_local_and_relative(browser, zone, local, day):
    context = browser.new_context(timezone_id=zone, locale="en-US")
    page = context.new_page()
    page.clock.set_fixed_time("2026-11-12T14:30:00Z")
    context.route(
        "https://site.test/**",
        lambda route: route.fulfill(
            body=SCRIPT.read_text()
            if route.request.url.endswith(".js")
            else PAGE.format(recent="2026-11-12T11:30:00Z", lang="en", on="on %(date)s"),
            content_type="text/javascript" if route.request.url.endswith(".js") else "text/html",
        ),
    )
    page.goto("https://site.test/")
    recent = page.locator("#recent")
    assert recent.text_content() == "3 hours ago"
    assert local in recent.get_attribute("title")
    assert "UTC" not in recent.get_attribute("title")
    assert page.locator("#old").text_content() == f"on {day}"
    context.close()


def test_the_texts_are_those_of_the_server(browser):
    """The language of the page and the translation of "on" come from the server."""
    context = browser.new_context(timezone_id="Europe/Berlin", locale="en-US")
    page = context.new_page()
    page.clock.set_fixed_time("2026-11-12T14:30:00Z")
    context.route(
        "https://site.test/**",
        lambda route: route.fulfill(
            body=SCRIPT.read_text()
            if route.request.url.endswith(".js")
            else PAGE.format(recent="2026-11-12T11:30:00Z", lang="de", on="am %(date)s"),
            content_type="text/javascript" if route.request.url.endswith(".js") else "text/html",
        ),
    )
    page.goto("https://site.test/")
    assert page.locator("#recent").text_content() == "vor 3 Stunden"
    assert page.locator("#old").text_content() == "am 06.01.2026"
    context.close()
