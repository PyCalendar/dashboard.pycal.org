"""The flows of people in the browser: sign in with GitHub, create a project, share it."""

import re

import pytest
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
    expect(table.locator("[data-columns-shown]")).to_have_text("Title, Step, Number, Creator")
    expect(table.locator("td.col-title").first).to_be_visible()
    expect(table.locator("td.col-status").first).to_be_hidden()
    expect(table.locator("td.col-link").first).to_be_hidden()  # the title and number link
    row = table.locator("tr[data-status='open']").first
    expect(row).to_have_css("border-left-color", "rgb(29, 107, 51)")  # open: green
    table.get_by_text("Display:").click()
    table.get_by_label("Title").uncheck()
    table.get_by_label("Number", exact=True).uncheck()
    expect(table.locator("td.col-title").first).to_be_hidden()
    expect(table.locator("td.col-link").first).to_be_visible()  # now the icon links
    expect(table.locator("[data-columns-shown]")).to_have_text("Step, Creator")
    table.get_by_label("Status").check()
    expect(row).to_have_css("border-left-style", "none")
    page.reload()
    expect(page.locator("td.col-title").first).to_be_hidden()
    expect(page.locator("td.col-status").first).to_be_visible()
    page.get_by_label("Per page").select_option("10")
    expect(page).to_have_url(re.compile(r"per_page=10"))
    assert github.writes() == []


def test_share_a_project(signed_in, site, alice):
    """The owner gives another person a role by their GitHub handle, which the field proposes."""
    page = signed_in
    page.goto(f"{site}/projects/new/")
    page.get_by_label("Name").fill("Shared")
    expect(page.get_by_label("Public")).to_be_checked()  # the default
    page.get_by_label("Private").check()
    page.get_by_role("button", name="Create the project").click()
    page.get_by_role("link", name="Collaborators").click()
    expect(page.get_by_label("GitHub handle")).to_have_attribute("data-complete-connected", "")
    page.get_by_label("GitHub handle").press_sequentially("ali")
    proposal = page.get_by_role("option", name="@alice")
    expect(proposal.locator("img.avatar")).to_have_count(1)
    proposal.click()
    expect(page.get_by_label("GitHub handle")).to_have_value("alice")
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
    page.locator("[data-add-condition]").get_by_role("button", name="Close").click()  # the cross
    expect(menu).to_be_hidden()
    page.get_by_label("Add a condition").click()
    page.keyboard.press("Escape")  # so does Escape
    expect(menu).to_be_hidden()
    page.get_by_label("Add a condition").click()
    menu.get_by_label("Condition").select_option("branch")
    expect(menu.get_by_label("Name of the label")).to_be_hidden()
    menu.get_by_text("outdated", exact=True).click()
    menu.get_by_text("conflict", exact=True).click()
    menu.get_by_role("button", name="Add the column").click()
    expect(page).to_have_url(re.compile(r"col=branch~all~outdated~conflict"))
    expect(page.locator("[data-pull-request]")).to_have_count(3)
    expect(page.locator(".result-no")).to_have_count(1)
    expect(page.locator(".result-no")).to_have_attribute("aria-label", "does not apply")
    # the toggles: without the crosses, then without the check marks: the crosses come back
    page.get_by_role("button", name="Show those it does not apply to").click()
    expect(page.locator("[data-pull-request]")).to_have_count(2)
    page.get_by_role("button", name="Show those it applies to").click()
    expect(page.locator("[data-pull-request]")).to_have_count(1)
    expect(page.get_by_role("button", name="Show those it does not apply to")).to_have_attribute(
        "aria-pressed", "true"
    )
    page.get_by_role("button", name="Show those it applies to").click()  # both again
    expect(page.locator("[data-pull-request]")).to_have_count(3)
    # its gear: other states
    page.get_by_label("Change the column").click()
    gear = page.locator("[data-condition-column='0'] [data-condition-form]")
    gear.get_by_text("outdated", exact=True).click()
    gear.get_by_role("button", name="Change the column").click()
    expect(page).to_have_url(re.compile(r"col=branch~all~conflict&"))
    # a second column: a label, chosen from those of the repositories
    page.get_by_label("Add a condition").click()
    menu = page.locator("[data-add-condition] [data-condition-form]")
    menu.get_by_role("button", name="Add the column").click()  # the browser asks for a label
    expect(page).not_to_have_url(re.compile(r"col=labels"))
    menu.get_by_label("Name of the label").fill("needs review")
    menu.get_by_role("button", name="Add the column").click()
    expect(page.locator(".label-chip").first).to_have_text("needs review")
    heads = page.locator("th.col-condition")
    expect(heads.nth(1).locator(".label-chip")).to_have_text("needs review")
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


def test_the_bar_at_the_top_is_one_row_on_a_phone(page, site, signed_in):
    """The projects, the account, the language and the colors side by side, also on a phone."""
    page.set_viewport_size({"width": 360, "height": 740})
    page.goto(f"{site}/projects/")
    tops = [
        round(page.locator(selector).first.bounding_box()["y"])
        for selector in (
            ".nav nav a[href='/projects/']",
            ".account-menu summary",
            ".theme-menu summary",
        )
    ]
    assert max(tops) - min(tops) < 20, tops


