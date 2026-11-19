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


def test_create_a_project(signed_in, site, github, update_worker):
    """Create a project, add repositories in two ways, see the app step, see them read."""
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
    expect(field).to_have_attribute("data-complete-connected", "")
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
    page.get_by_role("button", name="Show repositories").click()
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

    # the overview: the added repositories are read in the background at once
    page.get_by_role("link", name="Go to the overview").click()
    expect(page.locator("[data-status='never']")).to_have_count(0)
    expect(page.locator("[data-status='current']")).to_contain_text("Up to date", timeout=15000)
    page.get_by_role("button", name="Update").click()  # and again, when asked
    expect(page.locator("[data-status='current']")).to_contain_text("Up to date", timeout=15000)
    expect(page.locator("[data-open-issues] strong")).to_have_text("4")
    expect(page.locator("[data-open-pull-requests] strong")).to_have_text("2")
    expect(page.locator("[data-last-updated]")).not_to_contain_text("never")
    expect(page.locator("[data-repository='collective/icalendar']")).to_contain_text("3")
    assert Project.objects.get().updated is not None

    # the pull requests of all its repositories, from the tile with their number
    page.locator("[data-open-pull-requests] a").click()
    expect(page).to_have_url(re.compile(r"/projects/[0-9a-f]{6}/pull-requests/$"))
    expect(page.get_by_role("link", name="Pull requests")).to_have_attribute("aria-current", "page")
    expect(page.locator("[data-pull-request]")).to_have_count(2)
    expect(page.locator("[data-pull-request] [data-github-user='octocat']").first).to_be_visible()
    # the columns: hidden by CSS, the choice kept by the browser
    table = page.locator("[data-pull-requests]")
    expect(table.locator("[data-columns-shown]")).to_have_text("Title, Number, Creator")
    expect(table.locator("td.col-title").first).to_be_visible()
    expect(table.locator("td.col-status").first).to_be_hidden()
    expect(table.locator("td.col-link").first).to_be_hidden()  # the title and number link
    row = table.locator("tr[data-status='open']").first
    expect(row).to_have_css("border-left-color", "rgb(29, 107, 51)")  # open: green
    table.get_by_text("Display:").click()
    table.get_by_label("Title").uncheck()
    table.get_by_label("Number").uncheck()
    expect(table.locator("td.col-title").first).to_be_hidden()
    expect(table.locator("td.col-link").first).to_be_visible()  # now the icon links
    expect(table.locator("[data-columns-shown]")).to_have_text("Creator")
    table.get_by_label("Status").check()
    expect(row).to_have_css("border-left-style", "none")
    page.reload()
    expect(page.locator("td.col-title").first).to_be_hidden()
    expect(page.locator("td.col-status").first).to_be_visible()
    page.get_by_label("Per page").select_option("10")
    expect(page).to_have_url(re.compile(r"per_page=10"))
    assert github.writes() == []


def test_share_a_project(signed_in, site, alice):
    """The owner gives another person a role by their GitHub name, which the field proposes."""
    page = signed_in
    page.goto(f"{site}/projects/new/")
    page.get_by_label("Name").fill("Shared")
    expect(page.get_by_label("Public")).to_be_checked()  # the default
    page.get_by_label("Private").check()
    page.get_by_role("button", name="Create the project").click()
    page.get_by_role("link", name="Collaborators").click()
    expect(page.get_by_label("GitHub name")).to_have_attribute("data-complete-connected", "")
    page.get_by_label("GitHub name").press_sequentially("ali")
    proposal = page.get_by_role("option", name="@alice")
    expect(proposal.locator("img.avatar")).to_have_count(1)
    proposal.click()
    expect(page.get_by_label("GitHub name")).to_have_value("alice")
    page.locator("[data-share]").get_by_label("Role", exact=True).select_option("write")
    page.get_by_role("button", name="Share").click()
    expect(page.get_by_text("@alice may change the project.")).to_be_visible()
    expect(page.locator("[data-member='alice']")).to_be_visible()
    expect(page).to_have_url(re.compile(r"/projects/[0-9a-f]{6}/collaborators/$"))


