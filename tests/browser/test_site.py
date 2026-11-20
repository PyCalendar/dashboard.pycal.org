"""Visit the site in Chromium like a contributor."""

from playwright.sync_api import expect


def test_start_page(page, site):
    page.goto(site)
    expect(
        page.get_by_role("heading", name="Welcome to the community of PyCalendar")
    ).to_be_visible()
    expect(page.locator("[data-github-app]")).to_have_count(0)
    expect(page.locator("[data-no-app]")).to_have_count(0)
    page.get_by_role("link", name="About the site").click()
    expect(page).to_have_url(f"{site}/about/")
    expect(page.get_by_text("writes nothing to GitHub")).to_be_visible()


def test_switch_to_dark_colors(page, site):
    page.goto(f"{site}/about/")
    page.get_by_label("Colors of the page").click()
    page.get_by_role("button", name="Dark").click()
    expect(page).to_have_url(f"{site}/about/")
    expect(page.locator("html")).to_have_attribute("data-theme", "dark")
    expect(page.locator("body")).to_have_css("background-color", "rgb(17, 24, 32)")


def test_error_page_links_its_documentation(page, site):
    response = page.goto(f"{site}/setup/installed/?installation_id=x")
    assert response.status == 400
    expect(page.get_by_role("heading", name="Invalid installation")).to_be_visible()
    expect(
        page.get_by_role("link", name="What this error means and how to solve it")
    ).to_have_attribute(
        "href",
        "https://docs.example.org/reference/errors.html#pycal_dashboard.errors.dashboard.InvalidInstallationId",
    )
    expect(page.locator("#error-details")).to_contain_text(
        "Error: InvalidInstallationId (HTTP 400)"
    )


def test_page_not_found(page, site):
    assert page.goto(f"{site}/nowhere/").status == 404
    page.get_by_role("link", name="Back to the start").click()
    expect(page).to_have_url(f"{site}/")


def test_account_asks_to_sign_in(page, site):
    page.goto(f"{site}/account/")
    expect(page.get_by_role("heading", name="Sign in with GitHub")).to_be_visible()
    expect(page.get_by_role("button", name="Sign in with GitHub")).to_be_visible()


def test_the_account(signed_in, site):
    page = signed_in
    page.goto(f"{site}/account/")
    expect(page.get_by_role("heading", name="Account · @bob")).to_be_visible()
    expect(page.get_by_role("link", name="Install the GitHub App").first).to_have_attribute(
        "href", "https://github.com/apps/dashboard-test/installations/new"
    )
    expect(page.get_by_label("Email me when an installation")).to_be_checked()


def test_sign_out(signed_in, site):
    page = signed_in
    page.goto(site)
    page.locator(".account-menu summary").click()
    page.get_by_role("button", name="Sign out").click()
    expect(page.get_by_role("link", name="Sign in with GitHub")).to_be_visible()


def test_phone_width_without_horizontal_scroll(page, site):
    page.set_viewport_size({"width": 360, "height": 740})
    for path in ("/", "/about/", "/account/", "/setup/github-app/"):
        page.goto(f"{site}{path}")
        width = page.evaluate("document.documentElement.scrollWidth")
        assert width <= 360, (path, width)


def test_works_without_javascript(browser, site):
    context = browser.new_context(java_script_enabled=False)
    page = context.new_page()
    page.goto(f"{site}/about/")
    page.get_by_label("Colors of the page").click()
    page.get_by_role("button", name="Light").click()
    expect(page.locator("html")).to_have_attribute("data-theme", "light")
    context.close()


def test_switch_the_language(page, site):
    page.goto(f"{site}/about/")
    page.get_by_label("Language").click()
    page.get_by_role("button", name="Deutsch").click()
    expect(page).to_have_url(f"{site}/about/")
    expect(page.locator("html")).to_have_attribute("lang", "de")
    expect(page.get_by_role("heading", name="Datenschutz")).to_be_visible()
    page.get_by_label("Sprache").click()
    page.get_by_role("button", name="English").click()
    expect(page.locator("html")).to_have_attribute("lang", "en")


def test_choose_the_language_and_the_colors_in_the_account(signed_in, site):
    page = signed_in
    page.goto(f"{site}/account/")
    page.locator("select#language").select_option("de")
    page.locator("select#theme").select_option("dark")
    page.get_by_role("button", name="Save the preferences").click()
    expect(page.get_by_role("status")).to_have_text("Deine Einstellungen sind gespeichert.")
    expect(page.locator("html")).to_have_attribute("lang", "de")
    expect(page.locator("html")).to_have_attribute("data-theme", "dark")
    expect(page.locator("body")).to_have_css("background-color", "rgb(17, 24, 32)")


def test_the_browser_reaches_nothing_but_the_site(page, site):
    """Also without the routes, and for redirects that they miss, nothing leaves the machine."""
    import pytest
    from playwright.sync_api import Error

    page.context.unroute_all()
    with pytest.raises(Error):
        page.goto("https://github.com/login", timeout=5000)


def test_delete_the_account(signed_in, site):
    """The red area of the page Account deletes the account after the GitHub handle is typed."""
    from django.contrib.auth import get_user_model

    page = signed_in
    page.goto(f"{site}/account/")
    area = page.locator("[data-delete-account]")
    expect(area).to_have_css("border-top-style", "solid")
    area.get_by_label("Type your GitHub handle, bob, to confirm").fill("bob")
    area.get_by_role("button", name="Delete my account").click()
    expect(page).to_have_url(f"{site}/")
    expect(page.get_by_text("Your account is deleted.")).to_be_visible()
    expect(page.get_by_role("link", name="Sign in with GitHub")).to_be_visible()
    assert not get_user_model().objects.filter(username="bob").exists()