def test_save_a_filter_and_open_it_again(signed_in, site, github, bob):
    """Save the columns as a filter, with the suggested opposite; open it from the tab Filters."""
    pull_request_project(github, bob)
    page = signed_in
    page.goto(
        f"{site}/projects/icalendar/pull-requests/"
        "?col=labels~not~present~needs+review&col=status~applies~open"
    )
    expect(page.locator("[data-pull-request]")).to_have_count(3)  # open, or without the label
    page.get_by_role("link", name="Save", exact=True).click()
    expect(page.get_by_role("link", name="Filters")).to_have_attribute("aria-current", "page")
    page.locator("[data-opposite]").get_by_role("button", name="Use it").click()
    expect(page.locator("[data-condition-row='0']")).to_contain_text(
        "It does not have the label needs review"
    )
    expect(page.locator("[data-opposite]")).to_have_count(0)
    status = page.locator("[data-condition-row='1']")
    status.locator("label.switch").click()  # off: grayed out
    expect(status.locator(".condition-name")).to_have_css("opacity", "0.45")
    status.locator("label.switch").click()  # on again
    expect(status.locator(".condition-name")).to_have_css("opacity", "1")
    page.get_by_label("Name").fill("Waiting")
    page.get_by_label("Description", exact=True).fill("Not *reviewed* yet")
    page.get_by_role("button", name="Save the filter").click()
    expect(page.get_by_text("The filter Waiting is saved.")).to_be_visible()
    item = page.locator("[data-filter='Waiting']")
    expect(item.locator("em")).to_have_text("reviewed")
    held = []  # the numbers wait until the spinner is seen
    page.route(re.compile(r"/filters/\d+/\?numbers=1$"), lambda route: held.append(route))
    item.locator("summary").click()  # the table of conditions, its numbers filled in
    expect(item.locator("[data-filter-conditions] tr[data-condition-count]")).to_have_count(2)
    expect(item.locator("[data-count-of='0'] .loading[role=status]")).to_be_visible()
    while not held:
        page.wait_for_timeout(20)
    held[0].continue_()
    expect(item.locator("[data-count-of='0']")).to_have_text("2")  # without the label
    expect(item.locator("[data-filter-total]")).to_have_text("The filter shows 3 pull requests.")
    item.get_by_role("link", name="Pull requests").click()
    expect(page.get_by_role("heading", name="Waiting: 3 pull requests")).to_be_visible()
    page.get_by_role("link", name="Save", exact=True).click()
    expect(page.get_by_role("heading", name=re.compile("^Edit the filter Waiting"))).to_be_visible()
    expect(page.locator("[data-save-indicator]")).to_have_text("✓ Saved")  # it saves itself
    page.get_by_role("link", name="← Back to the pull requests").click()
    expect(page.get_by_role("heading", name="Waiting: 3 pull requests")).to_be_visible()
    page.get_by_role("link", name="Filters", exact=True).click()
    page.get_by_role("link", name="New filter").click()  # the table, its menu + open
    expect(page.locator("[data-add-condition]")).to_have_attribute("open", "")
    expect(page.get_by_role("heading", name="Waiting")).to_have_count(0)


def test_steps_of_pull_requests(signed_in, site, github, bob):
    """Filters become steps without a new page, are moved in the bar, and are explained."""
    from pycal_dashboard.models import PullRequestFilter

    project = pull_request_project(github, bob)
    for name, column in (
        ("Conflicts", "branch~applies~conflict"),
        ("Review", "labels~applies~present~needs review"),
    ):
        PullRequestFilter.objects.create(project=project, name=name, columns=[column])
    page = signed_in
    page.goto(f"{site}/projects/icalendar/filters/")
    for name in ("Conflicts", "Review"):
        item = page.locator(f"[data-filter='{name}']")
        url = page.url
        item.get_by_role("button", name="Make it a step").click()
        expect(item.locator("[data-step-link]")).to_have_text(f"Step: {name}")
        assert page.url == url  # no new page
    page.get_by_role("link", name="Steps", exact=True).click()
    bar = page.locator("[data-step-bar]")
    expect(bar.locator("[data-step]")).to_have_count(2)
    expect(bar.locator("[data-step]").first).to_contain_text("Conflicts")
    bar.locator("[data-step]").nth(1).get_by_role("button", name="Move left: earlier").click()
    expect(bar.locator("[data-step]").first).to_contain_text("Review")
    expect(bar.locator("[data-step]").first.locator(".step-number")).to_have_text("Step 1")
    # the arrows to move: left of the name and right of it; disabled at the ends
    first = bar.locator("[data-step]").first
    expect(first.get_by_role("button", name="Move left: earlier")).to_be_disabled()
    expect(
        bar.locator("[data-step]").last.get_by_role("button", name="Move right: later")
    ).to_be_disabled()
    left = first.get_by_role("button", name="Move left: earlier").bounding_box()
    assert left["x"] < first.locator(".step-name").bounding_box()["x"]
    page.reload()
    expect(page.locator("[data-step-bar] [data-step]").first).to_contain_text("Review")
    heads = page.locator("[data-step-bar] [data-step]")
    heads.nth(1).drag_to(heads.nth(0))
    expect(page.locator("[data-step-bar] [data-step]").first).to_contain_text("Conflicts")
    # a click on a step shows it below; its condition is explained with the pencil
    page.locator("[data-step-bar]").get_by_role("link", name="Review").click()
    detail = page.locator("[data-step-detail]")
    detail.get_by_label("Name", exact=True).fill("Waiting for a review")
    detail.locator(".condition-edit > summary").click()
    detail.get_by_label("Summary", exact=True).last.fill("A person reviews it")
    description = detail.get_by_label("Description: how to do it")
    description.fill("Ask @")
    editor = detail.locator("[data-markdown-field]:has(#description-0)")
    editor.get_by_text("Variables", exact=True).click()  # the menu of the bar of the editor
    editor.get_by_role("menuitem", name="{author_handle}").click()  # inserted, no button
    expect(description).to_have_value("Ask @{author_handle}")
    expect(editor.locator("[data-variables-menu]")).not_to_have_attribute("open", "")
    # it saves itself: no button, a status that says so
    expect(detail.get_by_role("button", name="Save the step")).to_be_hidden()
    expect(detail.locator("[data-save-status]")).to_have_text("✓ Saved", timeout=10000)
    expect(page.locator("[data-step-bar]")).to_contain_text("Waiting for a review")
    # Preview: the text with an example pull request, said above it
    editor.get_by_role("button", name="Preview").click()
    shown = editor.locator("[data-markdown-shown]")
    expect(shown).to_contain_text("Ask @niccokunzmann")
    expect(shown).to_contain_text("With an example pull request:")
    page.reload()
    expect(page.locator("[data-step-detail]").get_by_label("Name", exact=True)).to_have_value(
        "Waiting for a review"
    )


def test_the_page_of_a_pull_request(page, site, github, bob):
    """From the table to a pull request: the bar of its steps, a click on a step, its tasks."""
    from pycal_dashboard.models import PullRequestFilter, PullRequestStep

    project = pull_request_project(github, bob)
    for position, (name, column, summary) in enumerate(
        (
            ("Conflicts", "branch~applies~conflict", "Solve the conflict"),
            ("Review", "labels~applies~present~needs review", "Review it, {author_handle}"),
        )
    ):
        saved = PullRequestFilter.objects.create(project=project, name=name, columns=[column])
        PullRequestStep.objects.create(
            project=project,
            filter=saved,
            name=name,
            position=position,
            conditions={column: {"summary": summary, "description": "See *the guide*."}},
        )
    page.set_viewport_size({"width": 390, "height": 800})  # a phone
    page.goto(f"{site}/projects/icalendar/pull-requests/")
    page.get_by_role("link", name="Ready", exact=True).click()
    bar = page.locator("[data-progress]")
    expect(bar.locator("[data-step]")).to_have_count(2)
    expect(bar.locator("[data-step]").first).to_have_attribute("data-complete", "true")
    current = bar.locator("[data-current]")
    expect(current).to_contain_text("Review")
    expect(current.locator("a")).to_have_attribute("aria-current", "step")
    expect(current.locator(".square-todo")).to_have_css(
        "background-color", "rgb(163, 36, 47)"
    )  # red
    task = page.locator("[data-task='todo']")
    expect(task.locator("em")).to_have_text("the guide")  # open: its description shows
    expect(task).to_contain_text("Review it, octocat")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")  # fits a phone
    bar.get_by_role("link", name="Conflicts").click()
    done = page.locator("[data-task='done']")
    expect(done).to_contain_text("Solve the conflict")
    expect(done.locator("em")).to_be_hidden()  # closed
    done.locator("summary").click()
    expect(done.locator("em")).to_be_visible()