def test_give_a_project_a_short_address(signed_in, site, github):
    """A project of one repository takes the suggested address; the old one still leads to it."""
    page = signed_in
    github.add_repository("collective/icalendar")
    page.goto(f"{site}/projects/new/")
    page.get_by_label("Name").fill("iCalendar")
    page.get_by_role("button", name="Create the project").click()
    expect(page).to_have_url(re.compile(r"/projects/[0-9a-f]{6}/repositories/$"))
    old = page.url
    page.get_by_label("Repository", exact=True).fill("collective/icalendar")
    page.locator("[data-add-by-name]").get_by_role("button", name="Add").click()
    suggestion = page.locator("[data-suggestion]")
    expect(suggestion).to_contain_text("icalendar")
    suggestion.get_by_role("button", name="Use it").click()
    expect(page).to_have_url(f"{site}/projects/icalendar/repositories/")
    expect(
        page.get_by_text("The address of the project is /projects/icalendar/ now")
    ).to_be_visible()
    page.goto(old)
    expect(page).to_have_url(f"{site}/projects/icalendar/repositories/")

    page.get_by_role("link", name="Settings").click()
    page.locator("[data-rename]").get_by_label("Address").fill("pycal~ical")
    page.get_by_role("button", name="Change the address").click()
    expect(page).to_have_url(f"{site}/projects/pycal~ical/settings/")
    expect(page.locator("[data-old-slugs]")).to_contain_text("icalendar")


def test_describe_a_project_in_markdown(signed_in, site):
    """The bar above the description formats it; the preview shows it as the page will."""
    page = signed_in
    page.goto(f"{site}/projects/new/")
    page.get_by_label("Name").fill("iCalendar")
    field = page.locator("[data-markdown-field]")
    expect(field).to_have_attribute("data-markdown-connected", "")
    description = page.get_by_label("Description", exact=True)
    description.fill("calendars")
    description.select_text()
    field.get_by_role("button", name="Bold").click()
    expect(description).to_have_value("**calendars**")
    field.get_by_role("button", name="Preview").click()
    expect(field.locator("[data-markdown-shown] strong")).to_have_text("calendars")
    expect(description).to_be_hidden()
    field.get_by_role("button", name="Write").click()
    expect(description).to_be_visible()
    page.get_by_role("button", name="Create the project").click()
    page.get_by_role("link", name="Overview", exact=True).click()
    expect(page.locator("[data-description] strong")).to_have_text("calendars")


def test_click_away_the_notice_of_failed_updates(page, site, github, bob):
    """The notice of failed updates hides when clicked away, also after a reload."""
    from pycal_dashboard.models import Repository
    from pycal_dashboard.services.project_editor import ProjectEditor
    from pycal_dashboard.services.repository_update import RepositoryUpdate

    github.add_repository("collective/icalendar", installation=11)
    repository = Repository.objects.create(full_name="collective/icalendar")
    project = ProjectEditor.create(bob, "iCalendar")
    project.repositories.add(repository)
    github.fail_with = 502
    github.fail_html = "<html><head><title>502 Bad Gateway</title></head></html>"
    RepositoryUpdate(repository).run()
    page.goto(f"{site}{project.path()}")
    notice = page.locator("[data-update-errors]")
    expect(notice).to_contain_text("1 repository could not be updated")
    notice.get_by_text("Details to copy").click()
    expect(notice.locator("textarea")).to_contain_text("GitHubUnavailable")
    notice.get_by_role("button", name="Hide this notice").click()
    expect(notice).to_be_hidden()
    page.reload()
    expect(page.locator("[data-update-errors]")).to_be_hidden()


def pull_request_project(github, bob):
    """A project with pull requests of all kinds, read from the fake GitHub."""
    from pycal_dashboard.models import Repository
    from pycal_dashboard.services.project_editor import ProjectEditor
    from pycal_dashboard.services.repository_update import RepositoryUpdate

    github.add_repository("collective/icalendar", installation=11)
    github.add_label("collective/icalendar", "needs review", "", "fbca04")
    github.add_issue("collective/icalendar", "Ready", pull_request=True, labels=("needs review",))
    github.add_issue("collective/icalendar", "Conflict", pull_request=True, mergeable_state="dirty")
    github.add_issue("collective/icalendar", "Behind", pull_request=True, mergeable_state="behind")
    repository = Repository.objects.create(full_name="collective/icalendar")
    project = ProjectEditor.create(bob, "iCalendar", slug="icalendar")
    project.repositories.add(repository)
    RepositoryUpdate(repository).run()
    return project


