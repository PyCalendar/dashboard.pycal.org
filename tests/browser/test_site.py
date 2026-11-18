"""Visit the site in Chromium like a contributor."""

import re

from playwright.sync_api import expect

from tests.conftest import REPOSITORY


def test_find_something_to_work_on(page, site):
    page.goto(site)
    expect(
        page.get_by_role("heading", name="Welcome to the community of PyCalendar")
    ).to_be_visible()
    page.get_by_role("link", name="Find something to work on").click()
    expect(page).to_have_url(f"{site}/contribute/")
    expect(page.get_by_role("link", name="Issue 1").first).to_have_attribute(
        "href", f"https://github.com/{REPOSITORY}/issues/1"
    )


def test_menu_leads_to_every_page(page, site):
    page.goto(site)
    for name, path in [
        ("Reviews", "/reviews/"),
        ("Repositories", "/repositories/"),
        ("Contributors", "/contributors/"),
        ("Contribute", "/contribute/"),
    ]:
        page.get_by_role("navigation", name="Menu").get_by_role("link", name=name).click()
        expect(page).to_have_url(f"{site}{path}")
        expect(page.get_by_role("link", name=name)).to_have_attribute("aria-current", "page")


def test_repository_and_contributor(page, site):
    page.goto(f"{site}/repositories/")
    page.get_by_role("link", name=REPOSITORY).click()
    expect(page.get_by_role("heading", level=1)).to_contain_text("icalendar")
    page.get_by_label("Kind").select_option("issues")
    page.get_by_role("button", name="Show").click()
    expect(page).to_have_url(re.compile(r"kind=issues"))
    expect(page.get_by_role("link", name="Pull request 4")).to_have_count(0)
    page.get_by_role("link", name="@alice").first.click()
    expect(page.get_by_role("heading", name="@alice")).to_be_visible()


def test_period_of_the_contributors(page, site):
    page.goto(f"{site}/contributors/")
    page.get_by_label("Period").select_option("30")
    page.get_by_role("button", name="Show").click()
    expect(page).to_have_url(f"{site}/contributors/?days=30")
    expect(page.get_by_text("in the last 30 days")).to_be_visible()


def test_switch_to_dark_colors(page, site):
    page.goto(f"{site}/about/")
    page.get_by_label("Colors of the page").click()
    page.get_by_role("button", name="Dark").click()
    expect(page).to_have_url(f"{site}/about/")
    expect(page.locator("html")).to_have_attribute("data-theme", "dark")
    expect(page.locator("body")).to_have_css("background-color", "rgb(17, 24, 32)")


def test_error_page_links_its_documentation(page, site):
    response = page.goto(f"{site}/repositories/PyCalendar/nothing/")
    assert response.status == 404
    expect(page.get_by_role("heading", name="Repository not found")).to_be_visible()
    expect(
        page.get_by_role("link", name="What this error means and how to solve it")
    ).to_have_attribute(
        "href",
        "https://docs.example.org/reference/errors.html#pycal_dashboard.errors.dashboard.RepositoryNotFound",
    )
    expect(page.locator("#error-details")).to_contain_text("Error: RepositoryNotFound (HTTP 404)")


def test_page_not_found(page, site):
    assert page.goto(f"{site}/nowhere/").status == 404
    page.get_by_role("link", name="Back to the start").click()
    expect(page).to_have_url(f"{site}/")


def test_account_asks_to_sign_in(page, site):
    page.goto(f"{site}/account/")
    expect(page.get_by_role("heading", name="Sign in with GitHub")).to_be_visible()
    expect(page.get_by_role("button", name="Sign in with GitHub")).to_be_visible()


def test_preferences(signed_in, site):
    page = signed_in
    page.goto(f"{site}/account/")
    expect(page.get_by_role("heading", name="Account · @bob")).to_be_visible()
    expect(page.get_by_role("link", name="Pull request 4")).to_be_visible()  # asked to review
    page.get_by_label("Email me a weekly summary").check()
    page.get_by_label(REPOSITORY).check()
    page.get_by_role("button", name="Save the preferences").click()
    expect(page.get_by_role("status")).to_have_text("Your preferences are saved.")
    expect(page.get_by_label("Email me a weekly summary")).to_be_checked()
    page.get_by_role("link", name=page.locator("a.brand").inner_text().strip()).click()
    expect(page.get_by_role("heading", name="Repositories you watch")).to_be_visible()


def test_sign_out(signed_in, site):
    page = signed_in
    page.goto(site)
    page.locator(".account-menu summary").click()
    page.get_by_role("button", name="Sign out").click()
    expect(page.get_by_role("link", name="Sign in with GitHub")).to_be_visible()


def test_phone_width_without_horizontal_scroll(page, site):
    page.set_viewport_size({"width": 360, "height": 740})
    for path in ("/", "/repositories/", f"/repositories/{REPOSITORY}/", "/account/"):
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