def test_columns_of_reviews_and_of_the_author(page, site, github, bob):
    """The menu + adds the reviews of a pull request and the ratio of its author."""
    project = pull_request_project(github, bob)
    mona = {"id": 777, "login": "monalisa", "avatar_url": "", "type": "User"}
    github.add_review("collective/icalendar", 1, mona)
    github.add_review("collective/icalendar", 1, mona, "COMMENTED")  # counts: all kinds do
    github.add_review("collective/icalendar", 1, state="COMMENTED")  # octocat on their own: not
    github.add_issue("collective/icalendar", "Hers", pull_request=True, user=mona)  # 4
    github.add_review("collective/icalendar", 4)  # octocat reviews it twice
    github.add_review("collective/icalendar", 4, state="COMMENTED")
    from pycal_dashboard.services.repository_update import RepositoryUpdate

    assert RepositoryUpdate(project.repositories.get()).run()
    page.goto(f"{site}/projects/icalendar/pull-requests/")
    page.get_by_label("Add a condition").click()
    menu = page.locator("[data-add-condition] [data-condition-form]")
    menu.get_by_label("Condition").select_option("reviews")
    expect(menu.get_by_label("Name of the label")).to_be_hidden()
    expect(menu.get_by_label("The pull request has")).to_have_value("at_least")  # by default
    menu.get_by_label("Reviews", exact=True).fill("1")
    menu.get_by_role("button", name="Add the column").click()
    expect(page).to_have_url(re.compile(r"col=reviews~all~at_least~1"))
    ready = page.locator("[data-pull-request='collective/icalendar#1']")
    expect(ready.locator(".col-condition")).to_contain_text("2 reviews")  # all kinds, not own
    # the comments do not count with their switch off in the gear of the column
    page.locator("th.col-condition .column-menu summary").first.click()
    gear = page.locator("th.col-condition [data-condition-form]").first
    kinds = gear.locator("[data-review-kinds='reviews_kinds']")
    expect(kinds).to_contain_text("Dismissed: an approval or a request for changes")
    expect(kinds.locator("input[value='own']")).not_to_be_checked()  # by default
    kinds.locator("label.switch", has_text="commented").click()
    gear.get_by_role("button", name="Change the column").click()
    expect(page).to_have_url(
        re.compile(r"col=reviews~all~at_least~1~approved~changes_requested~dismissed")
    )
    expect(ready.locator(".col-condition")).to_contain_text("1 review")
    page.get_by_label("Add a condition").click()
    menu.get_by_label("Condition").select_option("author")
    menu.get_by_label("Of the author, in the project").select_option("review_ratio")
    expect(menu.get_by_label("Is", exact=True)).to_have_value("below")  # by default
    menu.get_by_label("Is", exact=True).select_option("above")
    menu.get_by_label("The number to compare with").fill("0.3")
    menu.get_by_role("button", name="Add the column").click()
    expect(page).to_have_url(re.compile(r"col=author~all~review_ratio~above~0.3"))
    # octocat opened 3 and reviewed the pull request of monalisa twice, with the comment: 0.67
    expect(ready.locator(".col-condition").nth(1)).to_contain_text("0.67")
    expect(ready.locator(".col-condition").nth(1)).to_have_attribute("data-result", "yes")


def test_hide_a_step_and_check_the_pull_requests_outside(signed_in, site, github, bob):
    """The switch hides a step at once; Check lists the pull requests outside of the steps."""
    from pycal_dashboard.models import PullRequestFilter, PullRequestStep

    project = pull_request_project(github, bob)
    saved = PullRequestFilter.objects.create(
        project=project, name="Conflicts", columns=["branch~applies~conflict"]
    )
    step = PullRequestStep.objects.create(project=project, filter=saved, name="Conflicts")
    page = signed_in
    page.goto(f"{site}/projects/icalendar/steps/")
    switch = page.locator("[data-step-visible] input[role=switch]")
    expect(switch).to_be_checked()  # visible by default
    assert switch.bounding_box()["width"] < 60  # the switch as everywhere
    page.locator("[data-step-visible] label.switch").click()  # hidden
    expect(page.locator("[data-save-status]")).to_have_attribute("data-state", "saved")
    step.refresh_from_db()
    assert step.hidden
    page.get_by_label("Add the labels").last.fill("conflict solved, done")  # on completing
    expect(page.locator("[data-save-status]")).to_have_attribute("data-state", "saved")
    step.refresh_from_db()
    assert step.actions["complete"]["add"] == ["conflict solved", "done"]
    page.get_by_role("link", name="Check").click()
    expect(page.get_by_role("heading", name="Outside of the steps")).to_be_visible()
    expect(page.locator("[data-outside-pull]")).to_have_count(2)  # Ready and Behind
    page.locator("[data-outside-pull='collective/icalendar#1'] a").first.click()
    expect(page.locator("[data-outside-note]")).to_be_visible()
    expect(page.locator("[data-progress] [data-step]")).to_have_count(0)  # hidden


def test_a_form_sent_while_the_site_starts_comes_back(signed_in, site, github, bob):
    """The page of the start waits for /health/ and then opens a page, never 405."""
    from pathlib import Path

    pull_request_project(github, bob)
    starting = (Path(__file__).parents[2] / "docker" / "starting.html").read_text()
    page = signed_in

    def restarting(route):  # nginx answers the form with the page of the start
        if route.request.method == "POST":
            route.fulfill(status=503, body=starting, content_type="text/html")
        else:
            route.continue_()

    page.route(re.compile(r"/projects/icalendar/update/$"), restarting)
    page.goto(f"{site}/projects/icalendar/")
    page.get_by_role("button", name="Update").click()
    expect(page.get_by_role("heading", name="The site is starting")).to_be_visible()
    # the update takes only POST: back to the page of the form, not 405
    expect(page).to_have_url(f"{site}/projects/icalendar/", timeout=10000)
    expect(page.get_by_role("heading", name="iCalendar")).to_be_visible()


