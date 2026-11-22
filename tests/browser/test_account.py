"""The pages of the account and of the administrators in Chromium."""

from playwright.sync_api import expect


def test_an_administrator_allows_the_images_of_a_host(signed_in, site, settings, bob):
    """Administration -> Settings: a host whose images load; the privacy policy names it."""
    settings.SITE_ADMINS = ["bob"]
    page = signed_in
    page.goto(f"{site}/projects/")
    page.locator(".account-menu summary").click()
    page.get_by_role("link", name="Settings").click()
    page.get_by_label("Hosts whose images load, one a line").fill("insight.pycal.org")
    page.get_by_role("button", name="Save the settings").click()
    expect(page.get_by_text("The settings are saved.")).to_be_visible()
    page.goto(f"{site}/about/privacy/")
    expect(page.locator("[data-image-hosts]")).to_contain_text("insight.pycal.org")
