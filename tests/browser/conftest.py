"""Browser tests: the site runs with a fake GitHub, Chromium visits it (Playwright)."""

import os

import pytest
from django.conf import settings as django_settings

from pycal_dashboard.services.repository_sync import RepositorySync

# Playwright's synchronous API runs an event loop; the database is used from this thread only.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")


@pytest.fixture
def site(live_server, transactional_db, organization):
    """The address of a site that read the organization; nothing leaves the machine."""
    RepositorySync(1).run()
    return live_server.url


@pytest.fixture
def page(page, site):
    """A page of Chromium that may only open the site; JavaScript errors fail the test."""
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.context.route(
        "**/*",
        lambda route: route.continue_() if route.request.url.startswith(site) else route.abort(),
    )
    page.set_default_timeout(5000)
    yield page
    assert not errors, errors


@pytest.fixture
def signed_in(page, site, client, bob):
    """The page with bob signed in, through the session cookie of the test client."""
    client.force_login(bob)
    cookie = client.cookies[django_settings.SESSION_COOKIE_NAME]
    page.context.add_cookies([{"name": cookie.key, "value": cookie.value, "url": site}])
    return page
