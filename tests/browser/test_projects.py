"""The flows of people in the browser: sign in with GitHub, create a project, share it."""

import re

from playwright.sync_api import expect

from pycal_dashboard.models import Profile, Project


def test_sign_in_with_github(page, site, oauth):
    """From the start page through GitHub, which the fake authorizes, back to the site."""
    page.goto(f"{site}/projects/")
    page.get_by_role("link", name="Sign in with GitHub").click()
    expect(page.get_by_role("heading", name="Sign in with GitHub")).to_be_visible()
    page.get_by_role("button", name="Sign in with GitHub").click()
    expect(page).to_have_url(f"{site}/projects/")
    expect(page.locator(".account-menu summary")).to_contain_text("carol")
    assert oauth.codes == ["the-code"]
    profile = Profile.objects.get(github_name="carol")
    assert profile.github_id == "77"
    assert profile.user.socialaccount_set.get().socialtoken_set.exists()  # lists the repositories
    page.goto(f"{site}/account/")
    expect(page.get_by_role("heading", name="Account · @carol")).to_be_visible()


def test_create_a_project(signed_in, site, github):
    """Create a project, add repositories in two ways, see the app step, update it."""
    page = signed_in
    github.organizations = ["PyCalendar"]
    github.add_repository("collective/icalendar", issues=3, pulls=2, installation=11)
    github.add_repository("PyCalendar/plann", issues=1)
    page.goto(f"{site}/")
    page.get_by_role("link", name="Projects").first.click()
    page.get_by_role("link", name="+ Create a project").click()
    page.get_by_label("Name").fill("iCalendar")
    page.get_by_label("Description").fill("The calendars of Python")
    page.get_by_role("button", name="Create the project").click()
    expect(
        page.get_by_text("The project iCalendar is created. Add its repositories.")
    ).to_be_visible()

    # by name, with the proposals of the field
    field = page.get_by_label("Repository", exact=True)
    field.fill("ical")
    expect(
        page.locator("#repository-choices option[value='collective/icalendar']")
    ).to_be_attached()
    field.fill("collective/icalendar")
    page.locator("[data-add-by-name]").get_by_role("button", name="Add").click()
    expect(page.get_by_text("collective/icalendar is added.")).to_be_visible()
    expect(
        page.locator("[data-repository='collective/icalendar'] [data-app-installed]")
    ).to_be_visible()

    # from an organization
    page.get_by_label("Organization or account").select_option("PyCalendar")
    page.get_by_role("button", name="Show its repositories").click()
    page.get_by_label("plann").check()
    page.locator("[data-owner-repositories]").get_by_role(
        "button", name="Add the chosen repositories"
    ).click()
    expect(page.get_by_text("PyCalendar/plann is added.")).to_be_visible()

    # the next step: the app on the repositories without it
    install = page.locator("[data-install-step]")
    expect(install).to_contain_text("1 repository has no GitHub App yet.")
    expect(
        install.get_by_role("link", name="Install the GitHub App", exact=True)
    ).to_have_attribute("href", "https://github.com/apps/dashboard-test/installations/new")
    expect(
        install.get_by_role("link", name="The permissions it asks for and why")
    ).to_have_attribute("href", "https://docs.example.org/reference/permissions.html")

    # the overview, updated in the background
    page.get_by_role("link", name="Go to the overview").click()
    expect(page.locator("[data-status='never']")).to_be_visible()
    page.get_by_role("button", name="Update").click()
    expect(page.locator("[data-status='current']")).to_contain_text("Up to date", timeout=15000)
    expect(page.locator("[data-open-issues] strong")).to_have_text("4")
    expect(page.locator("[data-open-pull-requests] strong")).to_have_text("2")
    expect(page.locator("[data-last-updated]")).not_to_contain_text("never")
    expect(page.locator("[data-repository='collective/icalendar']")).to_contain_text("3")
    assert Project.objects.get().updated is not None
    assert github.writes() == []


def test_share_a_project(signed_in, site, alice):
    """The owner gives another person a role by their GitHub name."""
    page = signed_in
    page.goto(f"{site}/projects/new/")
    page.get_by_label("Name").fill("Shared")
    page.get_by_label("Private: only its people see it").check()
    page.get_by_role("button", name="Create the project").click()
    page.get_by_role("link", name="People").click()
    page.get_by_label("GitHub name").fill("alice")
    page.locator("[data-share]").get_by_label("Role").select_option("write")
    page.get_by_role("button", name="Share").click()
    expect(page.get_by_text("@alice may change the project.")).to_be_visible()
    expect(page.locator("[data-member='alice']")).to_be_visible()
    expect(page).to_have_url(re.compile(r"/projects/[0-9a-f]{6}/shared/people/$"))


def test_give_a_project_a_short_address(signed_in, site, github):
    """A project of one repository takes the suggested address; the old one still leads to it."""
    page = signed_in
    github.add_repository("collective/icalendar")
    page.goto(f"{site}/projects/new/")
    page.get_by_label("Name").fill("iCalendar")
    page.get_by_role("button", name="Create the project").click()
    expect(page).to_have_url(re.compile(r"/projects/[0-9a-f]{6}/icalendar/repositories/$"))
    old = page.url
    page.get_by_label("Repository", exact=True).fill("collective/icalendar")
    page.locator("[data-add-by-name]").get_by_role("button", name="Add").click()
    suggestion = page.locator("[data-suggestion]")
    expect(suggestion).to_contain_text("icalendar")
    suggestion.get_by_role("button", name="Use it").click()
    expect(page).to_have_url(f"{site}/projects/icalendar/icalendar/repositories/")
    expect(
        page.get_by_text("The address of the project is /projects/icalendar/icalendar/ now")
    ).to_be_visible()
    page.goto(old)
    expect(page).to_have_url(f"{site}/projects/icalendar/icalendar/repositories/")

    page.get_by_role("link", name="Settings").click()
    page.locator("[data-rename]").get_by_label("Address").fill("pycal~ical")
    page.get_by_role("button", name="Change the address").click()
    expect(page).to_have_url(f"{site}/projects/pycal~ical/icalendar/settings/")
    expect(page.locator("[data-old-slugs]")).to_contain_text("icalendar")