def test_columns_of_conditions(page, site, github, bob):
    """Add a column with +, filter by it, change it with its gear, add another, drag it."""
    pull_request_project(github, bob)
    page.goto(f"{site}/projects/icalendar/pull-requests/")
    page.get_by_label("Add a condition").click()
    menu = page.locator("[data-add-condition] [data-condition-form]")
    expect(menu.get_by_label("Name of the label")).to_be_visible()  # Label comes first
    menu.get_by_label("Condition").select_option("branch")
    expect(menu.get_by_label("Name of the label")).to_be_hidden()
    menu.get_by_text("outdated", exact=True).click()
    menu.get_by_text("conflict", exact=True).click()
    menu.get_by_text("only those it applies to").click()
    menu.get_by_role("button", name="Add the column").click()
    expect(page).to_have_url(re.compile(r"col=branch~applies~outdated~conflict"))
    expect(page.locator("[data-pull-request]")).to_have_count(2)
    expect(page.locator("td.col-condition .result-yes")).to_have_count(2)
    # its gear: show all, then the crosses of those it does not apply to
    page.get_by_label("Change the column").click()
    gear = page.locator("[data-condition-column='0'] [data-condition-form]")
    gear.get_by_text("all pull requests").click()
    gear.get_by_role("button", name="Change the column").click()
    expect(page.locator("[data-pull-request]")).to_have_count(3)
    expect(page.locator(".result-no")).to_have_count(1)
    expect(page.locator(".result-no")).to_have_attribute("aria-label", "does not apply")
    # a second column: a label, chosen from those of the repositories
    page.get_by_label("Add a condition").click()
    menu = page.locator("[data-add-condition] [data-condition-form]")
    menu.get_by_role("button", name="Add the column").click()  # the browser asks for a label
    expect(page).not_to_have_url(re.compile(r"col=labels"))
    menu.get_by_label("Name of the label").fill("needs review")
    menu.get_by_role("button", name="Add the column").click()
    expect(page.locator(".label-chip").first).to_have_text("needs review")
    heads = page.locator("th.col-condition")
    expect(heads.nth(1)).to_contain_text("Label needs review: present")
    heads.nth(1).drag_to(heads.nth(0))
    expect(page).to_have_url(re.compile(r"col=labels~[^&]+&col=branch"))


def test_the_table_in_german_on_a_phone(page, site, github, bob):
    """German takes much space: the page, its table and its menus fit a phone."""
    pull_request_project(github, bob)
    page.set_viewport_size({"width": 360, "height": 740})
    page.goto(f"{site}/language/")  # the language of the menu: German
    page.context.add_cookies([{"name": "django_language", "value": "de", "url": site}])
    columns = "col=branch~all~up_to_date~outdated~conflict&col=status~all~open~auto_merge"
    page.goto(f"{site}/projects/icalendar/pull-requests/?{columns}")
    expect(page.get_by_role("heading", name="3 Pull Requests")).to_be_visible()
    expect(page.locator("[data-per-page-submit]")).to_be_hidden()  # the menu changes at once
    assert page.evaluate("document.documentElement.scrollWidth") <= 360
    page.get_by_text("Anzeigen:").click()
    for column in ("Status", "Organisation", "Repository", "Erstellt"):
        page.locator("[data-columns]").get_by_label(column, exact=True).check()
    assert page.evaluate("document.documentElement.scrollWidth") <= 360  # the table scrolls
    # the script writes the times in the language of the page, as the server translated it
    expect(page.locator("td.col-created time").first).to_contain_text("am ")
    expect(page.locator("td.col-created time").first).not_to_contain_text("on ")
    page.get_by_label("Eine Bedingung hinzufügen").click()
    panel = page.locator("[data-add-condition] .menu-panel")
    expect(panel).to_be_visible()
    box = panel.bounding_box()
    assert box["x"] >= 0 and box["x"] + box["width"] <= 360
    assert page.evaluate("document.documentElement.scrollWidth") <= 360