def test_download_and_restore_a_backup(signed_in, site, github, bob, tmp_path):
    """The settings save the project as YAML; restoring shows what it changes, then asks."""
    from pycal_dashboard.models import PullRequestFilter

    project = pull_request_project(github, bob)
    PullRequestFilter.objects.create(project=project, name="Open", columns=["status~applies~open"])
    page = signed_in
    page.goto(f"{site}/projects/icalendar/settings/")
    page.locator("[data-settings-tabs]").get_by_role("link", name="Backup").click()
    with page.expect_download() as download:
        page.get_by_role("link", name="Download the backup").click()
    backup = tmp_path / "backup.yaml"
    download.value.save_as(backup)
    assert "dashboard_backup: 1" in backup.read_text()
    PullRequestFilter.objects.all().delete()
    PullRequestFilter.objects.create(project=project, name="Later", columns=[])
    page.locator("[data-restore]").get_by_label("A backup of a project").set_input_files(backup)
    page.get_by_role("button", name="Show what the backup changes").click()
    expect(page.locator("[data-restore-adds]")).to_contain_text("Add the filter “Open”")
    later = page.get_by_label("Delete the filter “Later”, added after the backup")
    expect(later).not_to_be_checked()
    page.get_by_role("button", name="Restore the backup").click()
    expect(page.get_by_text("The backup is restored.")).to_be_visible()
    names = sorted(PullRequestFilter.objects.values_list("name", flat=True))
    assert names == ["Later", "Open"]  # nothing deleted without a tick


def test_take_and_restore_a_snapshot(signed_in, site, github, bob):
    """Settings -> Snapshots: take one, then restore it; what came after stays unless ticked."""
    from pycal_dashboard.models import PullRequestFilter

    project = pull_request_project(github, bob)
    PullRequestFilter.objects.create(project=project, name="Open", columns=["status~applies~open"])
    page = signed_in
    page.goto(f"{site}/projects/icalendar/settings/")
    page.locator("[data-settings-tabs]").get_by_role("link", name="Snapshots").click()
    page.get_by_role("button", name="Take a snapshot").click()
    expect(page.get_by_text("The snapshot is taken.")).to_be_visible()
    expect(page.locator("[data-snapshot-list] tbody tr")).to_have_count(1)
    PullRequestFilter.objects.all().delete()
    PullRequestFilter.objects.create(project=project, name="Later", columns=[])
    page.get_by_role("button", name="Restore").click()
    expect(page.locator("[data-restore-adds]")).to_contain_text("Add the filter “Open”")
    page.get_by_role("button", name="Restore the backup").click()
    expect(page.get_by_text("The backup is restored.")).to_be_visible()
    assert sorted(PullRequestFilter.objects.values_list("name", flat=True)) == ["Later", "Open"]
    page.locator("[data-settings-tabs]").get_by_role("link", name="Danger zone").click()
    expect(page.get_by_role("button", name="Delete the project")).to_be_visible()


def test_sync_the_pull_requests_of_people(signed_in, site, github, bob):
    """PR Sync for people: their GitHub handles, which the field proposes; their open PRs."""
    from pycal_dashboard.models import PullRequestMessage
    from pycal_dashboard.services.repository_update import RepositoryUpdate

    project = pull_request_project(github, bob)  # three open pull requests of octocat
    mona = {"id": 777, "login": "monalisa", "avatar_url": "", "type": "User", "name": "Mona"}
    github.add_issue("collective/icalendar", "Hers", pull_request=True, user=mona)
    github.add_issue("collective/icalendar", "Done", pull_request=True, user=mona, state="closed")
    github.add_account("monafromgithub", 888)  # of GitHub only: proposed after those known
    RepositoryUpdate(project.repositories.get()).run()
    page = signed_in
    page.goto(f"{site}/projects/icalendar/message/scope/")
    save = page.locator("[data-save-message]")
    expect(save).to_have_text("Keep 0 pull requests synchronized")
    field = page.get_by_label("GitHub handles of authors")
    expect(field).to_have_attribute("data-complete-connected", "")
    field.press_sequentially("mon")
    proposal = page.get_by_role("option", name="@monalisa")
    expect(proposal).to_contain_text("Mona")
    options = page.get_by_role("option")
    expect(options).to_have_count(2)
    expect(options.nth(1)).to_have_text("@monafromgithub")
    proposal.click()
    expect(field).to_have_value("monalisa, ")
    expect(save).to_have_text("Keep 1 pull request synchronized")  # the open one, on by default
    field.press_sequentially("octo")
    page.get_by_role("option", name="@octocat").click()
    expect(save).to_have_text("Keep 4 pull requests synchronized")
    save.click()
    expect(page.get_by_text("The scope is saved: 4 pull requests get the message")).to_be_visible()
    message = PullRequestMessage.objects.get()
    assert (message.authors, message.to_authors) == (["monalisa", "octocat"], True)
    expect(field).to_have_value("monalisa, octocat")
    page.locator("[data-scope-authors]").get_by_text("Add to the open pull requests of").click()
    expect(save).to_have_text("Keep 0 pull requests synchronized")  # switched off


