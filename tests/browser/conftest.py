"""Browser tests: the site runs with a fake GitHub, Chromium visits it (Playwright)."""

import os

import pytest
from django.conf import settings as django_settings

# Playwright's synchronous API runs an event loop; the database is used from this thread only.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")


@pytest.fixture(scope="session")
def django_db_modify_db_settings(tmp_path_factory):
    """A database in a file, as on the site: requests in parallel threads and the update in the
    background wait for each other, instead of failing as with SQLite in memory."""
    from django.conf import settings

    database = tmp_path_factory.mktemp("database") / "test.sqlite3"
    settings.DATABASES["default"]["TEST"]["NAME"] = str(database)


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    """Chromium reaches only this machine: a proxy that leads nowhere for everything else.

    Routes of Playwright do not see redirects, such as one to GitHub; the proxy stops them too.
    """
    return {
        **browser_type_launch_args,
        "proxy": {"server": "http://127.0.0.1:9", "bypass": "localhost,127.0.0.1"},
    }


@pytest.fixture
def site(live_server, transactional_db, settings, monkeypatch):
    """The address of the site; nothing leaves the machine. Updates only wait, see update_worker."""
    settings.ACCOUNT_DEFAULT_HTTP_PROTOCOL = "http"
    return live_server.url


@pytest.fixture
def update_worker(update_worker, site):
    """The worker of the updates, stopped before the site and its database end."""
    return update_worker


@pytest.fixture
def oauth(monkeypatch):
    """GitHub for the sign in: allauth reaches the fake OAuth app."""
    from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

    from tests.fakes.github_oauth import FakeOAuth

    fake = FakeOAuth()
    monkeypatch.setattr(
        DefaultSocialAccountAdapter, "get_requests_session", lambda self: fake.session()
    )
    return fake


@pytest.fixture
def page(page, site):
    """A page of Chromium that may only open the site; JavaScript errors fail the test."""
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    from tests.fakes.github_oauth import FakeOAuth

    page.context.route(
        "**/*",
        lambda route: route.continue_() if route.request.url.startswith(site) else route.abort(),
    )
    # the site sends the person to GitHub to authorize it; the fake agrees and goes back at once
    page.context.route(f"{site}/accounts/github/login/**", FakeOAuth.authorize)
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