def test_the_message_of_the_pull_requests(signed_in, site, github, bob):
    """PR Sync: edit the message (saved while it is written), preview it, the scope, apply."""
    from pycal_dashboard.models import PullRequestFilter, PullRequestMessage, PullRequestStep

    project = pull_request_project(github, bob)
    saved = PullRequestFilter.objects.create(
        project=project, name="Review", columns=["labels~applies~present~needs review"]
    )
    PullRequestStep.objects.create(project=project, filter=saved, name="Review")
    page = signed_in
    page.goto(f"{site}/projects/icalendar/pull-requests/")
    page.get_by_role("link", name="PR Sync").click()
    expect(page.locator("[data-no-message]")).to_be_visible()
    page.get_by_role("link", name="Create the message").click()  # Edit
    expect(page.locator("form[data-autosaving]")).to_have_count(1)
    page.get_by_role("textbox", name="The message").fill("**{pr_title}**: {tasks_todo}")
    expect(page.locator("[data-save-status]")).to_have_text("✓ Saved", timeout=10000)
    page.reload()  # it is kept
    expect(page.get_by_role("textbox", name="The message")).to_have_value(
        "**{pr_title}**: {tasks_todo}"
    )
    tabs = page.locator("[data-sync-tabs]")
    tabs.get_by_role("link", name="Preview").click()
    label = page.locator("[data-example-label]")
    expect(label).to_have_text("Example 1 of 2: Review, 0 of 1 quality checks done")
    expect(page.locator("[data-message-rendered] strong")).to_be_visible()
    page.get_by_role("link", name="The next example: one more quality check done").click()
    expect(label).to_have_text("Example 2 of 2: outside of the steps, 1 of 1 quality checks done")
    expect(page.locator("[data-message-rendered]")).to_contain_text("Nothing to do.")
    page.get_by_role("textbox", name="The message of the pull request").fill("1")
    page.get_by_role("button", name="Show").click()
    expect(page.locator("[data-message-rendered]")).to_contain_text("Ready")
    page.get_by_role("link", name="Edit this step").click()  # the step, and back
    page.get_by_role("link", name="← Back to the review of the message").click()
    expect(page.locator("[data-message-rendered]")).to_contain_text("Ready")
    page.locator("[data-sync-tabs]").get_by_role("link", name="Synchronization").click()
    expect(page.locator("[data-not-applied]")).to_be_visible()  # edited, not applied
    save = page.locator("[data-save-message]")
    expect(save).to_have_text("Keep 0 pull requests synchronized")  # off by default
    page.locator("[data-message-scope]").get_by_text("Add to all open pull requests").click()
    expect(save).to_have_text("Keep 3 pull requests synchronized")
    page.set_viewport_size({"width": 390, "height": 900})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")  # fits a phone
    save.click()
    expect(page.get_by_text("The scope is saved: 3 pull requests get the message")).to_be_visible()
    page.locator("[data-not-applied]").get_by_role("link", name="Continue editing").click()
    page.get_by_role("button", name="Apply").click()
    expect(page.get_by_text("The message is applied: 3 pull requests get it")).to_be_visible()
    message = PullRequestMessage.objects.get()
    assert message.to_open and message.template.startswith("**{pr_title}**")
    assert message.draft is None
    page.locator("[data-sync-tabs]").get_by_role("link", name="Edit").click()
    expect(page.locator("[data-apply]")).to_have_text("✓ Applied")
    expect(page.locator("[data-apply]")).to_be_disabled()
    expect(page.locator("form[data-autosaving]")).to_have_count(1)
    page.get_by_role("textbox", name="The message").fill("Changed: {pr_title}")
    expect(page.locator("[data-apply]")).to_have_text("Apply")  # not the current one
    page.get_by_role("button", name="Apply").click()  # at once, while it is saved: one click
    expect(page.get_by_text("The message is applied: 3 pull requests get it")).to_be_visible()
    message.refresh_from_db()
    assert message.template == "Changed: {pr_title}"
    # an autosave on its way may come after Apply: the same text, so it is applied all the same
    assert message.draft in (None, message.template)


def test_a_filter_keeps_its_name_from_the_step_to_the_table_and_back(signed_in, site, github, bob):
    """Step -> Edit the filter -> the table -> change a condition -> Save: still the filter."""
    from pycal_dashboard.models import PullRequestFilter, PullRequestStep

    project = pull_request_project(github, bob)
    saved = PullRequestFilter.objects.create(
        project=project, name="Review", columns=["labels~applies~present~needs review"]
    )
    PullRequestStep.objects.create(project=project, filter=saved, name="Review")
    PullRequestFilter.objects.create(project=project, name="Other", columns=[])
    page = signed_in
    page.goto(f"{site}/projects/icalendar/steps/")
    page.get_by_role("link", name="Edit the filter").click()
    expect(page.get_by_label("Name", exact=True)).to_have_value("Review")
    page.get_by_role("link", name="← Back to the pull requests").click()
    page.locator("th.col-condition .column-menu summary").first.click()  # the gear
    menu = page.locator("th.col-condition [data-condition-form]").first
    menu.get_by_label("Name of the label").fill("needs docs")
    menu.get_by_role("button", name="Change the column").click()
    expect(page.get_by_role("heading", name=re.compile("^Review: "))).to_be_visible()
    page.get_by_role("link", name="Save", exact=True).click()
    expect(page.get_by_label("Name", exact=True)).to_have_value("Review")  # not empty
    page.get_by_label("Name", exact=True).fill("Other")  # the name of another filter
    page.get_by_role("button", name="Save as a new filter").click()
    expect(page.locator("[data-conflict]")).to_contain_text("The project has a filter Other")
    page.get_by_role("button", name="Replace Other").click()
    expect(page.get_by_text("The filter Other is saved.")).to_be_visible()
    assert PullRequestFilter.objects.get(name="Other").columns == [
        "labels~applies~present~needs docs"
    ]


def test_a_saved_filter_saves_itself(signed_in, site, github, bob):
    """The page of a saved filter: saved while it is edited, linked to its conditions and step."""
    from pycal_dashboard.models import PullRequestFilter, PullRequestStep

    project = pull_request_project(github, bob)
    saved = PullRequestFilter.objects.create(
        project=project, name="Review", columns=["labels~applies~present~needs review"]
    )
    step = PullRequestStep.objects.create(project=project, filter=saved, name="Peer review")
    page = signed_in
    page.goto(f"{site}/projects/icalendar/filters/")
    page.locator("[data-filter='Review']").get_by_role("link", name="Edit").click()
    status = page.locator("[data-save-indicator]")
    expect(status).to_have_text("✓ Saved")
    expect(page.locator("form[data-autosaving]")).to_have_count(1)  # the script is ready
    held = []  # the saving waits until its animation is seen
    page.route(re.compile(r"/filters/save/"), lambda route: held.append(route))
    page.get_by_label("Name", exact=True).fill("Maintainer review")
    expect(status).to_have_attribute("data-state", "saving")
    expect(status).to_have_text("Saving…")
    assert status.evaluate("e => getComputedStyle(e, '::before').animationName") == "spin"
    for _ in range(500):  # let each saving through, also one more when the field is left
        while held:
            held.pop().continue_()
        if status.get_attribute("data-state") == "saved":
            break
        page.wait_for_timeout(20)
    page.unroute(re.compile(r"/filters/save/"))
    expect(status).to_have_text("✓ Saved", timeout=10000)
    saved.refresh_from_db()
    assert saved.name == "Maintainer review"
    page.get_by_role("link", name="Peer review").click()
    expect(page.locator(f"[data-step-detail='{step.pk}']")).to_be_visible()
    page.go_back()
    page.get_by_role("link", name="Edit the conditions").click()
    expect(page.get_by_role("heading", name=re.compile("^Maintainer review"))).to_be_visible()


def test_saving_as_a_new_filter_leaves_the_saved_one(signed_in, site, github, bob):
    from pycal_dashboard.models import PullRequestFilter

    project = pull_request_project(github, bob)
    PullRequestFilter.objects.create(
        project=project, name="Review", columns=["labels~applies~present~needs review"]
    )
    page = signed_in
    page.goto(f"{site}/projects/icalendar/filters/")
    page.locator("[data-filter='Review']").get_by_role("link", name="Edit").click()
    expect(page.locator("form[data-autosaving]")).to_have_count(1)
    page.get_by_label("Name", exact=True).fill("Copy")
    page.get_by_role("button", name="Save as a new filter").click()
    expect(page.get_by_text("The filter Copy is saved.")).to_be_visible()
    names = sorted(PullRequestFilter.objects.values_list("name", flat=True))
    assert names == ["Copy", "Review"]


def test_readers_go_from_the_filters_to_the_steps_and_back(page, site, github, bob):
    from pycal_dashboard.models import PullRequestFilter, PullRequestStep

    project = pull_request_project(github, bob)
    saved = PullRequestFilter.objects.create(
        project=project, name="Review", columns=["labels~applies~present~needs review"]
    )
    PullRequestStep.objects.create(project=project, filter=saved, name="Peer review")
    page.goto(f"{site}/projects/icalendar/filters/")
    page.get_by_role("link", name="Peer review").click()
    page.get_by_role("link", name="Filter: Review").click()
    expect(page.get_by_role("heading", name=re.compile("^Review"))).to_be_visible()


def test_the_evidence_of_a_task_and_the_page_of_its_author(page, site, github, bob):
    """A task links to the merge box on GitHub and to the page of the author with its tabs."""
    from pycal_dashboard.models import PullRequestFilter, PullRequestStep

    project = pull_request_project(github, bob)
    saved = PullRequestFilter.objects.create(
        project=project,
        name="Ready",
        columns=["branch~applies~conflict", "author~applies~review_ratio~below~1"],
    )
    PullRequestStep.objects.create(project=project, filter=saved, name="Ready")
    page.goto(f"{site}/projects/icalendar/pull/2/")
    tasks = page.locator("[data-tasks]")
    expect(tasks.get_by_role("link", name="Where it is merged, on GitHub")).to_have_attribute(
        "href", "https://github.com/collective/icalendar/pull/2#issue-comment-box"
    )
    tasks.get_by_role("link", name="octocat in the project").click()
    states = page.locator("[data-contributor-states]")
    expect(states).to_contain_text("Review to pull request ratio")
    expect(states).to_contain_text("Pull requests opened")
    page.get_by_role("link", name="Pull requests 3").click()
    items = page.locator("[data-contributor-list='pull-requests'] li")
    expect(items).to_have_count(3)
    page.get_by_role("link", name="#2 Conflict").click()
    expect(page.locator("[data-tasks]")).to_be_visible()


def row_tops(page, part: str) -> list[float]:
    """Where a row of the boxes of the steps starts in each box, measured at once, when the
    page with its styles is loaded: before, the boxes are not a grid yet."""
    page.wait_for_load_state("load")
    return page.evaluate(
        "part => [...document.querySelectorAll('[data-progress] [data-step]')].map("
        "box => box.querySelector(part).getBoundingClientRect().top)",
        part,
    )


def test_skip_a_step_of_a_pull_request(signed_in, site, github, bob):
    """A writer skips the step a pull request is in, with a reason; the rows stay aligned."""
    from pycal_dashboard.models import PullRequestFilter, PullRequestStep

    project = pull_request_project(github, bob)
    for position, (name, column) in enumerate(
        (
            ("Peer review of the pull request", "labels~applies~present~needs review"),
            ("Open", "status~applies~open"),
        )
    ):
        saved = PullRequestFilter.objects.create(project=project, name=name, columns=[column])
        PullRequestStep.objects.create(project=project, filter=saved, name=name, position=position)
    page = signed_in
    page.set_viewport_size({"width": 700, "height": 900})  # the long name takes two lines
    page.goto(f"{site}/projects/icalendar/pull/1/")
    bar = page.locator("[data-progress]")
    first, second = bar.locator("[data-step]").nth(0), bar.locator("[data-step]").nth(1)
    expect(first).to_have_attribute("data-current", "")
    # the rows line up as in a table: the tasks of both steps at the same height
    tops = row_tops(page, ".progress-tasks")
    assert abs(tops[0] - tops[1]) < 1, tops
    first.locator("[data-skip-step]").click()  # the dialog pops out
    dialog = page.locator("[data-skip-dialog]:popover-open")
    expect(dialog).to_be_visible()
    dialog.get_by_label("Why can the step Peer review of the pull request be skipped?").fill(
        "Reviewed at the meeting"
    )
    dialog.get_by_role("button", name="Skip Peer review of the pull request").click()
    expect(page.get_by_text("The step Peer review of the pull request is skipped.")).to_be_visible()
    first = page.locator("[data-progress] [data-step]").nth(0)
    expect(first).to_have_attribute("data-skipped", "")
    expect(first.locator("[data-skip-reason]")).to_have_text("Reviewed at the meeting")
    expect(first.locator("[data-skipped-by] .github-user")).to_have_attribute(
        "href", "/projects/icalendar/contributors/bob/"
    )
    second = page.locator("[data-progress] [data-step]").nth(1)
    expect(second.locator(".progress-here")).to_have_text("The pull request is here")
    # "The pull request is here" and "Skipped by" are in the same row
    rows = row_tops(page, ".progress-status")
    assert abs(rows[0] - rows[1]) < 1, rows
    status = first.locator(".progress-status")
    expect(status).to_have_text(re.compile(r"^Skipped by\s+@bob: Reviewed at the meeting$"))
    first.get_by_role("button", name="Don't skip").click()
    expect(page.locator("[data-progress] [data-step]").nth(0)).to_have_attribute("data-current", "")


LIGHTNESS = """e => {  // the lightness of the background of an element, 0 to 1
  const canvas = document.createElement("canvas");
  const context = canvas.getContext("2d");
  context.fillStyle = getComputedStyle(e).backgroundColor;
  context.fillRect(0, 0, 1, 1);
  const [r, g, b] = context.getImageData(0, 0, 1, 1).data;
  return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
}"""


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_the_colors_of_steps_suit_light_and_dark_pages(page, site, github, bob, scheme):
    """A strong color, as labels on GitHub have, is a light background on light pages and a
    dark one on dark pages, so that the text stays readable."""
    from pycal_dashboard.models import PullRequestFilter, PullRequestStep

    project = pull_request_project(github, bob)
    saved = PullRequestFilter.objects.create(
        project=project, name="Review", columns=["labels~applies~present~needs review"]
    )
    PullRequestStep.objects.create(project=project, filter=saved, name="Review", color="#d73a4a")
    page.emulate_media(color_scheme=scheme)
    for address, box in (
        ("/projects/icalendar/steps/", "[data-step-bar] .step-box"),
        ("/projects/icalendar/pull/1/", "[data-progress] [data-step]"),
    ):
        page.goto(site + address)
        lightness = page.locator(box).first.evaluate(LIGHTNESS)
        if scheme == "light":
            assert lightness > 0.7, (address, lightness)
        else:
            assert lightness < 0.3, (address, lightness)


def test_choose_who_sets_the_status_labels(signed_in, site, github, bob):
    """PR Sync, tab Status Label: a table of the choices of the step labels, off by default."""
    from pycal_dashboard.models import PullRequestFilter, PullRequestStep

    project = pull_request_project(github, bob)
    saved = PullRequestFilter.objects.create(
        project=project, name="Review", columns=["labels~applies~present~needs review"]
    )
    PullRequestStep.objects.create(project=project, filter=saved, name="Review")
    page = signed_in
    page.goto(f"{site}/projects/icalendar/")
    page.get_by_role("link", name="PR Sync").click()
    page.locator("[data-sync-tabs]").get_by_role("link", name="Status Label").click()
    table = page.locator("[data-step-labels] table")
    expect(table.get_by_label("Off")).to_be_checked()
    effect = page.locator("[data-effect='sync']")
    expect(effect).to_be_hidden()  # the current choice: nothing to apply
    table.get_by_label("Synchronize").check()
    expect(effect).to_be_visible()  # what Apply does, above it
    expect(effect).to_contain_text("Create the labels Review and label 0 pull requests.")
    page.get_by_role("button", name="Apply").click()
    expect(page.get_by_text("The step labels are applied.")).to_be_visible()
    project.refresh_from_db()
    assert project.step_labels == "sync"
    expect(page.locator("[data-step-labels] table").get_by_label("Synchronize")).to_be_checked()
    expect(page.locator("[data-effect='sync']")).to_be_hidden()


def test_the_overview_updates_only_its_box(page, site, github, bob):
    """While a project updates, the box Updating reads itself again every 10 seconds; the page
    does not reload. When the update is done, the box shows a check mark."""
    from pycal_dashboard.models import Repository
    from pycal_dashboard.services.project_editor import ProjectEditor
    from pycal_dashboard.services.update_queue import UpdateQueue

    github.add_repository("collective/icalendar", issues=3, pulls=2, installation=11)
    project = ProjectEditor.create(bob, "iCalendar", slug="icalendar")
    project.repositories.add(Repository.objects.create(full_name="collective/icalendar"))
    UpdateQueue.add(project, bob, start=False)
    page.clock.install()
    page.goto(f"{site}/projects/icalendar/")
    box = page.locator("[data-live-status]")
    expect(box).to_have_attribute("data-status", "updating")
    expect(box.locator(".loading[role=status]")).to_be_visible()
    page.evaluate("window.notReloaded = true")
    page.clock.run_for(11_000)  # still updating: the box again, the same page
    expect(page.locator("[data-live-status]")).to_have_attribute("data-status", "updating")
    assert UpdateQueue.work() == 1
    page.clock.run_for(11_000)
    box = page.locator("[data-live-status]")
    expect(box).to_have_attribute("data-update-done", "")
    expect(box.locator(".badge-success")).to_be_visible()
    assert "✓" in box.locator(".badge-success").evaluate(
        "e => getComputedStyle(e, '::before').content"
    )
    expect(page.locator("[data-open-issues] strong")).to_have_text("3")  # the numbers, too
    assert page.evaluate("window.notReloaded") is True


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_the_choice_of_a_color_suits_light_and_dark_pages(signed_in, site, github, bob, scheme):
    """The swatches of the editor of a step: the color on light pages, dark on dark ones."""
    from pycal_dashboard.models import PullRequestFilter, PullRequestStep

    project = pull_request_project(github, bob)
    saved = PullRequestFilter.objects.create(
        project=project, name="Review", columns=["labels~applies~present~needs review"]
    )
    PullRequestStep.objects.create(project=project, filter=saved, name="Review")
    page = signed_in
    page.emulate_media(color_scheme=scheme)
    page.goto(f"{site}/projects/icalendar/steps/")
    swatches = page.locator("[data-step-colors] .swatch[style]")
    expect(swatches.first).to_be_visible()
    for index in range(swatches.count()):
        lightness = swatches.nth(index).evaluate(LIGHTNESS)
        if scheme == "light":
            assert lightness > 0.6, (index, lightness)
        else:  # the tint of a chosen step: well below the text, above the dark page
            assert lightness < 0.35, (index, lightness)


def test_a_column_of_the_dashboard(page, site, github, bob):
    """The menu + adds the column Dashboard: the pull requests that skip a step."""
    from pycal_dashboard.models import Issue, PullRequestFilter, PullRequestStep, StepSkip

    project = pull_request_project(github, bob)
    saved = PullRequestFilter.objects.create(
        project=project, name="Review", columns=["labels~applies~present~needs review"]
    )
    step = PullRequestStep.objects.create(project=project, filter=saved, name="Review")
    StepSkip.objects.create(step=step, issue=Issue.objects.get(number=2), user=bob, reason="Met")
    page.goto(f"{site}/projects/icalendar/pull-requests/")
    page.get_by_label("Add a condition").click()
    menu = page.locator("[data-add-condition] [data-condition-form]")
    menu.get_by_label("Condition").select_option("dashboard")
    menu.locator(".fields-dashboard label.switch", has_text="a skipped step").click()
    menu.get_by_role("button", name="Add the column").click()
    expect(page).to_have_url(re.compile(r"col=dashboard~\w+~skipped"))
    skipping = page.locator("[data-pull-request='collective/icalendar#2'] .col-condition")
    expect(skipping).to_have_attribute("data-result", "yes")
    other = page.locator("[data-pull-request='collective/icalendar#1'] .col-condition")
    expect(other).to_have_attribute("data-result", "no")


def test_a_column_of_the_type_of_author(page, site, github, bob):
    """The menu + adds the column Type of author: the switches, their help, the first-timers."""
    from pycal_dashboard.models import Issue

    pull_request_project(github, bob)
    Issue.objects.filter(number=2).update(author_association="FIRST_TIME_CONTRIBUTOR")
    page.goto(f"{site}/projects/icalendar/pull-requests/")
    page.get_by_label("Add a condition").click()
    menu = page.locator("[data-add-condition] [data-condition-form]")
    menu.get_by_label("Condition").select_option("author_type")
    fields = menu.locator(".fields-author_type")
    expect(fields.get_by_text("They are exclusive")).to_be_visible()
    expect(fields.get_by_role("link", name="More in the documentation")).to_have_attribute(
        "href", re.compile(r"reference/conditions/author_type\.html$")
    )
    fields.locator("label.switch", has_text="first-timer").click()
    menu.get_by_role("button", name="Add the column").click()
    expect(page).to_have_url(re.compile(r"col=author_type~\w+~first_timer"))
    first = page.locator("[data-pull-request='collective/icalendar#2'] .col-condition")
    expect(first).to_have_attribute("data-result", "yes")
    expect(first).to_contain_text("first-timer")
    other = page.locator("[data-pull-request='collective/icalendar#1'] .col-condition")
    expect(other).to_have_attribute("data-result", "no")
    expect(other).to_contain_text("contributor")


def test_the_kinds_of_reviews_on_the_page_of_a_person(page, site, github, bob):
    """The gear chooses which reviews count; a switch counts again at once. By default, the
    reviews of octocat on their own pull requests do not count."""
    project = pull_request_project(github, bob)
    mona = {"id": 777, "login": "monalisa", "avatar_url": "", "type": "User"}
    github.add_issue("collective/icalendar", "Hers", pull_request=True, user=mona)  # 4
    github.add_review("collective/icalendar", 4)  # by octocat
    github.add_review("collective/icalendar", 4, state="COMMENTED")
    github.add_review("collective/icalendar", 1, state="COMMENTED")  # on their own
    from pycal_dashboard.services.repository_update import RepositoryUpdate

    assert RepositoryUpdate(project.repositories.get()).run()
    page.goto(f"{site}/projects/icalendar/contributors/octocat/?tab=reviews")
    reviews = page.locator(".contributor-tabs a", has_text="Reviews").locator(".tab-count")
    expect(reviews).to_have_text("2")
    page.locator("[data-kinds-menu] summary").click()
    expect(page.locator("[data-kinds-apply]")).to_be_hidden()  # the script counts at once
    form = page.locator("[data-kinds-form]")
    expect(form).to_contain_text("By default, a review counts only when its author is not")
    form.locator("label.switch", has_text="by the author of the pull request").click()
    expect(page).to_have_url(re.compile(r"kinds=own"))
    expect(
        page.locator(".contributor-tabs a", has_text="Reviews").locator(".tab-count")
    ).to_have_text("3")
    page.locator("[data-kinds-menu] summary").click()
    page.locator("[data-kinds-form] label.switch", has_text="commented").click()
    expect(page).to_have_url(re.compile(r"kinds=approved"))
    expect(
        page.locator(".contributor-tabs a", has_text="Reviews").locator(".tab-count")
    ).to_have_text("1")
    expect(page.locator("[data-contributor-list='reviews'] li")).to_have_count(1)


def test_drag_a_condition_into_skip_if(signed_in, site, github, bob):
    """The page of saving a filter: Quality checks and Skip if; a condition is dragged between."""
    pull_request_project(github, bob)
    page = signed_in
    page.goto(
        f"{site}/projects/icalendar/filters/save/"
        "?col=status~applies~open&col=labels~applies~present~needs+review"
    )
    checks = page.locator("tbody[data-section='checks']")
    skip = page.locator("tbody[data-section='skip']")
    expect(checks.locator("tr[data-condition-row]")).to_have_count(2)
    expect(skip.locator("tr[data-condition-row]")).to_have_count(0)
    checks.locator("tr[data-condition-row='1']").drag_to(skip.locator("tr[data-drop-here]"))
    expect(page).to_have_url(re.compile(r"labels~skip~present"))
    skip = page.locator("tbody[data-section='skip']")
    expect(skip.locator("tr[data-condition-row]")).to_contain_text("It has the label needs review")
    skip.get_by_role("button", name="To the quality checks").click()
    expect(page).to_have_url(re.compile(r"labels~applies~present"))
    expect(page.locator("tbody[data-section='skip'] tr[data-condition-row]")).to_have_count(0)


def test_drag_a_condition_keeps_what_was_typed(signed_in, site, github, bob):
    """The name, the description and the switches stay when a condition is dragged or moved."""
    pull_request_project(github, bob)
    page = signed_in
    page.goto(
        f"{site}/projects/icalendar/filters/save/"
        "?col=status~applies~draft&col=status~applies~closed~merged~auto_merge&per_page=25"
    )
    page.get_by_label("Name").fill("Ready")
    page.locator("textarea#description").fill("Open *ones*")
    page.locator("tr[data-condition-row='0'] label.switch").click()  # off
    checks = page.locator("tbody[data-section='checks']")
    skip = page.locator("tbody[data-section='skip']")
    checks.locator("tr[data-condition-row='1']").drag_to(skip.locator("tr[data-drop-here]"))
    expect(page).to_have_url(re.compile(r"status~skip~closed~merged~auto_merge"))
    expect(page.locator("tbody[data-section='skip'] tr[data-condition-row]")).to_have_count(1)
    expect(page.get_by_label("Name")).to_have_value("Ready")
    expect(page.locator("textarea#description")).to_have_value("Open *ones*")
    expect(page.locator("input[name=on][value='0']")).not_to_be_checked()
    expect(page.locator("input[name=on][value='1']")).to_be_checked()
    page.get_by_role("button", name="Remove").first.click()  # a button keeps them, too
    expect(page.get_by_label("Name")).to_have_value("Ready")
    expect(page.locator("tr[data-condition-row]")).to_have_count(1)


def test_a_column_of_text(page, site, github, bob):
    """The menu + adds a column of text: the title starts with a text, the case not matching."""
    pull_request_project(github, bob)
    page.goto(f"{site}/projects/icalendar/pull-requests/")
    page.get_by_label("Add a condition").click()
    menu = page.locator("[data-add-condition] [data-condition-form]")
    menu.get_by_label("Condition").select_option("text")
    menu.get_by_label("How it matches").select_option("starts")
    menu.get_by_label("The text, or the regex").fill("con")
    menu.get_by_role("button", name="Add the column").click()
    expect(page).to_have_url(re.compile(r"col=text~all~title~starts~con"))
    conflict = page.locator("[data-pull-request='collective/icalendar#2'] .col-condition")
    expect(conflict).to_have_attribute("data-result", "yes")
    ready = page.locator("[data-pull-request='collective/icalendar#1'] .col-condition")
    expect(ready).to_have_attribute("data-result", "no")


def test_a_github_handle_leads_to_the_pages_of_the_person(page, site, github, bob):
    """The handle of an author opens their page in the project, whose heading opens their page
    in all projects; the mark of GitHub next to every handle leads to GitHub."""
    pull_request_project(github, bob)
    page.goto(f"{site}/projects/icalendar/pull-requests/")
    author = page.locator("[data-pull-request] .github-person").first
    expect(author.locator(".github-link-icon")).to_have_attribute(
        "href", "https://github.com/octocat"
    )
    author.locator("[data-github-user='octocat']").click()
    expect(page).to_have_url(f"{site}/projects/icalendar/contributors/octocat/")
    heading = page.locator("[data-contributor] h2")
    expect(heading.locator(".github-link-icon")).to_have_attribute(
        "href", "https://github.com/octocat"
    )
    heading.locator("[data-github-user='octocat']").click()
    expect(page).to_have_url(f"{site}/people/octocat/")
    expect(page.locator("[data-person-project='icalendar']")).to_contain_text("3 pull requests")
    page.locator("[data-person-project='icalendar'] a").click()
    expect(page).to_have_url(f"{site}/projects/icalendar/contributors/octocat/")
